# dimensionamento/logic.py
import math
import datetime
from pyworkforce.queuing import ErlangC


def calcular_shrinkage_total_para_cenario(cenario_dimensionamento):
    # ... (código existente, sem mudanças) ...
    fatores_produtividade = []
    componentes_aplicados = cenario_dimensionamento.componentes_shrinkage_aplicados.all()
    if not componentes_aplicados: return 0.0
    for comp_aplicado in componentes_aplicados:
        fatores_produtividade.append(1 - (comp_aplicado.percentual_aplicado / 100.0))
    produtividade_liquida = 1.0
    for fator in fatores_produtividade: produtividade_liquida *= fator
    shrinkage_total_decimal = 1 - produtividade_liquida
    return shrinkage_total_decimal * 100.0


def _calcular_erlang_c_com_indicadores(
        taxa_horaria_transacoes, aht_para_erlang, interval_duration_seconds,
        service_level_target, asa_target):
    """Função auxiliar para encapsular o cálculo de Erlang C e indicadores."""
    agentes_erlang_raw = 0.0
    ns_projetado_decimal = None
    ocupacao_projetada_decimal = None

    try:
        erlang_c_calculator = ErlangC(
            transactions=taxa_horaria_transacoes, aht=aht_para_erlang,
            interval=interval_duration_seconds, asa=asa_target)

        required_positions_data = erlang_c_calculator.required_positions(service_level=service_level_target)

        if required_positions_data and 'positions' in required_positions_data and required_positions_data[
            'positions'] is not None:
            agentes_erlang_raw = required_positions_data['positions']
            if 'service_level' in required_positions_data and required_positions_data['service_level'] is not None:
                ns_projetado_decimal = required_positions_data['service_level']
            if 'occupancy' in required_positions_data and required_positions_data['occupancy'] is not None:
                ocupacao_projetada_decimal = required_positions_data['occupancy']
        else:
            agentes_erlang_raw = (taxa_horaria_transacoes * aht_para_erlang) / interval_duration_seconds

        agentes_erlang_arredondados = math.ceil(agentes_erlang_raw)

        if agentes_erlang_arredondados > 0:
            # Recalcula/confirma NS e Ocupação com o número arredondado de agentes
            if ns_projetado_decimal is None or (
                    agentes_erlang_raw != agentes_erlang_arredondados):  # Se não foi pego antes ou se arredondou
                sl_calculated = erlang_c_calculator.service_level(positions=agentes_erlang_arredondados)
                if sl_calculated is not None: ns_projetado_decimal = sl_calculated

            if ocupacao_projetada_decimal is None or (agentes_erlang_raw != agentes_erlang_arredondados):
                raw_occupancy = (
                                            taxa_horaria_transacoes * aht_para_erlang / interval_duration_seconds) / agentes_erlang_arredondados
                ocupacao_projetada_decimal = min(raw_occupancy, 1.0)
        elif taxa_horaria_transacoes > 0:
            ns_projetado_decimal = 0.0
            ocupacao_projetada_decimal = 0.0
        elif taxa_horaria_transacoes == 0:
            ns_projetado_decimal = 1.0
            ocupacao_projetada_decimal = 0.0
            agentes_erlang_arredondados = 0  # Garante que é zero se não há transações

    except Exception as e:
        print(f"Erro durante cálculos Erlang C (auxiliar): {e}. Usando cálculo bruto para agentes.")
        agentes_erlang_raw = (taxa_horaria_transacoes * aht_para_erlang) / interval_duration_seconds
        agentes_erlang_arredondados = math.ceil(agentes_erlang_raw)
        ns_projetado_decimal = None
        ocupacao_projetada_decimal = None

    return agentes_erlang_arredondados, ns_projetado_decimal, ocupacao_projetada_decimal


