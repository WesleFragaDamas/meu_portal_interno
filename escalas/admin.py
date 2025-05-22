# escalas/admin.py
from django.contrib import admin
from .models import TipoTurno, AlocacaoTurno


@admin.register(TipoTurno)
class TipoTurnoAdmin(admin.ModelAdmin):
    list_display = (
        'nome_turno',
        'duracao_jornada_total',
        'tempo_produtivo_calculado',
        'duracao_pausa1',
        'duracao_pausa2',
        'duracao_pausa3',
        'ativo'
    )
    list_filter = ('ativo',)
    search_fields = ('nome_turno',)
    ordering = ('nome_turno',)

    fieldsets = (
        (None, {
            'fields': ('nome_turno', 'duracao_jornada_total', 'ativo')
        }),
        ('Configuração da Pausa 1', {
            'fields': ('duracao_pausa1', 'inicio_pausa1_apos_x_tempo')
        }),
        ('Configuração da Pausa 2 (Principal)', {
            'fields': ('duracao_pausa2', 'inicio_pausa2_apos_x_tempo')
        }),
        ('Configuração da Pausa 3', {
            'fields': ('duracao_pausa3', 'inicio_pausa3_apos_x_tempo_da_pausa2')
        }),
        ('Calculado (Read-Only)', {
            'fields': ('tempo_produtivo_calculado',),
            'classes': ('collapse',)  # Pode começar recolhido
        }),
    )
    readonly_fields = ('tempo_produtivo_calculado',)


@admin.register(AlocacaoTurno)
class AlocacaoTurnoAdmin(admin.ModelAdmin):
    list_display = (
        'cenario_dimensionamento',
        'tipo_turno',
        'hora_inicio_efetiva_turno',
        'quantidade_agentes'
    )
    list_filter = ('cenario_dimensionamento__nome_cenario', 'tipo_turno__nome_turno', 'hora_inicio_efetiva_turno')
    search_fields = ('cenario_dimensionamento__nome_cenario', 'tipo_turno__nome_turno')
    autocomplete_fields = ['cenario_dimensionamento', 'tipo_turno']  # Facilita a seleção
    ordering = ('cenario_dimensionamento__data_referencia', 'hora_inicio_efetiva_turno')
    list_select_related = ('cenario_dimensionamento', 'tipo_turno')  # Otimiza queries

    # Para facilitar a edição, podemos restringir os campos ou usar fieldsets
    fields = ('cenario_dimensionamento', 'tipo_turno', 'hora_inicio_efetiva_turno', 'quantidade_agentes', 'observacoes')