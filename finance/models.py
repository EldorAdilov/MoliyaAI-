from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.PositiveIntegerField(null=True, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    primary_income_source = models.CharField(max_length=150, blank=True)
    initial_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    login_otp = models.CharField(max_length=6, blank=True, null=True)
    login_otp_expiry = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Profili"


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100)
    is_income = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'name', 'is_income')

    def __str__(self):
        type_str = "Kirim" if self.is_income else "Chiqim"
        return f"{self.name} ({type_str})"


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('INCOME', 'Kirim'),
        ('EXPENSE', 'Chiqim'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    is_debt = models.BooleanField(default=False)
    debt_due_date = models.DateField(null=True, blank=True)
    is_debt_cleared = models.BooleanField(default=False)
    debtor_creditor = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} | {self.transaction_type} | {self.amount}"

    class Meta:
        ordering = ['-created_at']