def calcular_dimensionamento_receptivo_ou_chat_intervalo(
        tipo_calculo, volume_chamadas_ou_chats, tma_segundos,
        nivel_servico_meta_percentual, tempo_atendimento_meta_segundos,
        fator_shrinkage_total_percentual, concorrencia_chat=1):
    """
    Calcula agentes e indicadores para um intervalo RECEPTIVO (Voz ou Chat).
    Para CHAT, ajusta o AHT pela concorrência.
    Retorna (ag_erlang, ag_shrink, ns_projetado_pc, ocup_projetada_pc)
    """
    if not volume_chamadas_ou_chats or volume_chamadas_ou_chats == 0:
        return 0.0, 0.0, 100.0, 0.0

    taxa_horaria_transacoes = volume_chamadas_ou_chats * 2

    aht_efetivo_para_erlang = tma_segundos
    if tipo_calculo == 'CHAT_RECEPTIVO':
        if concorrencia_chat and concorrencia_chat > 0:
            aht_efetivo_para_erlang = tma_segundos / concorrencia_chat
        else:  # Se concorrência for 0 ou None, trata como 1 para evitar divisão por zero
            aht_efetivo_para_erlang = tma_segundos
            print("Aviso: Concorrência do chat inválida, usando 1.")

    interval_duration_seconds = 3600
    service_level_target = nivel_servico_meta_percentual / 100.0
    asa_target = tempo_atendimento_meta_segundos

    agentes_erlang_arredondados, ns_decimal, ocup_decimal = _calcular_erlang_c_com_indicadores(
        taxa_horaria_transacoes, aht_efetivo_para_erlang, interval_duration_seconds,
        service_level_target, asa_target
    )

    agentes_com_shrinkage_raw = 0.0
    if fator_shrinkage_total_percentual < 0: fator_shrinkage_total_percentual = 0.0
    if fator_shrinkage_total_percentual >= 100.0:
        agentes_com_shrinkage_raw = float('inf')
    elif agentes_erlang_arredondados == 0:
        agentes_com_shrinkage_raw = 0.0
    else:
        multiplicador_shrinkage = 1 / (1 - (fator_shrinkage_total_percentual / 100.0))
        agentes_com_shrinkage_raw = agentes_erlang_arredondados * multiplicador_shrinkage

    agentes_com_shrinkage_arredondados = math.ceil(agentes_com_shrinkage_raw)

    ns_projetado_pc = ns_decimal * 100.0 if ns_decimal is not None else None
    ocupacao_projetada_pc = ocup_decimal * 100.0 if ocup_decimal is not None else None

    # A ocupação para chat deve considerar a concorrência.
    # A ocupação retornada pelo ErlangC (usando AHT/concorrência) é a ocupação do "slot de chat".
    # A ocupação real do agente seria essa ocupação do slot multiplicada por (1/concorrência),
    # se cada agente estivesse sempre com o máximo de chats.
    # No entanto, a ocupação retornada pela fórmula de Erlang já considera o AHT ajustado.
    # Se o AHT usado no Erlang foi AHT_chat / Concorrência, então a ocupação resultante
    # já é a ocupação por "servidor virtual" ou "slot de chat".
    # A ocupação real do agente físico é mais complexa de derivar diretamente aqui,
    # pois depende de quantos chats ele realmente está tratando.
    # Por simplicidade, a 'ocupacao_projetada_pc' é a ocupação dos "slots" Erlang.
    # Para a ocupação do agente, se ele está com N chats e a ocupação do slot é Y,
    # a ocupação do agente é Y. Se ele só tem 1 chat, a ocupação dele é Y/N.
    # Vamos manter a ocupação do slot por enquanto.

    return agentes_erlang_arredondados, agentes_com_shrinkage_arredondados, ns_projetado_pc, ocupacao_projetada_pc


def calcular_dimensionamento_ativo_meta(cenario, fator_shrinkage_total_percentual):
    # ... (código existente, sem mudanças aqui) ...
    print(f"--- Calculando para Cenário ATIVO: {cenario.nome_cenario} ---")
    if not all([cenario.meta_campanha_ativo, cenario.taxa_contato_percentual_ativo,
                cenario.taxa_sucesso_contato_percentual_ativo, cenario.tma_segundos,
                cenario.tempo_produtivo_estimado_duracao]):
        return 0.0
    taxa_contato_dec = cenario.taxa_contato_percentual_ativo / 100.0
    taxa_sucesso_dec = cenario.taxa_sucesso_contato_percentual_ativo / 100.0
    if taxa_contato_dec == 0 or taxa_sucesso_dec == 0: return float('inf')
    tentativas_por_sucesso = 1 / (taxa_contato_dec * taxa_sucesso_dec)
    tempo_discagem_por_tentativa = cenario.tempo_medio_discagem_espera_seg_ativo if cenario.tempo_medio_discagem_espera_seg_ativo else 0
    tempo_tma = cenario.tma_segundos
    tempo_tmp = cenario.tmp_segundos_padrao if cenario.tmp_segundos_padrao else 0
    tempo_total_por_sucesso_segundos = ((tentativas_por_sucesso - 1) * tempo_discagem_por_tentativa + 1 * (
                tempo_discagem_por_tentativa + tempo_tma + tempo_tmp))
    minutos_produtivos_jornada = 0
    if cenario.tempo_produtivo_estimado_duracao: minutos_produtivos_jornada = cenario.tempo_produtivo_estimado_duracao.total_seconds() / 60
    if minutos_produtivos_jornada == 0: return float('inf')
    agentes_necessarios_bruto = (
                (cenario.meta_campanha_ativo * tempo_total_por_sucesso_segundos) / (minutos_produtivos_jornada * 60))
    agentes_com_shrinkage = 0.0
    if fator_shrinkage_total_percentual < 0: fator_shrinkage_total_percentual = 0.0
    if fator_shrinkage_total_percentual >= 100.0:
        agentes_com_shrinkage = float('inf')
    elif agentes_necessarios_bruto == 0:
        agentes_com_shrinkage = 0.0
    else:
        multiplicador_shrinkage = 1 / (1 - (fator_shrinkage_total_percentual / 100.0))
        agentes_com_shrinkage = agentes_necessarios_bruto * multiplicador_shrinkage
    return math.ceil(agentes_com_shrinkage)


