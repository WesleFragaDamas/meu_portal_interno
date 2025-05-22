# escalas/logic.py
import datetime
import math
from pyworkforce.queuing import ErlangC
from dimensionamento.models import IntervaloVolume  # Para pegar TMA, etc. do cenário


def calcular_cobertura_e_saldo_com_sla(cenario, alocacoes):
    """
    Calcula a cobertura de agentes, o saldo (cobertura - necessidade),
    e o Nível de Serviço projetado COM A COBERTURA REAL da escala
    para cada intervalo de 30 minutos do dia.

    A Cobertura aqui é o número de agentes ESCALADOS E DENTRO DA JORNADA,
    pois a NECESSIDADE (agentes_com_shrinkage) já considera o shrinkage (pausas, etc.).
    """
    intervalos_dimensionados = {
        iv.hora_inicio: iv
        for iv in IntervaloVolume.objects.filter(cenario=cenario).order_by('hora_inicio')
    }

    cobertura_intervalos = [0.0] * 48  # Número de agentes escalados e em horário de trabalho
    total_agentes_escalados_no_dia = sum(aloc.quantidade_agentes for aloc in alocacoes)

    for aloc in alocacoes:
        tipo_turno = aloc.tipo_turno
        hora_inicio_turno = aloc.hora_inicio_efetiva_turno
        qtd_agentes_neste_bloco = aloc.quantidade_agentes

        minutos_inicio_turno = hora_inicio_turno.hour * 60 + hora_inicio_turno.minute
        jornada_total_minutos = tipo_turno.duracao_jornada_total.total_seconds() / 60
        minutos_fim_turno = minutos_inicio_turno + jornada_total_minutos

        # Não precisamos mais calcular pausas individuais aqui para a cobertura,
        # pois o shrinkage já está na "Necessidade".
        # Apenas verificamos se o turno está ativo.

        for i in range(48):  # Para cada intervalo de 30 min do dia
            minutos_inicio_intervalo_dia = (i * 30)
            minutos_fim_intervalo_dia = minutos_inicio_intervalo_dia + 30

            turno_ativo_neste_intervalo = (minutos_inicio_turno < minutos_fim_intervalo_dia and
                                           minutos_fim_turno > minutos_inicio_intervalo_dia)

            if turno_ativo_neste_intervalo:
                cobertura_intervalos[i] += qtd_agentes_neste_bloco

    lista_saldo = [0.0] * 48
    lista_sla_projetado_cobertura = [None] * 48

    for i in range(48):
        hora_intervalo_obj = datetime.time(hour=i // 2, minute=(i % 2) * 30)
        intervalo_dim_data = intervalos_dimensionados.get(hora_intervalo_obj)

        necessidade_atual = 0
        if intervalo_dim_data and intervalo_dim_data.agentes_com_shrinkage is not None:
            necessidade_atual = intervalo_dim_data.agentes_com_shrinkage

        cobertura_atual = cobertura_intervalos[i]
        lista_saldo[i] = cobertura_atual - necessidade_atual

        if intervalo_dim_data and intervalo_dim_data.volume_estimado > 0 and cobertura_atual > 0:
            try:
                taxa_horaria_transacoes = intervalo_dim_data.volume_estimado * 2
                aht_para_erlang = cenario.tma_segundos

                if cenario.tipo_calculo == 'CHAT_RECEPTIVO' and hasattr(cenario,
                                                                        'concorrencia_chat') and cenario.concorrencia_chat and cenario.concorrencia_chat > 0:
                    aht_para_erlang = cenario.tma_segundos / cenario.concorrencia_chat

                # --- CORREÇÃO DO AttributeError: converter cobertura_atual para int ---
                posicoes_para_sla_calc = math.ceil(cobertura_atual)  # Garante inteiro e arredonda para cima
                if posicoes_para_sla_calc <= 0:  # ErlangC não aceita 0 ou menos posições se há tráfego
                    sl_cobertura = 0.0
                else:
                    erlang_calc = ErlangC(
                        transactions=taxa_horaria_transacoes,
                        aht=aht_para_erlang,
                        interval=3600,
                        asa=cenario.tempo_atendimento_meta_segundos
                    )
                    sl_cobertura = erlang_calc.service_level(positions=posicoes_para_sla_calc)
                # --- FIM DA CORREÇÃO ---

                print(
                    f"Intervalo {hora_intervalo_obj.strftime('%H:%M')}: Vol={intervalo_dim_data.volume_estimado}, Cobertura={cobertura_atual} (usado como {posicoes_para_sla_calc}), TMA Erlang={aht_para_erlang}, ASA={cenario.tempo_atendimento_meta_segundos}, SL Retornado={sl_cobertura}")

                if sl_cobertura is not None:
                    lista_sla_projetado_cobertura[i] = sl_cobertura * 100.0
                else:
                    lista_sla_projetado_cobertura[i] = 0.0
            except Exception as e:
                print(f"Erro ao calcular SLA para cobertura no intervalo {hora_intervalo_obj.strftime('%H:%M')}: {e}")
                lista_sla_projetado_cobertura[i] = None
        elif intervalo_dim_data and intervalo_dim_data.volume_estimado == 0:
            lista_sla_projetado_cobertura[i] = 100.0
        else:
            lista_sla_projetado_cobertura[i] = 0.0 if (
                        intervalo_dim_data and intervalo_dim_data.volume_estimado > 0 and cobertura_atual == 0) else None

    return cobertura_intervalos, lista_saldo, lista_sla_projetado_cobertura, total_agentes_escalados_no_dia