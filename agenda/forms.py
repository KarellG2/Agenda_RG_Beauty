from datetime import date

from django import forms
from .models import *


# disponibiilidad horarios
HORARIOS_DISPONIBLES = [
    ('09:00', '09:00 - 10:00'),
    ('10:00', '10:00 - 11:00'),
    ('11:00', '11:00 - 12:00'),
    ('12:00', '12:00 - 13:00'),
    ('14:00', '14:00 - 15:00'),
    ('15:00', '15:00 - 16:00'),
    ('16:00', '16:00 - 17:00'),
]


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre_s', 'descripcion', 'categoria']
        labels = {
            'nombre_s': 'Nombre del servicio',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
        }
        widgets = {
            'nombre_s': forms.TextInput(attrs={'class': 'admin-field'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'admin-field admin-textarea',
                'rows': 4,
            }),
            'categoria': forms.Select(attrs={'class': 'admin-field'}),
        }


class ReservaForm(forms.ModelForm):
    hora = forms.ChoiceField(choices=HORARIOS_DISPONIBLES)
    nombre_cliente = forms.CharField(max_length=100, label="Ingrese su Nombre")
    telefono_cliente = forms.CharField(max_length=20, label="Ingrese su Teléfono")
    correo_cliente = forms.EmailField(max_length=100, label="Ingrese su Correo Electrónico")

    class Meta:
        model = Reserva
        fields = [
            'id_personal_servicio',
            'fecha',
            'hora',
            'etiquetas',
        ]

        labels = {
            'id_personal_servicio': 'Elija un servicio y profesional',
            'fecha': 'Fecha',
        }

        widgets = {
            'id_personal_servicio': forms.Select(attrs={
                'class': 'form-control',
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_personal_servicio'].queryset = (
            ServicioPersonal.objects.select_related('id_servicio', 'id_personal')
        )

class AutenticacionForm(forms.Form):
    nombre = forms.CharField(max_length=100, label='Ingrese su Nombre')
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Contraseña',
    )


class AutenticacionClienteForm(AutenticacionForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Teléfono',
    )
    
