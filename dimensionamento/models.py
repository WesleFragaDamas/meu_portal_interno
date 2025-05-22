# dimensionamento/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

TIPO_CALCULO_CHOICES = [
    ('RECEPTIVO_VOZ', 'Voz Receptivo (Erlang C)'),
    ('ATIVO_META', 'Ativo por Meta'),
    ('CHAT_RECEPTIVO', 'Chat Receptivo (Erlang C com Concorrência)'),  # NOVA OPÇÃO
]


class ComponenteShrinkage(models.Model):
    # ... (sem alterações aqui) ...
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome do Componente de Shrinkage")
    percentual_padrao = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                          verbose_name="Percentual Padrão (%)")

    def __str__(self): return f"{self.nome} ({self.percentual_padrao}%)"

    class Meta: verbose_name = "Componente de Shrinkage"; verbose_name_plural = "Componentes de Shrinkage"; ordering = [
        'nome']


class CenarioDimensionamento(models.Model):
    nome_cenario = models.CharField(max_length=100, unique=True, verbose_name="Identificação do Cenário")
    data_referencia = models.DateField(default=timezone.now, verbose_name="Data de Referência do Cenário")
    tipo_calculo = models.CharField(
        max_length=20, choices=TIPO_CALCULO_CHOICES, default='RECEPTIVO_VOZ',
        verbose_name="Tipo de Dimensionamento"
    )
    volume_chamadas_diario_base = models.PositiveIntegerField(null=True, blank=True,
                                                              verbose_name="[RECEPTIVO/CHAT] Volume Diário (Base)")
    tma_segundos = models.PositiveIntegerField(default=180, verbose_name="TMA Padrão (Segundos)")
    nivel_servico_meta_percentual = models.FloatField(
        default=80.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name="[RECEPTIVO/CHAT] Meta de Nível de Serviço (%)"
    )
    tempo_atendimento_meta_segundos = models.PositiveIntegerField(
        default=20, verbose_name="[RECEPTIVO/CHAT] Tempo Meta para Atendimento (s)"
    )
    tmp_segundos_padrao = models.PositiveIntegerField(default=30, null=True, blank=True,
                                                      verbose_name="TMP Padrão (Pós-Chamada/Chat em segundos)")

    # --- NOVO CAMPO PARA CONCORRÊNCIA DO CHAT ---
    concorrencia_chat = models.PositiveIntegerField(
        default=1, null=True, blank=True,  # Default 1 se não for chat, ou se for 1 chat por vez
        validators=[MinValueValidator(1)],
        verbose_name="[CHAT] Concorrência Máxima por Agente",
        help_text="Quantos chats um agente pode atender simultaneamente."
    )
    # --- FIM DO NOVO CAMPO ---

    meta_campanha_ativo = models.PositiveIntegerField(null=True, blank=True,
                                                      verbose_name="[ATIVO] Meta da Campanha (nº sucessos)")
    taxa_contato_percentual_ativo = models.FloatField(null=True, blank=True,
                                                      validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                                      verbose_name="[ATIVO] Taxa de Contato (%)")
    taxa_sucesso_contato_percentual_ativo = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0),
                                                                                                 MaxValueValidator(
                                                                                                     100.0)],
                                                              verbose_name="[ATIVO] Taxa de Sucesso por Contato Efetivo (%)")
    tempo_medio_discagem_espera_seg_ativo = models.PositiveIntegerField(default=15, null=True, blank=True,
                                                                        verbose_name="[ATIVO] Tempo Médio Discagem/Espera por Tentativa (s)")

    jornada_padrao_duracao = models.DurationField(default=datetime.timedelta(hours=6, minutes=20),
                                                  verbose_name="Duração da Jornada Padrão",
                                                  help_text="Formato: HH:MM:SS ou HH:MM. Ex: 06:20:00.")
    tempo_produtivo_estimado_duracao = models.DurationField(default=datetime.timedelta(hours=5, minutes=30),
                                                            verbose_name="Tempo Produtivo Estimado por Jornada",
                                                            help_text="Formato: HH:MM:SS ou HH:MM. Ex: 05:30:00.")
    fator_shrinkage_total_calculado_percentual = models.FloatField(null=True, blank=True,
                                                                   validators=[MinValueValidator(0.0)],
                                                                   verbose_name="Fator de Shrinkage Total Aplicado (%)")
    ftes_calculados_estimativa = models.FloatField(null=True, blank=True, verbose_name="Estimativa de FTEs Calculados")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome_cenario} ({self.get_tipo_calculo_display()} - {self.data_referencia.strftime('%d/%m/%Y')})"

    class Meta: verbose_name = "Cenário de Dimensionamento"; verbose_name_plural = "Cenários de Dimensionamento"; ordering = [
        '-data_referencia', 'nome_cenario']


class ShrinkageAplicadoCenario(models.Model):
    # ... (sem alterações aqui) ...
    cenario = models.ForeignKey(CenarioDimensionamento, related_name="componentes_shrinkage_aplicados",
                                on_delete=models.CASCADE)
    componente = models.ForeignKey(ComponenteShrinkage, on_delete=models.CASCADE)
    percentual_aplicado = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                            verbose_name="Percentual Aplicado no Cenário (%)")

    def __str__(self): return f"{self.cenario.nome_cenario} - {self.componente.nome}: {self.percentual_aplicado}%"

    class Meta: unique_together = ('cenario',
                                   'componente'); verbose_name = "Shrinkage Aplicado ao Cenário"; verbose_name_plural = "Shrinkages Aplicados aos Cenários"; ordering = [
        'cenario', 'componente__nome']


class IntervaloVolume(models.Model):
    # ... (sem alterações aqui, mas os campos de resultado serão interpretados de forma diferente para chat) ...
    cenario = models.ForeignKey(CenarioDimensionamento, related_name="intervalos_volume", on_delete=models.CASCADE)
    hora_inicio = models.TimeField(verbose_name="Hora de Início do Intervalo")
    volume_estimado = models.PositiveIntegerField(default=0,
                                                  verbose_name="Volume Estimado no Intervalo")  # Para chat, seria "Volume de Chats Iniciados"
    agentes_erlang = models.FloatField(null=True, blank=True, verbose_name="Agentes Calculados (Erlang)")
    agentes_com_shrinkage = models.FloatField(null=True, blank=True, verbose_name="Agentes Necessários (c/ Shrinkage)")
    nivel_servico_projetado_percentual = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0),
                                                                                              MaxValueValidator(100.0)],
                                                           verbose_name="Nível de Serviço Projetado (%)")
    ocupacao_projetada_percentual = models.FloatField(null=True, blank=True,
                                                      validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                                      verbose_name="Ocupação Projetada (%)")

    def __str__(
            self): return f"{self.cenario.nome_cenario} - {self.hora_inicio.strftime('%H:%M')} ({self.volume_estimado} vol.)"  # Alterado para 'vol.'

    class Meta: verbose_name = "Volume por Intervalo"; verbose_name_plural = "Volumes por Intervalo"; ordering = [
        'cenario', 'hora_inicio']; unique_together = ('cenario', 'hora_inicio')