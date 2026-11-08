from datetime import date

from django import forms
<<<<<<< HEAD
from .models import Reserva, ServicioPersonal
=======
from .models import Personal, Reserva, Cliente, Etiqueta, Servicio
>>>>>>> 5e8b77262c1d3e549eda0a03f3d9cee82d212379


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
<<<<<<< HEAD
    hora = forms.ChoiceField(choices=HORARIOS_DISPONIBLES)
    nombre_cliente = forms.CharField(max_length=100, label="Ingrese su Nombre")
    telefono_cliente = forms.CharField(max_length=20, label="Ingrese su Teléfono")
    correo_cliente = forms.EmailField(max_length=100, label="Ingrese su Correo Electrónico")
=======
    hora = forms.ChoiceField(choices=HORARIOS_DISPONIBLES, label='Hora')
    etiquetas = forms.ModelMultipleChoiceField(
        queryset=Etiqueta.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Etiquetas',
    )
>>>>>>> 5e8b77262c1d3e549eda0a03f3d9cee82d212379

    class Meta:
        model = Reserva
        fields = [
            'id_personal_servicio',
            'fecha',
            'hora',
            'etiquetas',
        ]

        labels = {
<<<<<<< HEAD
            'id_personal_servicio': 'Elija un servicio y profesional',
=======
            'id_personal_servicio': 'Elija un servicio',
            'id_cliente': 'Ingrese su nombre',
            'id_personal': 'Eliga un profesional',
>>>>>>> 5e8b77262c1d3e549eda0a03f3d9cee82d212379
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

<<<<<<< HEAD
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_personal_servicio'].queryset = (
            ServicioPersonal.objects.select_related('id_servicio', 'id_personal')
        )
=======
    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < date.today():
            raise forms.ValidationError('La fecha de la reserva no puede ser anterior a hoy.')
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        profesional = cleaned_data.get('id_personal')

        if fecha and hora and profesional:
            reservas_iguales = Reserva.objects.filter(
                id_personal=profesional,
                fecha=fecha,
                hora=hora,
            )
            if self.instance.pk:
                reservas_iguales = reservas_iguales.exclude(pk=self.instance.pk)
            if reservas_iguales.exists():
                raise forms.ValidationError(
                    f'El profesional ya tiene una reserva agendada para {fecha} a las {hora}. Elige otro horario.'
                )

        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        etiquetas = self.cleaned_data.get('etiquetas', [])
        if commit:
            reserva.save()
            reserva.etiquetas.set(etiquetas)
        return reserva

>>>>>>> 5e8b77262c1d3e549eda0a03f3d9cee82d212379

class AutenticacionForm(forms.Form):
    nombre = forms.CharField(max_length=100, label='Ingrese su Nombre')
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Contraseña',
    )
<<<<<<< HEAD


class AutenticacionClienteForm(AutenticacionForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Teléfono',
    )
    
=======
>>>>>>> 5e8b77262c1d3e549eda0a03f3d9cee82d212379
