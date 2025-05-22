# escalas/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.forms import modelformset_factory
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required # IMPORTAR
import datetime

from dimensionamento.models import CenarioDimensionamento, IntervaloVolume
from .models import AlocacaoTurno, TipoTurno  # Certifique-se que TipoTurno está importado se usado no form
from .forms import AlocacaoTurnoForm
from .logic import calcular_cobertura_e_saldo_com_sla


def planejar_escalas_cenario(request, cenario_pk):
    cenario = get_object_or_404(CenarioDimensionamento, pk=cenario_pk)
    if not IntervaloVolume.objects.filter(cenario=cenario).exists() or \
            cenario.tipo_calculo == 'ATIVO_META':
        messages.warning(request,
                         f"O cenário '{cenario.nome_cenario}' não pode ter escalas planejadas aqui (deve ser Receptivo/Chat e ter o dimensionamento por intervalo calculado).")
        return redirect(reverse('dimensionamento:editar_cenario', kwargs={'pk': cenario.pk}))

    AlocacaoTurnoFormSet = modelformset_factory(
        AlocacaoTurno, form=AlocacaoTurnoForm, extra=1, can_delete=True
    )

    # Dados de Necessidade do Dimensionamento
    intervalos_dimensionamento = IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio')
    necessidade_por_intervalo_dict = {
        iv.hora_inicio: iv.agentes_com_shrinkage if iv.agentes_com_shrinkage is not None else 0
        for iv in intervalos_dimensionamento
    }
    total_horas_agente_necessarias = sum(val for val in necessidade_por_intervalo_dict.values()) * 0.5

    # --- INICIALIZAÇÃO DAS VARIÁVEIS DE RESULTADO DA ESCALA ---
    cobertura_calculada_lista = [0.0] * 48
    saldo_calculado_lista = [-necessidade_por_intervalo_dict.get(datetime.time(hour=i // 2, minute=(i % 2) * 30), 0) for
                             i in range(48)]
    sla_projetado_cobertura_lista = [None] * 48
    total_agentes_alocados = 0
    total_horas_agente_cobertas = 0.0
    eficiencia_escala_percentual = 0.0  # Default se não houver cobertura/necessidade
    sla_medio_dia_cobertura = None
    # --- FIM DA INICIALIZAÇÃO ---

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
            messages.error(request, "Erro ao salvar alocações. Verifique os dados.")
            # Se o formset não for válido, ainda recalculamos a cobertura com o que está no banco para reexibir
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
        # Calcular cobertura, saldo e totais para exibição inicial na carga GET
        alocacoes_atuais = AlocacaoTurno.objects.filter(cenario_dimensionamento=cenario).select_related('tipo_turno')
        if alocacoes_atuais.exists():
            cobertura_calculada_lista, saldo_calculado_lista, sla_projetado_cobertura_lista, total_agentes_alocados = calcular_cobertura_e_saldo_com_sla(
                cenario, alocacoes_atuais)
            for aloc in alocacoes_atuais:  # Recalcula total_horas_agente_cobertas
                if aloc.tipo_turno.tempo_produtivo_calculado:
                    total_horas_agente_cobertas += aloc.quantidade_agentes * (
                                aloc.tipo_turno.tempo_produtivo_calculado.total_seconds() / 3600.0)

    # Calcular eficiência e SLA médio após ter os valores de cobertura e horas (seja de POST falho ou GET)
    if total_horas_agente_cobertas > 0 and total_horas_agente_necessarias > 0:
        eficiencia_escala_percentual = (total_horas_agente_necessarias / total_horas_agente_cobertas) * 100.0
    elif total_horas_agente_necessarias == 0 and total_horas_agente_cobertas >= 0:  # Se não há necessidade, qualquer cobertura > 0 é "ok" ou 100% se cobertura=0
        eficiencia_escala_percentual = 100.0

    soma_sla_ponderado_cobertura = 0
    soma_volumes_para_sla_cobertura = 0
    if any(s is not None for s in sla_projetado_cobertura_lista):
        for i in range(48):
            hora_obj = datetime.time(hour=i // 2, minute=(i % 2) * 30)
            # Precisamos buscar o IntervaloVolume correspondente para pegar o volume_estimado
            intervalo_dim_data = IntervaloVolume.objects.filter(cenario=cenario, hora_inicio=hora_obj).first()

            if intervalo_dim_data and intervalo_dim_data.volume_estimado > 0 and sla_projetado_cobertura_lista[
                i] is not None:
                soma_sla_ponderado_cobertura += sla_projetado_cobertura_lista[i] * intervalo_dim_data.volume_estimado
                soma_volumes_para_sla_cobertura += intervalo_dim_data.volume_estimado

        if soma_volumes_para_sla_cobertura > 0:
            sla_medio_dia_cobertura = soma_sla_ponderado_cobertura / soma_volumes_para_sla_cobertura
        # Se todos os volumes são 0, mas há cobertura (ex: SLA foi 100 para esses), sla_medio pode ser 100
        elif all(iv.volume_estimado == 0 for iv in intervalos_dimensionamento if iv):
            sla_medio_dia_cobertura = 100.0

    intervalos_display = []
    for i in range(48):
        hora_obj = datetime.time(hour=i // 2, minute=(i % 2) * 30)
        hora_str = hora_obj.strftime('%H:%M')
        necessidade_atual = necessidade_por_intervalo_dict.get(hora_obj, 0)
        cobertura_atual = cobertura_calculada_lista[i]
        # O saldo já é calculado dentro de calcular_cobertura_e_saldo_com_sla,
        # mas se não houver alocações, saldo_calculado_lista pode não ter sido atualizado pelo retorno da função.
        # Por isso, recalculamos aqui para garantir.
        saldo_atual = cobertura_atual - necessidade_atual
        sla_cobertura_atual = sla_projetado_cobertura_lista[i]

        intervalos_display.append({
            'hora': hora_str,
            'necessidade': necessidade_atual,
            'cobertura': cobertura_atual,
            'saldo': saldo_atual,
            'sla_cobertura': sla_cobertura_atual
        })

    context = {
        'cenario': cenario,
        'formset': formset,
        'intervalos_display': intervalos_display,
        'total_agentes_alocados': total_agentes_alocados,
        'total_horas_agente_necessarias': total_horas_agente_necessarias,
        'total_horas_agente_cobertas': total_horas_agente_cobertas,
        'eficiencia_escala_percentual': eficiencia_escala_percentual,
        'sla_medio_dia_cobertura': sla_medio_dia_cobertura,
    }

    @login_required
    def planejar_escalas_cenario(request, cenario_pk):
        # ...
        pass

    return render(request, 'escalas/planejar_escalas.html', context)
