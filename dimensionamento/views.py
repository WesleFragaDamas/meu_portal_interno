# dimensionamento/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.forms import modelformset_factory, inlineformset_factory
from django.contrib import messages
from django.db import transaction
import datetime

from .models import CenarioDimensionamento, ComponenteShrinkage, ShrinkageAplicadoCenario, IntervaloVolume
from .forms import CenarioDimensionamentoForm, ShrinkageAplicadoCenarioForm, IntervaloVolumeForm
from .logic import processar_dimensionamento_completo_cenario

# View para Listar Cenários e Criar um Novo
def listar_e_criar_cenarios(request):
    cenarios = CenarioDimensionamento.objects.all().order_by('-data_referencia', 'nome_cenario')
    if request.method == 'POST':
        form_cenario = CenarioDimensionamentoForm(request.POST)
        if form_cenario.is_valid():
            novo_cenario = form_cenario.save()
            messages.success(request, f"Cenário '{novo_cenario.nome_cenario}' criado com sucesso! Agora adicione os detalhes.")
            return redirect(reverse('dimensionamento:editar_cenario', kwargs={'pk': novo_cenario.pk}))
        else:
            messages.error(request, "Erro ao criar o cenário. Verifique os dados.")
    else:
        form_cenario = CenarioDimensionamentoForm()
    context = {'cenarios': cenarios, 'form_cenario': form_cenario}
    return render(request, 'dimensionamento/listar_e_criar_cenarios.html', context)

# View para Editar um Cenário, seus Shrinkages e Volumes por Intervalo
def editar_cenario_dimensionamento(request, pk):
    cenario = get_object_or_404(CenarioDimensionamento, pk=pk)
    ShrinkageFormSet = inlineformset_factory(
        CenarioDimensionamento, ShrinkageAplicadoCenario,
        form=ShrinkageAplicadoCenarioForm, fields=['componente', 'percentual_aplicado'],
        extra=1, can_delete=True
    )
    IntervaloVolumeFormSet = modelformset_factory(
        IntervaloVolume, form=IntervaloVolumeForm,
        extra=0, can_delete=False, max_num=48
    )

    if request.method == 'GET':
        intervalos_existentes_count = IntervaloVolume.objects.filter(cenario=cenario).count()
        if intervalos_existentes_count < 48:
            intervalos_a_criar = []
            horas_ja_existentes = set(IntervaloVolume.objects.filter(cenario=cenario).values_list('hora_inicio', flat=True))
            for i in range(48):
                hora = i // 2
                minuto = (i % 2) * 30
                hora_atual = datetime.time(hour=hora, minute=minuto)
                if hora_atual not in horas_ja_existentes:
                    intervalos_a_criar.append(IntervaloVolume(cenario=cenario, hora_inicio=hora_atual, volume_estimado=0))
            if intervalos_a_criar:
                IntervaloVolume.objects.bulk_create(intervalos_a_criar)

    if request.method == 'POST':
        form_cenario = CenarioDimensionamentoForm(request.POST, instance=cenario)
        formset_shrinkage = ShrinkageFormSet(request.POST, instance=cenario, prefix='shrinkages')
        formset_intervalos = IntervaloVolumeFormSet(request.POST, queryset=IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio'), prefix='intervalos')

        if form_cenario.is_valid() and formset_shrinkage.is_valid() and formset_intervalos.is_valid():
            with transaction.atomic():
                form_cenario.save()
                formset_shrinkage.save()
                formset_intervalos.save()
            messages.success(request, f"Cenário '{cenario.nome_cenario}' atualizado com sucesso!")
            if 'calcular' in request.POST:
                sucesso_calculo, mensagem_calculo = processar_dimensionamento_completo_cenario(cenario.pk)
                if sucesso_calculo:
                    messages.info(request, mensagem_calculo)
                else:
                    messages.error(request, f"Houve um problema ao realizar o cálculo: {mensagem_calculo}")
            return redirect(reverse('dimensionamento:editar_cenario', kwargs={'pk': cenario.pk}))
        else:
            messages.error(request, "Erro ao atualizar o cenário. Verifique os dados nos formulários.")
    else: # GET request
        form_cenario = CenarioDimensionamentoForm(instance=cenario)
        formset_shrinkage = ShrinkageFormSet(instance=cenario, prefix='shrinkages')
        formset_intervalos = IntervaloVolumeFormSet(
            queryset=IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio'),
            prefix='intervalos'
        )
        for i, form_intervalo in enumerate(formset_intervalos):
            if form_intervalo.instance and form_intervalo.instance.pk:
                 form_intervalo.initial['hora_inicio_display'] = form_intervalo.instance.hora_inicio.strftime('%H:%M')
            else:
                hora = i // 2
                minuto = (i % 2) * 30
                form_intervalo.initial['hora_inicio_display'] = datetime.time(hour=hora, minute=minuto).strftime('%H:%M')

    context = {
        'cenario': cenario,
        'form_cenario': form_cenario,
        'formset_shrinkage': formset_shrinkage,
        'formset_intervalos': formset_intervalos,
    }
    return render(request, 'dimensionamento/editar_cenario.html', context)

# --- NOVA VIEW PARA O RELATÓRIO ---
def relatorio_dimensionamento_cenario(request, pk):
    cenario = get_object_or_404(CenarioDimensionamento, pk=pk)
    # Busca todos os intervalos de volume para este cenário, ordenados pela hora
    intervalos_volume = IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio')

    # No futuro, podemos calcular totais ou médias aqui para exibir no relatório
    total_volume_estimado = sum(iv.volume_estimado for iv in intervalos_volume if iv.volume_estimado)
    # ... outros totais/médias que possam ser úteis ...

    context = {
        'cenario': cenario,
        'intervalos_volume': intervalos_volume,
        'total_volume_estimado': total_volume_estimado,
    }
    return render(request, 'dimensionamento/relatorio_cenario.html', context)
# --- FIM DA NOVA VIEW ---