# escalas/urls.py
from django.urls import path
from . import views

app_name = 'escalas'

urlpatterns = [
    # URL para a página de planejamento de escalas de um cenário específico
    # cenario_pk será o ID do CenarioDimensionamento
    path('planejar/<int:cenario_pk>/', views.planejar_escalas_cenario, name='planejar_escalas'),
    # Poderíamos adicionar outras URLs aqui no futuro, como listar todos os planejamentos, etc.
]