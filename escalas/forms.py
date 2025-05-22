# escalas/forms.py
from django import forms
from .models import AlocacaoTurno, TipoTurno

class AlocacaoTurnoForm(forms.ModelForm):
    # Para ter um dropdown mais amigável para TipoTurno
    tipo_turno = forms.ModelChoiceField(
        queryset=TipoTurno.objects.filter(ativo=True).order_by('nome_turno'),
        label="Tipo de Turno",
        widget=forms.Select(attrs={'class': 'form-select'}) # Para Bootstrap, se usar
    )
    hora_inicio_efetiva_turno = forms.TimeField(
        label="Início do Turno",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}, format='%H:%M'),
        help_text="HH:MM"
    )
    quantidade_agentes = forms.IntegerField(
        label="Qtd. Agentes",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 80px;'})
    )

    class Meta:
        model = AlocacaoTurno
        fields = ['tipo_turno', 'hora_inicio_efetiva_turno', 'quantidade_agentes', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }