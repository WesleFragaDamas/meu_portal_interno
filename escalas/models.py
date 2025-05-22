# escalas/models.py
from django.db import models
from django.core.exceptions import ValidationError
from dimensionamento.models import CenarioDimensionamento  # Importa o Cenario para ForeignKey
import datetime


class TipoTurno(models.Model):
    nome_turno = models.CharField(max_length=100, unique=True, verbose_name="Nome do Tipo de Turno")
    # Ex: "Manhã 6h20", "Tarde 8h c/ 2x10+20", "Noturno Reduzido 5h50"

    duracao_jornada_total = models.DurationField(
        verbose_name="Duração Total da Jornada",
        help_text="Formato: HH:MM:SS ou HH:MM. Ex: 06:20:00"
    )

    # Pausa 1 (ex: 10 minutos)
    duracao_pausa1 = models.DurationField(
        default=datetime.timedelta(minutes=10), verbose_name="Duração Pausa 1",
        help_text="Formato: HH:MM:SS. Ex: 00:10:00"
    )
    inicio_pausa1_apos_x_tempo = models.DurationField(
        default=datetime.timedelta(hours=1), verbose_name="Pausa 1 Inicia Após X Tempo de Trabalho",
        help_text="Formato: HH:MM:SS. Ex: 01:00:00 (inicia após 1h de trabalho)"
    )
    # Considerar se a pausa é remunerada/produtiva ou não para cálculos de cobertura mais finos no futuro.
    # Por agora, vamos assumir que as pausas listadas aqui são as que tiram o agente do atendimento.

    # Pausa 2 (ex: 20 minutos - principal)
    duracao_pausa2 = models.DurationField(
        default=datetime.timedelta(minutes=20), verbose_name="Duração Pausa 2 (Principal)",
        help_text="Formato: HH:MM:SS. Ex: 00:20:00"
    )
    inicio_pausa2_apos_x_tempo = models.DurationField(
        default=datetime.timedelta(hours=3), verbose_name="Pausa 2 Inicia Após X Tempo de Trabalho",
        help_text="Formato: HH:MM:SS. Ex: 03:00:00 (aproximadamente na metade para uma jornada de 6h)"
    )

    # Pausa 3 (ex: 10 minutos)
    duracao_pausa3 = models.DurationField(
        default=datetime.timedelta(minutes=10), verbose_name="Duração Pausa 3",
        help_text="Formato: HH:MM:SS. Ex: 00:10:00"
    )
    # Regra "até 1h antes do fim da jornada" é mais complexa de modelar diretamente aqui.
    # Poderíamos ter um campo "Pausa 3 ocorre X tempo ANTES do fim da jornada"
    # Ou, para simplificar, "Pausa 3 Inicia Após X Tempo de Trabalho desde o início da Pausa 2"
    inicio_pausa3_apos_x_tempo_da_pausa2 = models.DurationField(
        default=datetime.timedelta(hours=2), verbose_name="Pausa 3 Inicia Após X Tempo do Fim da Pausa 2",
        help_text="Formato: HH:MM:SS. Ex: 02:00:00 (inicia 2h após o fim da pausa 2)"
    )
    # NOTA: A regra "até 1h antes do fim" será mais uma verificação na lógica de cálculo de cobertura.
    # A alternativa é o usuário poder ajustar o horário exato da pausa ao alocar o turno.

    tempo_produtivo_calculado = models.DurationField(
        null=True, blank=True, editable=False,  # Será calculado e salvo
        verbose_name="Tempo Produtivo Calculado da Jornada"
    )

    ativo = models.BooleanField(default=True, verbose_name="Turno Ativo?")

    def clean(self):
        # Validação para garantir que a soma das pausas não exceda a jornada, etc.
        soma_pausas = self.duracao_pausa1 + self.duracao_pausa2 + self.duracao_pausa3
        if soma_pausas >= self.duracao_jornada_total:
            raise ValidationError(
                "A soma das durações das pausas não pode ser maior ou igual à duração total da jornada.")
        # Outras validações podem ser adicionadas aqui

    def save(self, *args, **kwargs):
        # Calcular tempo produtivo
        soma_pausas = self.duracao_pausa1 + self.duracao_pausa2 + self.duracao_pausa3
        self.tempo_produtivo_calculado = self.duracao_jornada_total - soma_pausas
        super().save(*args, **kwargs)  # Chama o método save original

    def __str__(self):
        return f"{self.nome_turno} ({str(self.duracao_jornada_total).split('.')[0]})"  # Mostra HH:MM:SS

    class Meta:
        verbose_name = "Tipo de Turno"
        verbose_name_plural = "Tipos de Turno"
        ordering = ['nome_turno']


class AlocacaoTurno(models.Model):
    cenario_dimensionamento = models.ForeignKey(
        CenarioDimensionamento,
        on_delete=models.CASCADE,
        related_name="alocacoes_de_turnos",
        verbose_name="Cenário de Dimensionamento Associado"
    )
    tipo_turno = models.ForeignKey(
        TipoTurno,
        on_delete=models.PROTECT,  # Evita excluir um TipoTurno se ele estiver em uso
        related_name="alocacoes",
        verbose_name="Tipo de Turno Selecionado"
    )
    hora_inicio_efetiva_turno = models.TimeField(
        verbose_name="Hora de Início Efetiva do Turno",
        help_text="Hora real que este grupo de agentes inicia o turno."
    )
    quantidade_agentes = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade de Agentes Neste Turno/Horário"
    )
    # Poderíamos adicionar campos para horários específicos de pausa para esta alocação,
    # se quisermos permitir que o usuário ajuste as pausas padrão do TipoTurno.
    # Ex: inicio_pausa1_alocada = models.TimeField(null=True, blank=True)
    # Por enquanto, as pausas serão calculadas com base no TipoTurno e hora_inicio_efetiva_turno.

    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    def __str__(self):
        return f"{self.quantidade_agentes} Ag. no Turno '{self.tipo_turno.nome_turno}' às {self.hora_inicio_efetiva_turno.strftime('%H:%M')} para {self.cenario_dimensionamento.nome_cenario}"

    class Meta:
        verbose_name = "Alocação de Turno"
        verbose_name_plural = "Alocações de Turno"
        ordering = ['cenario_dimensionamento', 'hora_inicio_efetiva_turno', 'tipo_turno__nome_turno']