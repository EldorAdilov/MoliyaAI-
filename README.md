# ⚡ MoliyaAI Hub

MoliyaAI — shaxsiy moliyaviy oqimlarni boshqarish, kirim-chiqim operatsiyalari jurnali, qarz majburiyatlari nazorati va sun'iy intellekt (Gemini AI) tahlili hamda bashoratiga asoslangan zamonaviy veb-ilova va Telegram bot tizimi.

---

## ✨ Asosiy Imkoniyatlar

1. **Boshqaruv Markazi (Dashboard):** 
   - Jami kirim, chiqim va sof balansning oson va qulay vizualizatsiyasi.
   - Kunlik pul oqimi va qarzlar holatining interaktiv grafiklari (Chart.js yordamida).
2. **Hamyonlar & Operatsiyalar:** 
   - Hisobdagi mablag'larni boshqarish.
   - Tranzaksiyalarni toifalarga (kategoriyalarga) bo'lib kiritish.
   - Amalni qarz sifatida belgilash (Kimdan/Kimga, muddatlari bilan).
3. **Qarzlar Boshqaruvi:** 
   - Olingan va berilgan faol qarzlar hisobi.
   - Qarzlar to'langandan so'ng ularni "Yopilgan" deb belgilash va o'chirish tarixi.
4. **🧠 Moliya AI Hub:**
   - **Achchiq Haqiqat (Tahlil):** Foydalanuvchining barcha moliyaviy xatti-harakatlarini, kasbini, daromadini va tranzaksiyalarini Gemini AI modeli yordamida keskin va ogohlantiruvchi ohangda tahlil qilish.
   - **Kelajak Bashorati:** Kelgusi 30 kunlik pul oqimi va inqiroz xavfi haqida matematik prognozlar berish.
5. **🌓 Kun/Tun Rejimi (Light & Dark Mode):**
   - Interfeysni Quyosh/Oy tugmasi yordamida oson almashtirish.
   - Foydalanuvchi tanlovi brauzer keshida (`localStorage`) saqlanadi.
6. **🔑 Forget Password Wizard (Ko'p bosqichli parolni tiklash):**
   - Username va Email mosligi tekshirilib, pochtaga bepul 6 xonali tasdiqlash kodi yuboriladi.
   - 2 daqiqalik kutish taymeri va kodni qayta yuborish (Resend) tugmasi mavjud.
7. **🤖 Telegram Bot Integratsiyasi (`bot.py`):**
   - Ilova bilan yagona ma'lumotlar bazasida ishlaydi.
   - Telegram orqali operatsiyalarni qo'shish va Moliya AI Hub tahlillarini to'g'ridan-to'g'ri olish imkoniyati.

---

## 🛠️ Texnologiyalar

- **Backend:** Python, Django 5.x
- **Frontend:** Vanilla CSS (Glassmorphism & Cyber-Neon dizayni), HTML5, JavaScript
- **Sun'iy Intellekt:** Gemini (gemini-2.5-flash) Generative AI API
- **Telegram Bot:** pyTelegramBotAPI
- **Ma'lumotlar Bazasi:** SQLite (Lokal uchun) / PostgreSQL (Server uchun)

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Loyihani yuklab olish va virtual muhitni yoqish
```bash
git clone https://github.com/EldorAdilov/MoliyaAI.git
cd MoliyaAI
python -m venv .venv
# Windows uchun
.venv\Scripts\activate
# Linux/Mac uchun
source .venv/bin/activate
```

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` sozlamalarini yaratish
Loyiha ildiz papkasida `.env` nomli fayl yarating va quyidagi ma'lumotlarni to'ldiring:
```env
# Django Settings
SECRET_KEY=sizning_django_secret_keyingiz
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Gemini AI API Key
GEMINI_API_KEY=sizning_gemini_api_kalitingiz

# Telegram Bot Token
TELEGRAM_BOT_TOKEN=sizning_bot_tokeningiz

# Gmail SMTP Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=sizning_emailingiz@gmail.com
EMAIL_HOST_PASSWORD=sizning_google_app_parolingiz
```

### 4. Baza migratsiyasini bajarish va administrator yaratish
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Loyihani va Botni ishga tushirish
* **Veb-ilovani ishga tushirish:**
  ```bash
  python manage.py runserver
  ```
* **Telegram botni alohida ishga tushirish (polling):**
  ```bash
  python bot.py
  ```

---

## 📄 Litsenziya

Ushbu loyiha MIT Litsenziyasi ostida yaratilgan.
