# dimensionamento/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.forms import modelformset_factory, inlineformset_factory
from django.contrib import messages
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required

from .models import CenarioDimensionamento, ComponenteShrinkage, ShrinkageAplicadoCenario, IntervaloVolume
from .forms import CenarioDimensionamentoForm, ShrinkageAplicadoCenarioForm, IntervaloVolumeForm
from .logic import processar_dimensionamento_completo_cenario


@login_required
def listar_e_criar_cenarios(request):
    cenarios = CenarioDimensionamento.objects.all().order_by('-data_referencia', 'nome_cenario')

    # Inicializa form_cenario aqui para garantir que sempre existe para o context
    form_cenario = CenarioDimensionamentoForm()  # Formulário vazio para GET ou se POST falhar

    if request.method == 'POST':
        form_cenario_post = CenarioDimensionamentoForm(request.POST)  # Usa uma variável diferente para o POST
        if form_cenario_post.is_valid():
            novo_cenario = form_cenario_post.save()
            messages.success(request,
                             f"Cenário '{novo_cenario.nome_cenario}' criado com sucesso! Agora adicione os detalhes.")
            return redirect(reverse('dimensionamento:editar_cenario', kwargs={'pk': novo_cenario.pk}))
        else:
            messages.error(request, "Erro ao criar o cenário. Verifique os dados submetidos.")
            form_cenario = form_cenario_post  # Passa o formulário com erros para ser re-renderizado
            # A view continuará para o render final
    # else: # Para GET, form_cenario já foi inicializado como um novo formulário em branco

    context = {
        'cenarios': cenarios,
        'form_cenario': form_cenario,  # Sempre teremos um form_cenario aqui
    }
    return render(request, 'dimensionamento/listar_e_criar_cenarios.html', context)


@login_required
def editar_cenario_dimensionamento(request, pk):
    # ... (código da view editar_cenario_dimensionamento como estava antes, ela já retorna HttpResponse em todos os caminhos) ...
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
            horas_ja_existentes = set(
                IntervaloVolume.objects.filter(cenario=cenario).values_list('hora_inicio', flat=True))
            for i in range(48):
                hora = i // 2
                minuto = (i % 2) * 30
                hora_atual = datetime.time(hour=hora, minute=minuto)
                if hora_atual not in horas_ja_existentes:
                    intervalos_a_criar.append(
                        IntervaloVolume(cenario=cenario, hora_inicio=hora_atual, volume_estimado=0))
            if intervalos_a_criar:
                IntervaloVolume.objects.bulk_create(intervalos_a_criar)

    if request.method == 'POST':
        form_cenario_edit = CenarioDimensionamentoForm(request.POST,
                                                       instance=cenario)  # Renomeado para evitar conflito com o do GET
        formset_shrinkage = ShrinkageFormSet(request.POST, instance=cenario, prefix='shrinkages')
        formset_intervalos = IntervaloVolumeFormSet(request.POST,
                                                    queryset=IntervaloVolume.objects.filter(cenario=cenario).order_by(
                                                        'hora_inicio'), prefix='intervalos')

        if form_cenario_edit.is_valid() and formset_shrinkage.is_valid() and formset_intervalos.is_valid():
            with transaction.atomic():
                form_cenario_edit.save()  # Salva o form editado
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
            # Se algum formulário/formset for inválido no POST, precisamos re-passá-los para o template
            # O form_cenario para o contexto será o form_cenario_edit (com erros)
            # Os formsets já são os do POST (com erros)
            messages.error(request, "Erro ao atualizar o cenário. Verifique os dados nos formulários.")
            # A view continuará para o render final, passando form_cenario_edit como form_cenario no context
            context_form_cenario = form_cenario_edit  # Passa o form com erros
    else:  # GET request
        context_form_cenario = CenarioDimensionamentoForm(instance=cenario)  # Form para edição
        formset_shrinkage = ShrinkageFormSet(instance=cenario, prefix='shrinkages')
        formset_intervalos = IntervaloVolumeFormSet(
            queryset=IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio'),
            prefix='intervalos'
        )
        for i, form_intervalo_item in enumerate(
                formset_intervalos):  # Renomeado form_intervalo para form_intervalo_item
            if form_intervalo_item.instance and form_intervalo_item.instance.pk:
                form_intervalo_item.initial['hora_inicio_display'] = form_intervalo_item.instance.hora_inicio.strftime(
                    '%H:%M')
            else:
                hora = i // 2
                minuto = (i % 2) * 30
                form_intervalo_item.initial['hora_inicio_display'] = datetime.time(hour=hora, minute=minuto).strftime(
                    '%H:%M')

    # Garante que context_form_cenario está definido para o contexto final
    # Se for POST e inválido, já é form_cenario_edit. Se for GET, é o form de instância.
    # A lógica abaixo para formset_shrinkage e formset_intervalos já os define para GET e POST.

    context = {
        'cenario': cenario,
        'form_cenario': context_form_cenario if 'context_form_cenario' in locals() else CenarioDimensionamentoForm(
            instance=cenario),
        'formset_shrinkage': formset_shrinkage,
        'formset_intervalos': formset_intervalos,
    }
    return render(request, 'dimensionamento/editar_cenario.html', context)


@login_required
def relatorio_dimensionamento_cenario(request, pk):
    # ... (código da view relatorio_dimensionamento_cenario como estava antes) ...
    cenario = get_object_or_404(CenarioDimensionamento, pk=pk)
    intervalos_volume = IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio')
    total_volume_estimado = sum(iv.volume_estimado for iv in intervalos_volume if iv.volume_estimado)
    context = {
        'cenario': cenario,
        'intervalos_volume': intervalos_volume,
        'total_volume_estimado': total_volume_estimado,
    }
    return render(request, 'dimensionamento/relatorio_cenario.html', context)