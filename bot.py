import os
import sys
import django
from decimal import Decimal, InvalidOperation

# Django muhitini sozlash
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import telebot
from telebot import types
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from finance.models import UserProfile, Transaction, Category
import google.generativeai as genai

# Gemini API sozlash
genai.configure(api_key=settings.GEMINI_API_KEY)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN or TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("ILTIMOS, .env faylida Telegram bot tokenini o'rnating!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

# Vaqtinchalik foydalanuvchi ma'lumotlarini saqlash uchun lug'at (Tranzaksiya yaratish jarayoni uchun)
user_steps = {}

def get_profile_by_chat_id(chat_id):
    """Chat ID orqali foydalanuvchi profilini olish"""
    try:
        return UserProfile.objects.get(telegram_chat_id=str(chat_id))
    except UserProfile.DoesNotExist:
        return None

def send_main_menu(chat_id, text="Quyidagi bo'limlardan birini tanlang:"):
    """Bosh menyuni yuborish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📊 Balans va hisobotlar")
    btn2 = types.KeyboardButton("💸 Yangi operatsiya")
    btn3 = types.KeyboardButton("🤝 Qarzlarim")
    btn4 = types.KeyboardButton("🧠 Moliya AI")
    btn5 = types.KeyboardButton("🔀 So'nggi tranzaksiyalar")
    btn6 = types.KeyboardButton("ℹ️ Profil")
    btn7 = types.KeyboardButton("❌ Bog'lanishni uzish")
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5, btn6)
    markup.row(btn7)
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)

    if profile:
        send_main_menu(chat_id, f"Xush kelibsiz, *{profile.user.username}*! Siz tizimga muvaffaqiyatli bog'langansiz.")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = types.KeyboardButton("📱 Telefon raqamni ulash", request_contact=True)
        markup.add(btn)
        welcome_text = (
            "⚡ *MoliyaAI tizimiga xush kelibsiz!*\n\n"
            "Ushbu bot yordamida moliyaviy hisoblaringizni boshqarishingiz va AI tahlillarini olishingiz mumkin.\n\n"
            "🌐 *Web sahifa manzili:* https://moliya.upcode.uz\n\n"
            "⚠️ *Muhim:* Botdan foydalanish uchun avval web sahifada ro'yxatdan o'tgan bo'lishingiz va Sozlamalar bo'limida telefon raqamingizni kiritgan bo'lishingiz lozim.\n\n"
            "Davom etish uchun quyidagi tugma orqali kontaktingizni yuboring:"
        )
        bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if not message.contact:
        return

    phone = message.contact.phone_number
    # Faqat raqamlarni qoldiramiz
    phone_digits = "".join(c for c in phone if c.isdigit())

    # Bazadan mos raqamni izlaymiz (raqam boshidagi '+' belgisi bilan yoki belgisiz saqlangan bo'lishi mumkin)
    profile = UserProfile.objects.filter(phone_number=phone_digits).first()
    if not profile:
        profile = UserProfile.objects.filter(phone_number='+' + phone_digits).first()
    if not profile and phone_digits.startswith('998') and len(phone_digits) == 12:
        # Boshida + bo'lmagan 998 formatini ham tekshiramiz
        profile = UserProfile.objects.filter(phone_number=phone_digits[3:]).first()

    if profile:
        profile.telegram_chat_id = str(chat_id)
        profile.save()
        send_main_menu(chat_id, f"🎉 *Tabriklaymiz!* Tizim bilan ulanish o'rnatildi.\nFoydalanuvchi: *{profile.user.username}*")
    else:
        bot.send_message(
            chat_id,
            "❌ *Akkaunt topilmadi.*\n\n"
            "Siz kiritgan telefon raqami web-tizimda ro'yxatdan o'tkazilmagan.\n\n"
            "🌐 *Web sahifa manzili:* https://moliya.upcode.uz\n"
            "Iltimos, web ilovaga kirib, *Sozlamalar* bo'limidan telefon raqamingizni to'g'ri kiriting va qayta urinib ko'ring.",
            parse_mode="Markdown"
        )

# ==========================================
# 📊 BALANS VA HISOBOTLAR
# ==========================================
@bot.message_handler(func=lambda message: message.text == "📊 Balans va hisobotlar")
def handle_balance(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    transactions = Transaction.objects.filter(user=profile.user)
    total_income = transactions.filter(transaction_type='INCOME').aggregate(Sum=Sum('amount'))['Sum'] or Decimal('0.00')
    total_expense = transactions.filter(transaction_type='EXPENSE').aggregate(Sum=Sum('amount'))['Sum'] or Decimal('0.00')
    current_balance = total_income - total_expense
    initial_debt_val = profile.initial_debt or Decimal('0.00')

    report = (
        "📊 *Moliyaviy Hisobotlar paneli*\n\n"
        f"💳 *Sof Balansingiz:* `{current_balance:,.2f} UZS`\n"
        f"📈 *Umumiy Kirim:* `+{total_income:,.2f} UZS`\n"
        f"📉 *Umumiy Chiqim:* `-{total_expense:,.2f} UZS`\n"
        f"⚠️ *Dastlabki Qarz majburiyati:* `{initial_debt_val:,.2f} UZS`\n"
    )
    bot.send_message(chat_id, report, parse_mode="Markdown")

# ==========================================
# 🤝 QARZLARIM HISOBOTI
# ==========================================
@bot.message_handler(func=lambda message: message.text == "🤝 Qarzlarim")
def handle_debts(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    # Olingan qarzlar (INCOME + is_debt=True)
    taken_debts = Transaction.objects.filter(user=profile.user, transaction_type='INCOME', is_debt=True)
    # Berilgan qarzlar (EXPENSE + is_debt=True)
    given_debts = Transaction.objects.filter(user=profile.user, transaction_type='EXPENSE', is_debt=True)

    text = "🤝 *Qarz majburiyatlari va hisobotlari:*\n\n"

    # Olingan qarzlar ro'yxati
    text += "🔴 *Siz olgan (qaytarishingiz kerak bo'lgan) qarzlar:*\n"
    initial_debt_val = profile.initial_debt or Decimal('0.00')
    if initial_debt_val > 0:
        text += f"• *Dastlabki qarz majburiyati:* `{initial_debt_val:,.2f} UZS`\n"

    if taken_debts.exists():
        for t in taken_debts:
            due_str = t.debt_due_date.strftime('%d.%m.%Y') if t.debt_due_date else "Muddatsiz"
            created_str = t.created_at.strftime('%d.%m.%Y')
            person = f" | Kimdan: *{t.debtor_creditor}*" if t.debtor_creditor else ""
            desc = f" ({t.description})" if t.description else ""
            text += f"• *{t.amount:,.2f} UZS*{desc}{person}\n  📅 Olingan vaqt: _{created_str}_ | ⏳ Muddat: *{due_str}*\n"
    elif initial_debt_val == 0:
        text += "• Siz olgan qarzlar mavjud emas.\n"
    text += "\n"

    # Berilgan qarzlar ro'yxati
    text += "🟢 *Siz bergan (qaytarib olishingiz kerak bo'lgan) qarzlar:*\n"
    if given_debts.exists():
        for t in given_debts:
            due_str = t.debt_due_date.strftime('%d.%m.%Y') if t.debt_due_date else "Muddatsiz"
            created_str = t.created_at.strftime('%d.%m.%Y')
            person = f" | Kimga: *{t.debtor_creditor}*" if t.debtor_creditor else ""
            desc = f" ({t.description})" if t.description else ""
            text += f"• *{t.amount:,.2f} UZS*{desc}{person}\n  📅 Berilgan vaqt: _{created_str}_ | ⏳ Muddat: *{due_str}*\n"
    else:
        text += "• Siz bergan qarzlar mavjud emas.\n"

    bot.send_message(chat_id, text, parse_mode="Markdown")

# ==========================================
# 🔀 SO'NGGI TRANZAKSIYALAR
# ==========================================
@bot.message_handler(func=lambda message: message.text == "🔀 So'nggi tranzaksiyalar")
def handle_recent_transactions(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    txs = Transaction.objects.filter(user=profile.user)[:5]
    if not txs.exists():
        bot.send_message(chat_id, "ℹ️ Hozircha hech qanday tranzaksiyalar tarixi mavjud emas.")
        return

    text = "🔀 *So'nggi 5 ta operatsiya tarixi:*\n\n"
    for i, t in enumerate(txs, 1):
        sign = "+" if t.transaction_type == 'INCOME' else "-"
        date_str = t.created_at.strftime('%d.%m.%Y %H:%M')
        cat_name = t.category.name if t.category else "Boshqa"
        desc = f" ({t.description[:20]})" if t.description else ""
        text += f"{i}. *{sign}{t.amount:,.2f} UZS* | {cat_name}{desc}\n   📅 _{date_str}_\n\n"

    bot.send_message(chat_id, text, parse_mode="Markdown")

# ==========================================
# ℹ️ PROFIL MA'LUMOTLARI
# ==========================================
@bot.message_handler(func=lambda message: message.text == "ℹ️ Profil")
def handle_profile(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    profile_text = (
        "👤 *Foydalanuvchi Profili:*\n\n"
        f"• *Username:* {profile.user.username}\n"
        f"• *Yosh:* {profile.age if profile.age else 'Kiritilmagan'}\n"
        f"• *Kasbi:* {profile.occupation if profile.occupation else 'Kiritilmagan'}\n"
        f"• *Daromad manbai:* {profile.primary_income_source if profile.primary_income_source else 'Kiritilmagan'}\n"
        f"• *Telefon:* {profile.phone_number if profile.phone_number else 'Kiritilmagan'}\n"
    )
    bot.send_message(chat_id, profile_text, parse_mode="Markdown")

# ==========================================
# ❌ BOG'LANISHNI UZISH
# ==========================================
@bot.message_handler(func=lambda message: message.text == "❌ Bog'lanishni uzish")
def handle_unlink(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    profile.telegram_chat_id = None
    profile.save()

    markup = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "🔌 Telegram chat ID hisobingizdan uzildi. Botdan foydalanish uchun qayta ulanishingiz kerak.", reply_markup=markup)

# ==========================================
# 🧠 MOLIYA AI
# ==========================================
@bot.message_handler(func=lambda message: message.text == "🧠 Moliya AI")
def handle_ai_menu(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("💥 Achchiq haqiqat (Tahlil)")
    btn2 = types.KeyboardButton("🔮 Kelajak bashorati")
    btn3 = types.KeyboardButton("⬅️ Bosh menyuga qaytish")
    markup.add(btn1, btn2)
    markup.add(btn3)
    bot.send_message(chat_id, "🧠 *Moliya AI Hub* bo'limi. Tahlil turini tanlang:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⬅️ Bosh menyuga qaytish")
def handle_back_to_menu(message):
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text in ["💥 Achchiq haqiqat (Tahlil)", "🔮 Kelajak bashorati"])
def handle_ai_request(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    request_type = "tahlil" if "Achchiq" in message.text else "bashorat"
    
    transactions = Transaction.objects.filter(user=profile.user)
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    current_balance = total_income - total_expense

    if not transactions.exists():
        bot.send_message(chat_id, "Hali hech qanday xarajat kiritmagansiz. Tahlil qilishga ma'lumot yo'q.")
        return

    msg = bot.send_message(chat_id, "⏳ *AI ma'lumotlarni skanerlamoqda...* Iltimos kutib turing.", parse_mode="Markdown")

    try:
        # Foydalanuvchining barcha shaxsiy va moliyaviy ma'lumotlarini (paroldan tashqari) to'liq yig'amiz
        history_text = (
            f"Foydalanuvchi ma'lumotlari:\n"
            f"- Username: {profile.user.username}\n"
            f"- Email: {profile.user.email or 'Kiritilmagan'}\n"
            f"- Yosh: {profile.age or 'Nomalum'} yosh\n"
            f"- Kasbi: {profile.occupation or 'Kiritilmagan'}\n"
            f"- Daromad manbai: {profile.primary_income_source or 'Kiritilmagan'}\n"
            f"- Telefon raqam: {profile.phone_number or 'Kiritilmagan'}\n"
            f"- Boshlang'ich qarz: {profile.initial_debt or 0} UZS\n\n"
            f"Moliyaviy ko'rsatkichlar:\n"
            f"- Jami kirim: {total_income} UZS\n"
            f"- Jami chiqim: {total_expense} UZS\n"
            f"- Sof balans (Kirim - Chiqim): {current_balance} UZS\n\n"
            f"Barcha operatsiyalar logi (Eski va yangi amallar):\n"
        )
        for i, t in enumerate(transactions.order_by('created_at'), 1):
            cat = t.category.name if t.category else "Boshqa"
            t_type = "Kirim" if t.transaction_type == 'INCOME' else "Chiqim"
            debt_status = ""
            if t.is_debt:
                status = "Yopilgan" if t.is_debt_cleared else "Faol"
                if t.transaction_type == 'INCOME':
                    debt_type = f"Olingan qarz (Menga qarz berishgan / Boshqadan qarz olganman, kimdan: {t.debtor_creditor or 'Nomalum'})"
                else:
                    debt_type = f"Berilgan qarz (Men qarz berganman / Boshqa odam menga qaytarishi kerak, kimga: {t.debtor_creditor or 'Nomalum'})"
                debt_status = f" | [Turi: {debt_type}, Holati: {status}, Muddati: {t.debt_due_date or 'Nomalum'}]"
            
            desc = f" | Izoh: {t.description}" if t.description else ""
            history_text += f"{i}. {t_type}: {t.amount} UZS | Kategoriya: {cat} | Sana: {t.created_at.strftime('%Y-%m-%d %H:%M')}{debt_status}{desc}\n"

        if request_type == "tahlil":
            prompt = f"{history_text}\nYuqoridagi ma'lumotlar asosida foydalanuvchiga moliyaviy holati haqida juda qisqa (maksimal 3-4 ta gap), o'ta aniq, biroz keskin va achchiq haqiqat ko'rinishida tavsiya ber. Erkalatib o'tirma, xatolarini yuziga sol. O'zbek tilida yoz."
        else:
            prompt = f"""
            {history_text}
            Yuqoridagi pul oqimi tempiga qarab, ushbu foydalanuvchining kelgusi 30 kunlik moliyaviy bashoratini (Forecasting) yaratib ber. Agar u shu zaylda davom etsa, kelgusi oy oxirida balansi qayerga boradi? Dastlabki qarzini to'lahsga imkoniyati yetadimi yoki inqirozga uchraydimi? Matematik va mantiqiy taxminlarga tayangan holda juda qisqa (maksimal 3-4 gap), ogohlantiruvchi va jiddiy ohangda yoz. O'zbek tilida yoz.
            """

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        icon = "💀 Achchiq Haqiqat:\n\n" if request_type == "tahlil" else "🔮 Kelajak Bashorati:\n\n"
        bot.edit_message_text(icon + response.text, chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik yuz berdi: {str(e)}", chat_id, msg.message_id)

# ==========================================
# 💸 YANGI OPERATSIYA QO'SHISH WIZARD
# ==========================================
@bot.message_handler(func=lambda message: message.text == "💸 Yangi operatsiya")
def start_add_transaction(message):
    chat_id = message.chat.id
    profile = get_profile_by_chat_id(chat_id)
    if not profile:
        start_command(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton("[+] Kirim (Income)")
    btn2 = types.KeyboardButton("[-] Chiqim (Expense)")
    btn3 = types.KeyboardButton("❌ Bekor qilish")
    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(chat_id, "💸 Yangi tranzaksiya turini tanlang:", reply_markup=markup)
    bot.register_next_step_handler(message, process_type_step)

def process_type_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    tx_type = None
    if "Kirim" in text:
        tx_type = "INCOME"
    elif "Chiqim" in text:
        tx_type = "EXPENSE"

    if not tx_type:
        bot.send_message(chat_id, "Iltimos, tugmalardan birini tanlang.")
        bot.register_next_step_handler(message, process_type_step)
        return

    user_steps[chat_id] = {'type': tx_type}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    bot.send_message(chat_id, "💰 Tranzaksiya summasini kiriting (UZS):", reply_markup=markup)
    bot.register_next_step_handler(message, process_amount_step)

def process_amount_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    try:
        amount = Decimal(text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        bot.send_message(chat_id, "❌ Noto'g'ri miqdor kiritildi. Iltimos, faqat musbat son kiriting:")
        bot.register_next_step_handler(message, process_amount_step)
        return

    user_steps[chat_id]['amount'] = amount
    profile = get_profile_by_chat_id(chat_id)
    
    # Kategoriya ro'yxatini yuklash
    is_income = (user_steps[chat_id]['type'] == "INCOME")
    categories = Category.objects.filter(user=profile.user, is_income=is_income)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in categories:
        markup.add(types.KeyboardButton(cat.name))
    markup.add(types.KeyboardButton("🆕 Yangi kategoriya ochish"))
    markup.add(types.KeyboardButton("❌ Bekor qilish"))

    bot.send_message(chat_id, "📂 Kategoriyani tanlang yoki yangi kategoriya yozishni bosing:", reply_markup=markup)
    bot.register_next_step_handler(message, process_category_step)

def process_category_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    if text == "🆕 Yangi kategoriya ochish":
        bot.send_message(chat_id, "🆕 Yangi kategoriya nomini yozing:")
        bot.register_next_step_handler(message, process_custom_category_step)
        return

    user_steps[chat_id]['category'] = text
    ask_description(chat_id)

def process_custom_category_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    if not text.strip():
        bot.send_message(chat_id, "Kategoriya nomi bo'sh bo'lishi mumkin emas. Qaytadan yozing:")
        bot.register_next_step_handler(message, process_custom_category_step)
        return

    user_steps[chat_id]['category'] = text.strip()
    ask_description(chat_id)

def ask_description(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⏭️ Izohni o'tkazib yuborish"))
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    bot.send_message(chat_id, "📝 Tranzaksiyaga qisqa izoh yozing (ixtiyoriy):", reply_markup=markup)
    bot.register_next_step_handler(bot.send_message(chat_id, "..."), process_description_step)

def process_description_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    if text == "⏭️ Izohni o'tkazib yuborish":
        user_steps[chat_id]['description'] = ""
    else:
        user_steps[chat_id]['description'] = text

    # Qarz haqida so'raymiz
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Ha, bu qarz"), types.KeyboardButton("Yo'q, qarz emas"))
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    bot.send_message(chat_id, "❓ Ushbu amalni qarz sifatida belgilaymizmi?", reply_markup=markup)
    bot.register_next_step_handler(message, process_is_debt_step)

def process_is_debt_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    if "Ha" in text:
        user_steps[chat_id]['is_debt'] = True
        type_val = user_steps[chat_id]['type']
        if type_val == "INCOME":
            prompt = "👤 *Kimdan oldingiz?* (Ism yoki tashkilot nomi):"
        else:
            prompt = "👤 *Kimga berdingiz?* (Ism yoki tashkilot nomi):"
        bot.send_message(chat_id, prompt, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_debtor_creditor_step)
    else:
        user_steps[chat_id]['is_debt'] = False
        user_steps[chat_id]['debt_due_date'] = None
        user_steps[chat_id]['debtor_creditor'] = None
        save_transaction(chat_id)

def process_debtor_creditor_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    user_steps[chat_id]['debtor_creditor'] = text.strip()
    bot.send_message(chat_id, "📅 Qarzni qaytarish muddatini yozing (Masalan: YYYY-MM-DD):")
    bot.register_next_step_handler(message, process_debt_date_step)

def process_debt_date_step(message):
    chat_id = message.chat.id
    text = message.text

    if text == "❌ Bekor qilish" or text == "/start":
        send_main_menu(chat_id, "Operatsiya bekor qilindi.")
        return

    try:
        due_date = timezone.datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        bot.send_message(chat_id, "❌ Noto'g'ri sana formati. Iltimos, YYYY-MM-DD formatida yozing (masalan: 2026-08-30):")
        bot.register_next_step_handler(message, process_debt_date_step)
        return

    user_steps[chat_id]['debt_due_date'] = due_date
    save_transaction(chat_id)

def save_transaction(chat_id):
    profile = get_profile_by_chat_id(chat_id)
    data = user_steps.get(chat_id)
    if not profile or not data:
        send_main_menu(chat_id, "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
        return

    is_income_bool = (data['type'] == "INCOME")
    
    # Kategoriyani topish yoki yaratish
    category = None
    if data['category']:
        category, _ = Category.objects.get_or_create(
            user=profile.user, name=data['category'], is_income=is_income_bool
        )

    # Dastlabki qarz to'lovi tekshiruvi
    if data['type'] == 'EXPENSE' and data['category'] == "Dastlabki qarz to'lovi":
        initial_debt_val = profile.initial_debt or Decimal('0.00')
        profile.initial_debt = max(Decimal('0.00'), initial_debt_val - data['amount'])
        profile.save()

    Transaction.objects.create(
        user=profile.user,
        category=category,
        amount=data['amount'],
        transaction_type=data['type'],
        description=data['description'],
        is_debt=data['is_debt'],
        debt_due_date=data['debt_due_date'],
        debtor_creditor=data.get('debtor_creditor')
    )

    # Oqimni tozalash
    user_steps.pop(chat_id, None)
    
    send_main_menu(chat_id, "✅ *Muvaffaqiyatli saqlandi!* Operatsiya MoliyaAI bazasiga muvaffaqiyatli yozildi.")

# ==========================================
# RUN THE BOT
# ==========================================
if __name__ == '__main__':
    print("MoliyaAI Telegram boti ishga tushdi...")
    bot.infinity_polling()
