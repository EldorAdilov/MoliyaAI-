from django.urls import path
from .views import (register_view, login_view, logout_view,
                    dashboard_view, get_ai_analysis, wallets_view,
                    transactions_view, settings_view, get_ai_forecast, ai_analysis_page_view,
                    debts_view, forget_password_view,
                    api_login_view, api_transactions_view, api_summary_view)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('forget-password/', forget_password_view, name='forget_password'),

    # Mobile/Native App API endpoints
    path('api/login/', api_login_view, name='api_login'),
    path('api/transactions/mobile/', api_transactions_view, name='api_transactions_mobile'),
    path('api/summary/', api_summary_view, name='api_summary'),

    path('api/ai-analysis/', get_ai_analysis, name='get_ai_analysis'),
    path('wallets/', wallets_view, name='wallets'),
    path('transactions/', transactions_view, name='transactions'),
    path('debts/', debts_view, name='debts'),
    path('settings/', settings_view, name='settings'),
    path('ai-intelligence/', ai_analysis_page_view, name='ai_intelligence'),
    path('api/ai-forecast/', get_ai_forecast, name='get_ai_forecast'),
    path('', dashboard_view, name='dashboard'),
]