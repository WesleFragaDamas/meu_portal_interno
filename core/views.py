# core/views.py
from django.shortcuts import render

def dashboard(request):
    # No futuro, podemos passar dados para o dashboard aqui
    context = {
        'mensagem_bem_vindo': "Bem-vindo ao Portal de WFM Interno!"
    }
    return render(request, 'core/dashboard.html', context)