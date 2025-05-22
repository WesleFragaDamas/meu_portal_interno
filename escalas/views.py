# escalas/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.forms import modelformset_factory
from django.contrib import messages
from django.db import transaction
import datetime

from dimensionamento.models import CenarioDimensionamento, IntervaloVolume
from .models import AlocacaoTurno, TipoTurno
from .forms import AlocacaoTurnoForm
from .logic import calcular_cobertura_e_saldo_com_sla  # NOME DA FUNÇÃO ATUALIZADO


def planejar_escalas_cenario(request, cenario_pk):
    cenario = get_object_or_404(CenarioDimensionamento, pk=cenario_pk)
    if not IntervaloVolume.objects.filter(cenario=cenario).exists() or \
            cenario.tipo_calculo == 'ATIVO_META':
        messages.warning(request, f"O cenário '{cenario.nome_cenario}' não pode ter escalas planejadas aqui.")
        return redirect(reverse('dimensionamento:editar_cenario', kwargs={'pk': cenario.pk}))

    AlocacaoTurnoFormSet = modelformset_factory(
        AlocacaoTurno, form=AlocacaoTurnoForm, extra=1, can_delete=True
    )

    intervalos_dimensionamento = IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio')
    necessidade_por_intervalo_dict = {
        iv.hora_inicio: iv.agentes_com_shrinkage if iv.agentes_com_shrinkage is not None else 0
        for iv in intervalos_dimensionamento
    }
    total_horas_agente_necessarias = sum(val for val in necessidade_por_intervalo_dict.values()) * 0.5

    cobertura_calculada_lista = [0.0] * 48
    saldo_calculado_lista = [-necessidade_por_intervalo_dict.get(datetime.time(hour=i // 2, minute=(i % 2) * 30), 0) for
                             i in range(48)]
    sla_projetado_cobertura_lista = [None] * 48  # NOVA LISTA
    total_agentes_alocados = 0
    total_horas_agente_cobertas = 0.0
    eficiencia_escala_percentual = 0.0

    if request.method == 'POST':
        formset = AlocacaoTurnoFormSet(request.POST,
                                       queryset=AlocacaoTurno.objects.filter(cenario_dimensionamento=cenario).order_by(
                                           'hora_inicio_efetiva_turno'))
        if formset.is_valid():
            with transaction.atomic():
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.cenario_dimensionamento = cenario
                    instance.save()
                for obj in formset.deleted_objects: obj.delete()
            messages.success(request, "Alocações de turno salvas!")
            return redirect(reverse('escalas:planejar_escalas', kwargs={'cenario_pk': cenario.pk}))
        else:
            messages.error(request, "Erro ao salvar alocações.")
            # Se o formset não for válido, ainda recalculamos a cobertura com o que está no banco
            alocacoes_atuais = AlocacaoTurno.objects.filter(cenario_dimensionamento=cenario).select_related(
                'tipo_turno')
            if alocacoes_atuais.exists():
                cobertura_calculada_lista, saldo_calculado_lista, sla_projetado_cobertura_lista, total_agentes_alocados = calcular_cobertura_e_saldo_com_sla(
                    cenario, alocacoes_atuais)
                for aloc in alocacoes_atuais:
                    if aloc.tipo_turno.tempo_produtivo_calculado:
                        total_horas_agente_cobertas += aloc.quantidade_agentes * (
                                    aloc.tipo_turno.tempo_produtivo_calculado.total_seconds() / 3600.0)

    else:  # GET
        formset = AlocacaoTurnoFormSet(queryset=AlocacaoTurno.objects.filter(cenario_dimensionamento=cenario).order_by(
            'hora_inicio_efetiva_turno'))
        alocacoes_atuais = AlocacaoTurno.objects.filter(cenario_dimensionamento=cenario).select_related('tipo_turno')
        if alocacoes_atuais.exists():
            cobertura_calculada_lista, saldo_calculado_lista, sla_projetado_cobertura_lista, total_agentes_alocados = calcular_cobertura_e_saldo_com_sla(
                cenario, alocacoes_atuais)
            for aloc in alocacoes_atuais:
                if aloc.tipo_turno.tempo_produtivo_calculado:
                    total_horas_agente_cobertas += aloc.quantidade_agentes * (
                                aloc.tipo_turno.tempo_produtivo_calculado.total_seconds() / 3600.0)

    if total_horas_agente_cobertas > 0 and total_horas_agente_necessarias > 0:
        eficiencia_escala_percentual = (total_horas_agente_necessarias / total_horas_agente_cobertas) * 100.0
    elif total_horas_agente_necessarias == 0 and total_horas_agente_cobertas == 0:
        eficiencia_escala_percentual = 100.0

    intervalos_display = []
    for i in range(48):
        hora_obj = datetime.time(hour=i // 2, minute=(i % 2) * 30)
        hora_str = hora_obj.strftime('%H:%M')
        necessidade_atual = necessidade_por_intervalo_dict.get(hora_obj, 0)
        cobertura_atual = cobertura_calculada_lista[i]
        saldo_atual = saldo_calculado_lista[i]
        sla_cobertura_atual = sla_projetado_cobertura_lista[i]  # NOVO DADO

        intervalos_display.append({
            'hora': hora_str,
            'necessidade': necessidade_atual,
            'cobertura': cobertura_atual,
            'saldo': saldo_atual,
            'sla_cobertura': sla_cobertura_atual  # NOVO DADO
        })

    context = {
        'cenario': cenario,
        'formset': formset,
        'intervalos_display': intervalos_display,
        'total_agentes_alocados': total_agentes_alocados,
        'total_horas_agente_necessarias': total_horas_agente_necessarias,
        'total_horas_agente_cobertas': total_horas_agente_cobertas,
        'eficiencia_escala_percentual': eficiencia_escala_percentual,
    }
    return render(request, 'escalas/planejar_escalas.html', context)