def processar_dimensionamento_completo_cenario(cenario_id):
    from .models import CenarioDimensionamento, IntervaloVolume
    try:
        cenario = CenarioDimensionamento.objects.get(id=cenario_id)
    except CenarioDimensionamento.DoesNotExist:
        return False, f"Cenário com ID {cenario_id} não encontrado."

    shrinkage_total_pc = calcular_shrinkage_total_para_cenario(cenario)
    cenario.fator_shrinkage_total_calculado_percentual = shrinkage_total_pc
    ftes_finais_para_salvar = 0
    mensagem_sucesso = ""

    if cenario.tipo_calculo == 'ATIVO_META':
        IntervaloVolume.objects.filter(cenario=cenario).update(
            agentes_erlang=None, agentes_com_shrinkage=None,
            nivel_servico_projetado_percentual=None, ocupacao_projetada_percentual=None)

    # Garantir que os 48 IntervaloVolume existem, especialmente para receptivo/chat
    # (Para ativo, eles podem não ser preenchidos com agentes Erlang, mas a estrutura pode ser útil)
    intervalos_existentes_map = {iv.hora_inicio: iv for iv in cenario.intervalos_volume.all()}
    todos_intervalos_para_processar = []
    for i in range(48):
        hora = i // 2;
        minuto = (i % 2) * 30
        hora_inicio_intervalo = datetime.time(hour=hora, minute=minuto)
        intervalo_obj = intervalos_existentes_map.get(hora_inicio_intervalo)
        if not intervalo_obj:
            intervalo_obj = IntervaloVolume.objects.create(
                cenario=cenario, hora_inicio=hora_inicio_intervalo, volume_estimado=0)
        todos_intervalos_para_processar.append(intervalo_obj)

    if cenario.tipo_calculo == 'RECEPTIVO_VOZ' or cenario.tipo_calculo == 'CHAT_RECEPTIVO':
        tipo_str = "RECEPTIVO VOZ" if cenario.tipo_calculo == 'RECEPTIVO_VOZ' else "CHAT RECEPTIVO"
        print(f"Processando Cenário {tipo_str}: {cenario.nome_cenario}")
        total_minutos_agente_necessarios_dia = 0

        concorrencia = 1  # Default para voz
        if cenario.tipo_calculo == 'CHAT_RECEPTIVO':
            concorrencia = cenario.concorrencia_chat if cenario.concorrencia_chat and cenario.concorrencia_chat > 0 else 1
            print(f"Usando concorrência CHAT: {concorrencia}")

        for intervalo in todos_intervalos_para_processar:
            ag_erlang, ag_shrink, ns_proj_pc, ocup_proj_pc = calcular_dimensionamento_receptivo_ou_chat_intervalo(
                tipo_calculo=cenario.tipo_calculo,  # Passa o tipo
                volume_chamadas_ou_chats=intervalo.volume_estimado,
                tma_segundos=cenario.tma_segundos,
                nivel_servico_meta_percentual=cenario.nivel_servico_meta_percentual,
                tempo_atendimento_meta_segundos=cenario.tempo_atendimento_meta_segundos,
                fator_shrinkage_total_percentual=shrinkage_total_pc,
                concorrencia_chat=concorrencia  # Passa a concorrência
            )
            intervalo.agentes_erlang = ag_erlang
            intervalo.agentes_com_shrinkage = ag_shrink
            intervalo.nivel_servico_projetado_percentual = ns_proj_pc
            intervalo.ocupacao_projetada_percentual = ocup_proj_pc
            intervalo.save()
            if intervalo.agentes_com_shrinkage and intervalo.agentes_com_shrinkage > 0 and intervalo.agentes_com_shrinkage != float(
                    'inf'):
                total_minutos_agente_necessarios_dia += intervalo.agentes_com_shrinkage * 30

        if cenario.tempo_produtivo_estimado_duracao:
            minutos_produtivos_jornada = cenario.tempo_produtivo_estimado_duracao.total_seconds() / 60
            if minutos_produtivos_jornada > 0 and total_minutos_agente_necessarios_dia > 0:
                ftes_finais_para_salvar = math.ceil(total_minutos_agente_necessarios_dia / minutos_produtivos_jornada)
        mensagem_sucesso = f"Dimensionamento {tipo_str} para '{cenario.nome_cenario}' processado. FTEs Estimados: {ftes_finais_para_salvar}"

    elif cenario.tipo_calculo == 'ATIVO_META':
        ftes_calculados_ativo = calcular_dimensionamento_ativo_meta(cenario, shrinkage_total_pc)
        ftes_finais_para_salvar = ftes_calculados_ativo
        mensagem_sucesso = f"Dimensionamento ATIVO para '{cenario.nome_cenario}' processado. FTEs Estimados: {ftes_finais_para_salvar}"
    else:
        return False, f"Tipo de cálculo '{cenario.tipo_calculo}' não reconhecido."

    cenario.ftes_calculados_estimativa = ftes_finais_para_salvar
    cenario.save()
    print(mensagem_sucesso)
    return True, mensagem_sucesso