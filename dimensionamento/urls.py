# dimensionamento/urls.py
from django.urls import path
from . import views

app_name = 'dimensionamento'

urlpatterns = [
    path('', views.listar_e_criar_cenarios, name='listar_criar_cenarios'),
    path('editar/<int:pk>/', views.editar_cenario_dimensionamento, name='editar_cenario'),

    # --- NOVA URL PARA O RELATÓRIO ---
    path('relatorio/<int:pk>/', views.relatorio_dimensionamento_cenario, name='relatorio_cenario'),
    # --- FIM DA NOVA URL ---
]