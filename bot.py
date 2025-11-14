import telebot
import requests
import re
import time
import logging
import config

# Log sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.BOT_TOKEN)

class PinterestDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def clean_url(self, text):
        """Matndan Pinterest linkini tozalab olish"""
        # Pinterest link patternlari
        patterns = [
            r'https://pin\.it/[^\s]+',
            r'https://pinterest\.com/pin/[^\s]+',
            r'https://www\.pinterest\.com/pin/[^\s]+',
            r'https://pinterest\.com/pin/\d+',
            r'https://www\.pinterest\.com/pin/\d+'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        
        return None
    
    def download_content(self, url):
        """Pinterest dan kontent yuklash"""
        try:
            logger.info(f"URL ga so'rov: {url}")
            
            # URL ni to'g'rilash
            if url.startswith('pin.it/'):
                url = 'https://' + url
            
            response = self.session.get(url, timeout=20)
            
            if response.status_code != 200:
                logger.error(f"HTTP xatosi: {response.status_code}")
                return [], []
            
            html_content = response.text
            
            # Rasmlarni topish
            images = self.extract_images(html_content)
            logger.info(f"Topilgan rasmlar: {len(images)}")
            
            # Videolarni topish
            videos = self.extract_videos(html_content)
            logger.info(f"Topilgan videolar: {len(videos)}")
            
            return images[:10], videos[:5]
            
        except Exception as e:
            logger.error(f"Xatolik: {e}")
            return [], []
    
    def extract_images(self, html_content):
        """HTML dan rasm URLlarini olish"""
        images = []
        
        patterns = [
            r'src="(https://i\.pinimg\.com/[^"]+)"',
            r'data-src="(https://i\.pinimg\.com/[^"]+)"',
            r'"url":"(https://i\.pinimg\.com/[^"]+)"',
            r'contentUrl":"(https://i\.pinimg\.com/[^"]+)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for url in matches:
                clean_url = url.replace('\\u002F', '/').replace('\\', '')
                
                # Katta rasm olish
                if '236x' in clean_url:
                    clean_url = clean_url.replace('236x', 'originals')
                elif '474x' in clean_url:
                    clean_url = clean_url.replace('474x', 'originals')
                
                if 'originals' in clean_url and clean_url not in images:
                    images.append(clean_url)
        
        return images
    
    def extract_videos(self, html_content):
        """HTML dan video URLlarini olish"""
        videos = []
        
        patterns = [
            r'"video_url":"([^"]+)"',
            r'src="([^"]+\.mp4[^"]*)"',
            r'contentUrl":"([^"]+\.mp4[^"]*)"',
            r'video-src="([^"]+)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for url in matches:
                clean_url = url.replace('\\u002F', '/').replace('\\', '')
                if 'mp4' in clean_url and clean_url not in videos:
                    videos.append(clean_url)
        
        return videos

# Downloader yaratish
downloader = PinterestDownloader()

# /start komandasi
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    welcome_text = f"""
🤖 Salom {user.first_name}!

Men Pinterest botiman. Menga Pinterest linkini yuboring, men rasmlar va videolarni yuklab beraman.

📎 *Qanday ishlatish:*
1. Pinterest dan istalgan post linkini nusxalang
2. Linkni shu yerga yuboring (matn bilan birga bo'lsa ham ishlaydi)
3. Men rasmlar va videolarni avtomatik yuklab beraman

📍 *Qabul qilinadigan formatlar:*
• `https://pinterest.com/pin/...`
• `https://pin.it/...`
• `Take a look! 📌 https://pin.it/...` 
• *Va boshqa matnlar bilan birga*

🚀 Link yuboring va boshlaymiz!
    """
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# /help komandasi
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
🆘 *Yordam*

*Qanday link yuborish mumkin:*
- To'g'ridan-to'g'ri link: `https://pin.it/abc123`
- Matn bilan birga: `Take a look! 📌 https://pin.it/abc123`
- Har qanday matn ichidagi Pinterest linki

*Misol linklar:*
- https://pin.it/3p0CYozXz
- https://pinterest.com/pin/123456789
- Look at this! https://pin.it/abc123

Agar link ishlamasa, boshqa formatda urinib ko'ring.
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

# Barcha xabarlarni qayta ishlash
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    
    # Linkni tozalab olish
    clean_url = downloader.clean_url(text)
    
    if not clean_url:
        bot.reply_to(message, 
            "❌ *Pinterest linki topilmadi!*\n\n"
            "Iltimos, quyidagi formatlardan birida link yuboring:\n"
            "• `https://pin.it/...`\n"
            "• `https://pinterest.com/pin/...`\n"
            "• `Take a look! 📌 https://pin.it/...`\n\n"
            "Link matn bilan birga bo'lsa ham ishlaydi!",
            parse_mode='Markdown'
        )
        return
    
    # Kutish xabarini yuborish
    wait_msg = bot.reply_to(message, 
        f"⏳ *Link topildi!*\n`{clean_url}`\n\n*Tahlil qilinmoqda...*", 
        parse_mode='Markdown'
    )
    
    try:
        # Kontentni yuklash
        images, videos = downloader.download_content(clean_url)
        
        # Natijalarni tekshirish
        if not images and not videos:
            bot.edit_message_text(
                "❌ *Hech narsa topilmadi!*\n\n"
                "*Sabablari:*\n"
                "• Link noto'g'ri yoki muddati o'tgan\n"
                "• Post o'chirilgan\n"
                "• Sayt bloklashi\n"
                "• Boshqa link bilan sinab ko'ring",
                message.chat.id,
                wait_msg.message_id,
                parse_mode='Markdown'
            )
            return
        
        # Yuklash haqida xabar
        total_files = len(images) + len(videos)
        bot.edit_message_text(
            f"✅ *{len(images)} ta rasm va {len(videos)} ta video topildi!*\n\n⏳ *Yuklanmoqda...*",
            message.chat.id,
            wait_msg.message_id,
            parse_mode='Markdown'
        )
        
        sent_count = 0
        
        # Rasmlarni yuborish
        if images:
            for i, img_url in enumerate(images):
                try:
                    bot.send_photo(
                        message.chat.id,
                        img_url,
                        caption=f"📸 Rasm {i+1}/{len(images)}"
                    )
                    sent_count += 1
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Rasm yuborish xatosi: {e}")
        
        # Videolarni yuborish
        if videos:
            for i, vid_url in enumerate(videos):
                try:
                    bot.send_video(
                        message.chat.id,
                        vid_url,
                        caption=f"🎥 Video {i+1}/{len(videos)}"
                    )
                    sent_count += 1
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Video yuborish xatosi: {e}")
        
        # Yakuniy xabar va reklama
        reklama_text = """
🎉 *Yuklash yakunlandi!*

📊 *{sent_count} ta fayl muvaffaqiyatli yuborildi*

━━━━━━━━━━━━━━━━━━
🎮 *PUBG MOBILE uchun ENG ARZON UC SERVICE*
👉 @ZakirShaX da!
━━━━━━━━━━━━━━━━━━

✅ *Sifat kafolati*
💰 *Eng arzon narxlar*
⚡ *Tez yetkazib berish*

💬 Murojaat: @ZakirShaX
"""

        bot.send_message(
            message.chat.id,
            reklama_text.format(sent_count=sent_count),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Umumiy xatolik: {e}")
        try:
            bot.edit_message_text(
                f"❌ *Xatolik yuz berdi:*\n`{str(e)[:200]}`",
                message.chat.id,
                wait_msg.message_id,
                parse_mode='Markdown'
            )
        except:
            bot.reply_to(message, f"❌ Xatolik yuz berdi: {str(e)[:200]}")

# Botni ishga tushirish
if __name__ == '__main__':
    logger.info("🤖 Bot ishga tushdi...")
    print("Bot ishga tushdi! Endi 'Take a look! 📌' bilan link yuborishingiz mumkin.")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot xatosi: {e}")
