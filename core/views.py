# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required # IMPORTAR

@login_required # PROTEGER DASHBOARD
def dashboard(request):
    context = {'mensagem_bem_vindo': "Bem-vindo ao Portal de WFM Interno!"}
    return render(request, 'core/dashboard.html', context)