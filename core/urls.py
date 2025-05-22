# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views  # Views de autenticação do Django
from . import views  # Nossas views do app core

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Nossa view de dashboard existente

    # URLs de Autenticação do Django
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/logged_out.html'), name='logout'),

    # No futuro, podemos adicionar URLs para mudança de senha, etc.
    # path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    # path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    # path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    # ... e assim por diante
]