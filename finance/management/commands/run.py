import subprocess
import sys
import threading
import time
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "MoliyaAI Web Server va Telegram Botini bir vaqtda ishga tushirish"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("⚡ MoliyaAI Web Server va Telegram Bot ishga tushmoqda..."))
        
        # 1. Telegram bot jarayonini boshlash
        bot_process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # 2. Django Web server jarayonini boshlash
        server_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Matnlarni konsolga chop etish uchun yordamchi funksiya
        def log_stream(process, prefix, style_func):
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.stdout.write(style_func(f"[{prefix}] {line.strip()}"))
            except Exception:
                pass
            finally:
                process.stdout.close()

        # Chiqishlarni konsolga oqim ko'rinishida yuborish
        t_bot = threading.Thread(target=log_stream, args=(bot_process, 'BOT', self.style.WARNING))
        t_server = threading.Thread(target=log_stream, args=(server_process, 'WEB', self.style.HTTP_INFO))
        
        t_bot.daemon = True
        t_server.daemon = True
        
        t_bot.start()
        t_server.start()

        self.stdout.write(self.style.SUCCESS("✅ Ikkala tizim ham muvaffaqiyatli ishga tushirildi! To'xtatish uchun Ctrl+C ni bosing."))

        try:
            # Ikkala jarayondan biri tugashini yoki Ctrl+C bo'lishini kutamiz
            while True:
                if bot_process.poll() is not None:
                    self.stdout.write(self.style.ERROR("❌ Telegram Bot to'xtab qoldi!"))
                    break
                if server_process.poll() is not None:
                    self.stdout.write(self.style.ERROR("❌ Django Web Server to'xtab qoldi!"))
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.NOTICE("\n🛑 Tizimlar to'xtatilmoqda..."))
        finally:
            bot_process.terminate()
            server_process.terminate()
            bot_process.wait()
            server_process.wait()
            self.stdout.write(self.style.SUCCESS("👋 Xizmatlar o'chirildi."))
