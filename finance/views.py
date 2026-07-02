import google.generativeai as genai
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import Transaction, Category, UserProfile
from django.conf import settings
from django.core.mail import send_mail

genai.configure(api_key=settings.GEMINI_API_KEY)

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        age_input = request.POST.get('age')
        initial_debt_input = request.POST.get('initial_debt')
        occupation = request.POST.get('occupation', '')
        income_source = request.POST.get('income_source', '')

        if password != confirm_password:
            return render(request, 'finance/register.html', {'error': 'Kiritilgan parollar o\'zaro mos kelmadi!'})

        if User.objects.filter(username=username).exists():
            return render(request, 'finance/register.html', {'error': 'Bu foydalanuvchi nomi band!'})

        try:
            age = int(age_input) if age_input else None
        except (ValueError, TypeError):
            age = None

        try:
            initial_debt = Decimal(initial_debt_input) if initial_debt_input else Decimal('0.00')
        except (ValueError, TypeError, InvalidOperation):
            initial_debt = Decimal('0.00')

        user = User.objects.create_user(username=username, email=email, password=password)

        UserProfile.objects.create(
            user=user,
            age=age,
            initial_debt=initial_debt,
            occupation=occupation,
            primary_income_source=income_source
        )

        if initial_debt > 0:
            Category.objects.create(user=user, name="Dastlabki qarz to'lovi", is_income=False)

        login(request, user)
        return redirect('dashboard')

    return render(request, 'finance/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'finance/login.html', {'error': 'Xato foydalanuvchi nomi yoki parol!'})
    return render(request, 'finance/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    transactions = Transaction.objects.filter(user=user)

    # Umumiy hisob-kitoblar
    total_income = transactions.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    current_balance = total_income - total_expense

    today = timezone.now().date()
    days_list = []
    daily_incomes = []
    daily_expenses = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days_list.append(day.strftime('%d-%b'))

        day_inc = transactions.filter(transaction_type='INCOME', created_at__date=day).aggregate(Sum('amount'))[
                      'amount__sum'] or 0
        day_exp = transactions.filter(transaction_type='EXPENSE', created_at__date=day).aggregate(Sum('amount'))[
                      'amount__sum'] or 0

        daily_incomes.append(float(day_inc))
        daily_expenses.append(float(day_exp))

    # Bar Chart uchun olingan va berilgan qarzlar ko'rsatkichi
    taken_debts = transactions.filter(transaction_type='INCOME', is_debt=True).aggregate(Sum('amount'))[
                      'amount__sum'] or 0
    given_debts = transactions.filter(transaction_type='EXPENSE', is_debt=True).aggregate(Sum('amount'))[
                      'amount__sum'] or 0
    initial_debt_val = profile.initial_debt or Decimal('0.00')
    total_taken_debt = float(taken_debts) + float(initial_debt_val)

    context = {
        'profile': profile,
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'current_balance': float(current_balance),
        'days_list': days_list,
        'daily_incomes': daily_incomes,
        'daily_expenses': daily_expenses,
        'total_taken_debt': total_taken_debt,
        'given_debts': float(given_debts),
    }
    return render(request, 'finance/dashboard.html', context)




@login_required(login_url='login')
def wallets_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        amount_input = request.POST.get('amount')
        try:
            amount = Decimal(amount_input)
        except (ValueError, TypeError, InvalidOperation):
            amount = Decimal('0.00')

        transaction_type = request.POST.get('transaction_type')
        category_name = request.POST.get('category_name')
        custom_category = request.POST.get('custom_category')
        description = request.POST.get('description', '')
        created_at_input = request.POST.get('created_at')
        is_debt = request.POST.get('is_debt') == 'on'
        debt_due_date = request.POST.get('debt_due_date')

        final_category_name = custom_category.strip() if custom_category else category_name

        category = None
        if final_category_name:
            is_income_bool = (transaction_type == 'INCOME')
            category, created = Category.objects.get_or_create(
                user=user, name=final_category_name, is_income=is_income_bool
            )

        if created_at_input:
            try:
                created_at = timezone.datetime.strptime(created_at_input, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    created_at = timezone.datetime.strptime(created_at_input, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    created_at = timezone.now()
            created_at = timezone.make_aware(created_at)
        else:
            created_at = timezone.now()

        # Dastlabki qarz to'lovi tanlansa, profil qarzidan kiritilgan summani ayiramiz
        if transaction_type == 'EXPENSE' and final_category_name == "Dastlabki qarz to'lovi":
            pay_amount = amount
            profile.initial_debt = max(Decimal('0.00'), profile.initial_debt - pay_amount)
            profile.save()

        debtor_creditor = request.POST.get('debtor_creditor', '')

        Transaction.objects.create(
            user=user, category=category, amount=amount, transaction_type=transaction_type,
            created_at=created_at, description=description, is_debt=is_debt,
            debt_due_date=debt_due_date if (is_debt and debt_due_date) else None,
            debtor_creditor=debtor_creditor if is_debt else None
        )
        return redirect('wallets')

    transactions = Transaction.objects.filter(user=user)

    # Agar foydalanuvchida qarz saqlanib turgan bo'lsa, qarz to'lovi kategoriyasi borligini tasdiqlaymiz
    initial_debt_val = profile.initial_debt or Decimal('0.00')
    if initial_debt_val > 0:
        Category.objects.get_or_create(user=user, name="Dastlabki qarz to'lovi", is_income=False)

    categories = Category.objects.filter(user=user)
    total_income = transactions.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    current_balance = total_income - total_expense

    context = {
        'categories': categories,
        'profile': profile,
        'current_balance': float(current_balance),
        'total_income': float(total_income),
        'total_expense': float(total_expense),
    }
    return render(request, 'finance/wallets.html', context)


@login_required(login_url='login')
def transactions_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    transactions = Transaction.objects.filter(user=user)
    categories = Category.objects.filter(user=user)

    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    category_filter = request.GET.get('category', '')

    if search_query:
        transactions = transactions.filter(description__icontains=search_query)
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)
    if category_filter:
        transactions = transactions.filter(category__name=category_filter)

    context = {
        'transactions': transactions,
        'categories': categories,
        'profile': profile,
        'search_query': search_query,
        'type_filter': type_filter,
        'category_filter': category_filter,
    }
    return render(request, 'finance/transactions.html', context)




@login_required(login_url='login')
def settings_view(request):
    """Foydalanuvchi profili, yoshi va dastlabki qarzini tahrirlash oynasi"""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    success_message = None
    error_message = None

    if request.method == 'POST':
        age = request.POST.get('age')
        initial_debt = request.POST.get('initial_debt')
        occupation = request.POST.get('occupation', '')
        income_source = request.POST.get('income_source', '')
        phone_number_raw = request.POST.get('phone_number', '')
        email = request.POST.get('email', '').strip()

        phone_number = "".join(c for c in phone_number_raw if c.isdigit() or c == '+').strip()

        if email:
            if User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                error_message = "Ushbu elektron pochta manzili allaqachon boshqa foydalanuvchiga tegishli!"

        if not error_message:
            if phone_number:
                if UserProfile.objects.filter(phone_number=phone_number).exclude(id=profile.id).exists():
                    error_message = "Ushbu telefon raqami allaqachon boshqa hisobga biriktirilgan!"
                else:
                    profile.phone_number = phone_number
            else:
                profile.phone_number = None

        if not error_message:
            if email:
                user.email = email
                user.save()
            if age:
                try:
                    profile.age = int(age)
                except (ValueError, TypeError):
                    pass
            if initial_debt:
                try:
                    profile.initial_debt = Decimal(initial_debt)
                except (ValueError, TypeError, InvalidOperation):
                    pass
            profile.occupation = occupation
            profile.primary_income_source = income_source
            profile.save()

            if float(initial_debt or 0) > 0:
                Category.objects.get_or_create(user=user, name="Dastlabki qarz to'lovi", is_income=False)

            success_message = "Profil ma'lumotlari muvaffaqiyatli yangilandi!"

    context = {
        'profile': profile,
        'success_message': success_message,
        'error_message': error_message,
    }
    return render(request, 'finance/settings.html', context)



@login_required(login_url='login')
def ai_analysis_page_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'finance/ai_analysis.html', {'profile': profile})


def build_ai_history_context(user, profile, transactions, total_income, total_expense, current_balance):
    """Foydalanuvchining barcha shaxsiy va moliyaviy ma'lumotlarini (paroldan tashqari) AI uchun to'liq formatda yig'ish"""
    history_text = (
        f"Foydalanuvchi ma'lumotlari:\n"
        f"- Username: {user.username}\n"
        f"- Email: {user.email or 'Kiritilmagan'}\n"
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
        
    return history_text


@login_required(login_url='login')
def get_ai_analysis(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    current_balance = total_income - total_expense

    if not transactions.exists():
        return JsonResponse({'analysis': "Hali hech qanday xarajat kiritmadingiz. Tahlil qilishga ma'lumot yo'q."})

    try:
        history_text = build_ai_history_context(user, profile, transactions, total_income, total_expense, current_balance)

        prompt = f"{history_text}\nYuqoridagi ma'lumotlar asosida foydalanuvchiga moliyaviy holati haqida juda qisqa (maksimal 4-5 ta gap), o'ta aniq, biroz keskin va achchiq haqiqat ko'rinishida tavsiya ber. Erkalatib o'tirma, xatolarini yuziga sol. O'zbek tilida yoz."

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return JsonResponse({'analysis': response.text})
    except Exception as e:
        return JsonResponse({'analysis': f"Xatolik yuz berdi: {str(e)}"}, status=500)


@login_required(login_url='login')
def get_ai_forecast(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    current_balance = total_income - total_expense

    if not transactions.exists():
        return JsonResponse({'forecast': "Bashorat qilish uchun ma'lumotlar yetarli emas."})

    try:
        history_text = build_ai_history_context(user, profile, transactions, total_income, total_expense, current_balance)

        prompt = f"""
        {history_text}
        Yuqoridagi pul oqimi tempiga qarab, ushbu foydalanuvchining kelgusi 30 kunlik moliyaviy bashoratini (Forecasting) yaratib ber. Agar u shu zaylda davom etsa, kelgusi oy oxirida balansi qayerga boradi? Dastlabki qarzini to'lahsga imkoniyati yetadimi yoki inqirozga uchraydimi? Matematik va mantiqiy taxminlarga tayangan holda juda qisqa (maksimal 3-4 gap), ogohlantiruvchi va jiddiy ohangda yoz. O'zbek tilida yoz.
        """

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return JsonResponse({'forecast': response.text})
    except Exception as e:
        return JsonResponse({'forecast': f"Xatolik yuz berdi: {str(e)}"}, status=500)




@login_required(login_url='login')
def debts_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    success_message = None
    error_message = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_debt':
            amount_input = request.POST.get('amount')
            transaction_type = request.POST.get('transaction_type')
            debtor_creditor = request.POST.get('debtor_creditor')
            debt_due_date = request.POST.get('debt_due_date')
            description = request.POST.get('description', '')

            try:
                amount = Decimal(amount_input)
                if amount <= 0:
                    raise ValueError
            except (ValueError, TypeError, InvalidOperation):
                error_message = "Iltimos, to'g'ri va musbat miqdor kiriting!"
                amount = None

            if not debtor_creditor:
                error_message = "Ism yoki tashkilot nomini kiritish majburiy!"

            if not error_message and amount:
                is_income = (transaction_type == 'INCOME')
                category, _ = Category.objects.get_or_create(
                    user=user, name="Qarzlar", is_income=is_income
                )

                Transaction.objects.create(
                    user=user,
                    category=category,
                    amount=amount,
                    transaction_type=transaction_type,
                    is_debt=True,
                    is_debt_cleared=False,
                    debt_due_date=debt_due_date if debt_due_date else None,
                    debtor_creditor=debtor_creditor,
                    description=description
                )
                success_message = "Qarz muvaffaqiyatli qo'shildi!"

        elif action == 'clear_debt':
            tx_id = request.POST.get('transaction_id')
            try:
                tx = Transaction.objects.get(id=tx_id, user=user)
                tx.is_debt_cleared = True
                tx.save()
                success_message = "Qarz to'landi (yopildi) deb belgilandi!"
            except Transaction.DoesNotExist:
                error_message = "Tranzaksiya topilmadi!"

        elif action == 'delete_debt':
            tx_id = request.POST.get('transaction_id')
            try:
                tx = Transaction.objects.get(id=tx_id, user=user)
                tx.delete()
                success_message = "Qarz tranzaksiyasi o'chirildi!"
            except Transaction.DoesNotExist:
                error_message = "Tranzaksiya topilmadi!"

    # Olingan qarzlar (INCOME, is_debt=True, is_debt_cleared=False)
    taken_debts = Transaction.objects.filter(user=user, transaction_type='INCOME', is_debt=True, is_debt_cleared=False)
    # Berilgan qarzlar (EXPENSE, is_debt=True, is_debt_cleared=False)
    given_debts = Transaction.objects.filter(user=user, transaction_type='EXPENSE', is_debt=True, is_debt_cleared=False)

    # Yopilgan qarzlar tarixi
    cleared_debts = Transaction.objects.filter(user=user, is_debt=True, is_debt_cleared=True)

    # Summa hisoblash
    initial_debt_val = profile.initial_debt or Decimal('0.00')
    total_taken_active = sum(t.amount for t in taken_debts) + initial_debt_val
    total_given_active = sum(t.amount for t in given_debts)

    context = {
        'profile': profile,
        'taken_debts': taken_debts,
        'given_debts': given_debts,
        'cleared_debts': cleared_debts,
        'total_taken_active': float(total_taken_active),
        'total_given_active': float(total_given_active),
        'success_message': success_message,
        'error_message': error_message,
    }
    return render(request, 'finance/debts.html', context)




def forget_password_view(request):
    success_message = None
    error_message = None
    import time
    import random

    # Qadamni session holatidan aniqlaymiz
    if request.session.get('reset_otp_verified'):
        step = 3
    elif request.session.get('reset_otp'):
        step = 2
    else:
        step = 1

    # Agar foydalanuvchi tiklashni boshidan boshlashni xohlasa (masalan, "Orqaga" bosganda)
    if request.GET.get('action') == 'reset':
        request.session.pop('reset_username', None)
        request.session.pop('reset_email', None)
        request.session.pop('reset_otp', None)
        request.session.pop('reset_otp_expiry', None)
        request.session.pop('reset_otp_verified', None)
        return redirect('forget_password')

    # Kodni qayta yuborish (Username va Email kiritmasdan, session ma'lumotlari orqali)
    if request.GET.get('action') == 'resend':
        reset_username = request.session.get('reset_username')
        reset_email = request.session.get('reset_email')
        if reset_username and reset_email:
            otp = "".join(str(random.randint(0, 9)) for _ in range(6))
            request.session['reset_otp'] = otp
            request.session['reset_otp_expiry'] = time.time() + 600

            subject = "MoliyaAI — Parolni tiklash tasdiqlash kodi"
            message = (
                f"Salom, {reset_username}!\n\n"
                f"Sizning MoliyaAI akkauntingiz parolini tiklash uchun yangi tasdiqlash kodi:\n"
                f"Tasdiqlash kodi: {otp}\n\n"
                f"Ushbu kod 10 daqiqa davomida amal qiladi. Agar buni siz so'ramagan bo'lsangiz, ushbu xatga e'tibor bermang."
            )
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [reset_email],
                    fail_silently=False,
                )
                success_message = "Yangi tasdiqlash kodi elektron pochtangizga muvaffaqiyatli qayta yuborildi!"
            except Exception as e:
                error_message = f"Email yuborishda xatolik yuz berdi: {str(e)}. Biroq tizim sinovi uchun yangi tasdiqlash kodi: {otp}"
            step = 2
        else:
            return redirect('forget_password')

    if request.method == 'POST':
        if step == 1:
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()

            if not username or not email:
                error_message = "Iltimos, foydalanuvchi nomi va elektron pochta manzilingizni kiriting!"
            else:
                user = User.objects.filter(username__iexact=username).first()
                if user and user.email and user.email.strip().lower() == email.lower():
                    # 6 xonali tasodifiy tasdiqlash kodi
                    otp = "".join(str(random.randint(0, 9)) for _ in range(6))

                    # Ma'lumotlarni sessionga yozamiz (10 daqiqa muddat bilan)
                    request.session['reset_username'] = user.username
                    request.session['reset_email'] = email
                    request.session['reset_otp'] = otp
                    request.session['reset_otp_expiry'] = time.time() + 600

                    # Email xabarini yuboramiz
                    subject = "MoliyaAI — Parolni tiklash tasdiqlash kodi"
                    message = (
                        f"Salom, {user.username}!\n\n"
                        f"Sizning MoliyaAI akkauntingiz parolini tiklash uchun tasdiqlash kodi:\n"
                        f"Tasdiqlash kodi: {otp}\n\n"
                        f"Ushbu kod 10 daqiqa davomida amal qiladi. Agar buni siz so'ramagan bo'lsangiz, ushbu xatga e'tibor bermang."
                    )
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                        success_message = "Tasdiqlash kodi elektron pochtangizga muvaffaqiyatli yuborildi!"
                        step = 2
                    except Exception as e:
                        error_message = f"Email yuborishda xatolik yuz berdi: {str(e)}. Biroq tizim sinovi uchun bir martalik tasdiqlash kodi: {otp}"
                        # Konsol pochtasi ishlayotgan bo'lsa yoki local bo'lsa, ikkinchi qadamga baribir o'tkazamiz
                        step = 2
                else:
                    error_message = "Kiritilgan foydalanuvchi nomi va elektron pochta manzili mos kelmadi!"

        elif step == 2:
            otp_entered = request.POST.get('otp', '').strip()
            session_otp = request.session.get('reset_otp')
            session_expiry = request.session.get('reset_otp_expiry', 0)

            if session_otp and otp_entered == session_otp:
                if time.time() < session_expiry:
                    request.session['reset_otp_verified'] = True
                    success_message = "Tasdiqlash kodi muvaffaqiyatli qabul qilindi! Endi yangi parolingizni belgilang."
                    step = 3
                else:
                    error_message = "Tasdiqlash kodining amal qilish muddati tugagan (10 daqiqa). Iltimos, boshidan boshlang!"
            else:
                error_message = "Tasdiqlash kodi noto'g'ri! Iltimos, qayta urinib ko'ring."

        elif step == 3:
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not password or not confirm_password:
                error_message = "Iltimos, yangi parolni kiriting!"
            elif password != confirm_password:
                error_message = "Kiritilgan parollar bir-biriga mos kelmadi!"
            elif len(password) < 6:
                error_message = "Parol uzunligi kamida 6 ta belgidan iborat bo'lishi kerak!"
            else:
                reset_username = request.session.get('reset_username')
                user = User.objects.filter(username=reset_username).first()
                if user:
                    # Yangi parolni o'rnatamiz
                    user.set_password(password)
                    user.save()

                    # Avtomatik kirishni amalga oshiramiz (login)
                    authenticated_user = authenticate(request, username=reset_username, password=password)
                    if authenticated_user is not None:
                        login(request, authenticated_user)

                    # Session ma'lumotlarini tozalaymiz
                    request.session.pop('reset_username', None)
                    request.session.pop('reset_email', None)
                    request.session.pop('reset_otp', None)
                    request.session.pop('reset_otp_expiry', None)
                    request.session.pop('reset_otp_verified', None)

                    return redirect('dashboard')
                else:
                    error_message = "Tizim foydalanuvchisini topib bo'lmadi. Iltimos, boshidan urinib ko'ring!"

    context = {
        'step': step,
        'success_message': success_message,
        'error_message': error_message,
        'reset_username': request.session.get('reset_username', ''),
        'reset_email': request.session.get('reset_email', ''),
    }
    return render(request, 'finance/forget_password.html', context)


# ==========================================
# 📱 MOBILE APP API ENDPOINTS (NATIVE APP)
# ==========================================
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import Transaction, Category

import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile

@csrf_exempt
def api_login_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Generate 6-digit OTP
            otp = f"{random.randint(100000, 999999)}"
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.login_otp = otp
            profile.login_otp_expiry = timezone.now() + timedelta(minutes=10)
            profile.save()
            
            # Send confirmation email
            subject = "MoliyaAI — Qurilmani tasdiqlash kodi"
            message = f"Salom {user.username}!\n\nMoliyaAI mobil ilovasiga kirish uchun tasdiqlash kodingiz: {otp}\nUshbu kod 10 daqiqa davomida faol."
            from_email = "MoliyaAI <noreply@upcode.uz>"
            recipient_list = [user.email]
            
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                return JsonResponse({
                    'success': True,
                    'otp_sent': True,
                    'message': 'Tasdiqlash kodi elektron pochtangizga yuborildi!'
                })
            except Exception as mail_err:
                return JsonResponse({
                    'success': False,
                    'error': f"Tasdiqlash kodini emailga yuborib bo'lmadi: {str(mail_err)}"
                }, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'Xato username yoki parol!'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_verify_otp_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username')
        otp = data.get('otp')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Foydalanuvchi topilmadi!'}, status=400)
            
        profile = getattr(user, 'profile', None)
        if profile is not None and profile.login_otp == otp:
            if profile.login_otp_expiry and timezone.now() < profile.login_otp_expiry:
                profile.login_otp = None  # Clear OTP
                profile.save()
                
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'username': user.username,
                    'email': user.email,
                    'user_id': user.id
                })
            else:
                return JsonResponse({'success': False, 'error': 'Tasdiqlash kodining muddati tugagan!'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Noto\'g\'ri tasdiqlash kodi!'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def api_transactions_view(request):
    user = request.user
    if not user.is_authenticated:
        user_id = request.headers.get('X-User-ID') or request.GET.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Foydalanuvchi topilmadi'}, status=401)
        else:
            return JsonResponse({'success': False, 'error': 'Avtorizatsiyadan o\'tilmagan'}, status=401)
            
    if request.method == 'GET':
        transactions = Transaction.objects.filter(user=user).order_by('-created_at')
        data = []
        for t in transactions:
            data.append({
                'id': t.id,
                'amount': float(t.amount),
                'transaction_type': t.transaction_type,
                'category': t.category.name if t.category else 'Boshqa',
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M'),
                'description': t.description or '',
                'is_debt': t.is_debt,
                'debtor_creditor': t.debtor_creditor or '',
                'is_debt_cleared': t.is_debt_cleared
            })
        return JsonResponse({'success': True, 'transactions': data})
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = float(data.get('amount'))
            t_type = data.get('transaction_type') # 'INCOME' or 'EXPENSE'
            category_name = data.get('category')
            description = data.get('description', '')
            
            category = None
            if category_name:
                is_income = (t_type == 'INCOME')
                category, _ = Category.objects.get_or_create(
                    user=user,
                    name=category_name,
                    is_income=is_income
                )
            
            t = Transaction.objects.create(
                user=user,
                category=category,
                amount=amount,
                transaction_type=t_type,
                description=description
            )
            return JsonResponse({
                'success': True,
                'transaction': {
                    'id': t.id,
                    'amount': float(t.amount),
                    'transaction_type': t.transaction_type,
                    'category': t.category.name if t.category else 'Boshqa',
                    'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def api_summary_view(request):
    user = request.user
    if not user.is_authenticated:
        user_id = request.headers.get('X-User-ID') or request.GET.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Foydalanuvchi topilmadi'}, status=401)
        else:
            return JsonResponse({'success': False, 'error': 'Avtorizatsiyadan o\'tilmagan'}, status=401)
            
    transactions = Transaction.objects.filter(user=user)
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    current_balance = total_income - total_expense
    
    return JsonResponse({
        'success': True,
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'current_balance': float(current_balance)
    })

from django.shortcuts import redirect

def download_apk_view(request):
    return redirect('https://tmpfiles.org/dl/wVwdbmqSIy90/moliyaai.apk')