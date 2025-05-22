# dimensionamento/admin.py
from django.contrib import admin
from .models import (
    CenarioDimensionamento,
    ComponenteShrinkage,
    ShrinkageAplicadoCenario,
    IntervaloVolume
)


@admin.register(ComponenteShrinkage)
class ComponenteShrinkageAdmin(admin.ModelAdmin):
    list_display = ('nome', 'percentual_padrao')
    search_fields = ('nome',)


class ShrinkageAplicadoCenarioInline(admin.TabularInline):
    model = ShrinkageAplicadoCenario
    extra = 1
    autocomplete_fields = ['componente']


@admin.register(CenarioDimensionamento)
class CenarioDimensionamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome_cenario',
        'tipo_calculo',  # ADICIONADO
        'data_referencia',
        'tma_segundos',
        'nivel_servico_meta_percentual',
        'concorrencia_chat',  # ADICIONADO
        'ftes_calculados_estimativa',
        'atualizado_em'
    )
    list_filter = ('data_referencia', 'tipo_calculo', 'atualizado_em')  # ADICIONADO tipo_calculo ao filtro
    search_fields = ('nome_cenario', 'data_referencia')
    ordering = ('-data_referencia', 'nome_cenario')

    # Definindo os campos a serem exibidos e sua ordem na tela de edição do admin
    # Isso também ajuda a agrupar campos logicamente
    fieldsets = (
        (None, {  # Seção principal sem título
            'fields': ('nome_cenario', 'data_referencia', 'tipo_calculo')
        }),
        ('Parâmetros Comuns/Jornada', {
            'fields': ('tma_segundos', 'tmp_segundos_padrao', 'jornada_padrao_duracao',
                       'tempo_produtivo_estimado_duracao')
        }),
        ('Parâmetros para Voz Receptivo / Chat Receptivo', {
            'classes': ('collapse',),  # Começa recolhido, útil se tiver muitos campos
            'fields': ('volume_chamadas_diario_base', 'nivel_servico_meta_percentual',
                       'tempo_atendimento_meta_segundos', 'concorrencia_chat')
        }),
        ('Parâmetros para Ativo por Meta', {
            'classes': ('collapse',),
            'fields': ('meta_campanha_ativo', 'taxa_contato_percentual_ativo', 'taxa_sucesso_contato_percentual_ativo',
                       'tempo_medio_discagem_espera_seg_ativo')
        }),
        ('Resultados Calculados (Read-Only)', {
            'classes': ('collapse',),
            'fields': ('fator_shrinkage_total_calculado_percentual', 'ftes_calculados_estimativa')
        }),
    )
    readonly_fields = (
        'criado_em',
        'atualizado_em',
        'fator_shrinkage_total_calculado_percentual',
        'ftes_calculados_estimativa',
    )
    inlines = [
        ShrinkageAplicadoCenarioInline,
    ]


@admin.register(IntervaloVolume)
class IntervaloVolumeAdmin(admin.ModelAdmin):
    list_display = (
        'cenario', 'hora_inicio', 'volume_estimado', 'agentes_erlang',
        'agentes_com_shrinkage', 'nivel_servico_projetado_percentual',
        'ocupacao_projetada_percentual'
    )
    list_filter = ('cenario__nome_cenario', 'hora_inicio')
    search_fields = ('cenario__nome_cenario',)
    readonly_fields = (
        'agentes_erlang', 'agentes_com_shrinkage',
        'nivel_servico_projetado_percentual', 'ocupacao_projetada_percentual'
    )
    ordering = ('cenario__nome_cenario', 'hora_inicio')