from django import forms
from .models import Personal, Reserva, Cliente


# disponibiilidad horarios
HORARIOS_DISPONIBLES = [
    ('09:00', '10:00'),
    ('10:00', '11:00'),
    ('11:00', '12:00'),
    ('12:00', '13:00'),
#   ('13:00', '14:00'), <- hora de almuerzo
    ('14:00', '15:00'),
    ('15:00', '16:00'),
    ('16:00', '17:00'),
]



class ReservaForm(forms.ModelForm):
    hora = forms.ChoiceField(
        choices = HORARIOS_DISPONIBLES
    )
    class Meta:
        model = Reserva
        fields = [
            'id_personal_servicio',
            'id_cliente',
            'id_personal',
            'fecha',
            'hora',
        ]
        
        labels = {
            'id_personal_servicio': 'Elija un servicio',
            'id_cliente': 'Ingrese su nombre',
            'id_personal': 'Eliga un Profesional',
            'fecha': 'Fecha',
            'hora': 'Hora',
        }
        
        widgets = {
            'id_personal_servicio': forms.Select(attrs={
                'class': 'form-control',
            }),
            'id_cliente': forms.Select(attrs={
                'class': 'form-control',
            }),
            'id_personal': forms.Select(attrs={
                'class': 'form-control',
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'hora': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
        }
                
class AutenticacionForm(forms.Form):
    nombre = forms.CharField(max_length=100, label='Ingrese su Nombre')
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Contraseña',
    )
    