# dimensionamento/forms.py
from django import forms
from .models import CenarioDimensionamento, ShrinkageAplicadoCenario, IntervaloVolume

class CenarioDimensionamentoForm(forms.ModelForm):
    class Meta:
        model = CenarioDimensionamento
        fields = [
            'nome_cenario', 'data_referencia', 'tipo_calculo',
            'volume_chamadas_diario_base', 'tma_segundos',
            'nivel_servico_meta_percentual', 'tempo_atendimento_meta_segundos',
            'tmp_segundos_padrao',
            'concorrencia_chat', # NOVO CAMPO ADICIONADO
            'meta_campanha_ativo', 'taxa_contato_percentual_ativo',
            'taxa_sucesso_contato_percentual_ativo', 'tempo_medio_discagem_espera_seg_ativo',
            'jornada_padrao_duracao', 'tempo_produtivo_estimado_duracao',
        ]
        widgets = {
            'data_referencia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'nome_cenario': forms.TextInput(attrs={'placeholder': 'Ex: Campanha Dia das Mães'}),
            'tipo_calculo': forms.Select(attrs={'class': 'form-select'}),
            'volume_chamadas_diario_base': forms.NumberInput(attrs={'min': '0'}),
            'tma_segundos': forms.NumberInput(attrs={'min': '1'}),
            'nivel_servico_meta_percentual': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.1'}),
            'tempo_atendimento_meta_segundos': forms.NumberInput(attrs={'min': '0'}),
            'tmp_segundos_padrao': forms.NumberInput(attrs={'min': '0'}),
            'concorrencia_chat': forms.NumberInput(attrs={'min': '1', 'step': '1'}), # NOVO WIDGET
            'meta_campanha_ativo': forms.NumberInput(attrs={'min': '0'}),
            'taxa_contato_percentual_ativo': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.1'}),
            'taxa_sucesso_contato_percentual_ativo': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.1'}),
            'tempo_medio_discagem_espera_seg_ativo': forms.NumberInput(attrs={'min': '0'}),
            'jornada_padrao_duracao': forms.TextInput(attrs={'placeholder': 'HH:MM ou HH:MM:SS'}),
            'tempo_produtivo_estimado_duracao': forms.TextInput(attrs={'placeholder': 'HH:MM ou HH:MM:SS'}),
        }
        labels = {
            'nome_cenario': "Nome/Identificação do Cenário",
            'data_referencia': "Data de Referência",
            'tipo_calculo': "Qual o Tipo de Dimensionamento?",
            'volume_chamadas_diario_base': "[RECEPTIVO/CHAT] Volume Diário (Base)",
            'tma_segundos': "TMA Padrão (Segundos)",
            'nivel_servico_meta_percentual': "[RECEPTIVO/CHAT] Meta Nível de Serviço (%)",
            'tempo_atendimento_meta_segundos': "[RECEPTIVO/CHAT] Tempo Meta Atendimento (s)",
            'tmp_segundos_padrao': "TMP Padrão (Pós-Chamada/Chat em s)",
            'concorrencia_chat': "[CHAT] Concorrência Máxima por Agente", # NOVO LABEL
            'meta_campanha_ativo': "[ATIVO] Meta da Campanha (nº sucessos)",
            'taxa_contato_percentual_ativo': "[ATIVO] Taxa de Contato (%)",
            'taxa_sucesso_contato_percentual_ativo': "[ATIVO] Taxa de Sucesso por Contato (%)",
            'tempo_medio_discagem_espera_seg_ativo': "[ATIVO] Tempo Médio Discagem/Espera (s)",
            'jornada_padrao_duracao': "Jornada Padrão (Ex: 06:20)",
            'tempo_produtivo_estimado_duracao': "Tempo Produtivo por Jornada (Ex: 05:30)",
        }
        help_texts = {
            'jornada_padrao_duracao': 'Informe no formato HH:MM ou HH:MM:SS.',
            'tempo_produtivo_estimado_duracao': 'Informe no formato HH:MM ou HH:MM:SS.',
            'taxa_contato_percentual_ativo': 'Valor entre 0 e 100.',
            'taxa_sucesso_contato_percentual_ativo': 'Valor entre 0 e 100.',
            'concorrencia_chat': 'Quantos chats simultâneos um agente pode atender (ex: 2, 3).', # NOVO HELP TEXT
        }

class ShrinkageAplicadoCenarioForm(forms.ModelForm):
    # ... (sem alterações aqui) ...
    class Meta: model = ShrinkageAplicadoCenario; fields = ['componente', 'percentual_aplicado']; widgets = {'percentual_aplicado': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.1'})}

class IntervaloVolumeForm(forms.ModelForm):
    # ... (sem alterações aqui) ...
    hora_inicio_display = forms.CharField(label="Horário", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'hora-display-input'}))
    class Meta: model = IntervaloVolume; fields = ['volume_estimado']; labels = { 'volume_estimado': '' }; widgets = { 'volume_estimado': forms.NumberInput(attrs={'min': '0', 'class': 'volume-intervalo-input'})}