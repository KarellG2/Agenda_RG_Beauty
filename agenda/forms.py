from datetime import date

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
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
    nombre = forms.CharField(
        max_length=100,
        label='Ingrese su Nombre',
        error_messages={'required': 'Ingresa tu nombre de usuario.'},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Ingrese su Contraseña',
        error_messages={'required': 'Ingresa tu contraseña.'},
    )


class RegistroClienteForm(forms.Form):
    nombre = forms.CharField(
        max_length=100,
        label='Nombre completo',
        error_messages={'required': 'Ingresa tu nombre.'},
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'class': 'form-control',
        }),
    )
    telefono = forms.CharField(
        max_length=20,
        label='Teléfono',
        error_messages={'required': 'Ingresa tu teléfono.'},
        widget=forms.TextInput(attrs={
            'autocomplete': 'tel',
            'class': 'form-control',
        }),
    )
    correo = forms.EmailField(
        max_length=150,
        label='Correo electrónico',
        error_messages={
            'required': 'Ingresa tu correo electrónico.',
            'invalid': 'Ingresa un correo electrónico válido.',
        },
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
        }),
    )
    password1 = forms.CharField(
        label='Contraseña',
        error_messages={'required': 'Ingresa una contraseña.'},
        help_text=(
            'Mínimo 8 caracteres, una mayúscula, un número y un carácter especial.'
        ),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
        }),
    )
    password2 = forms.CharField(
        label='Repetir contraseña',
        error_messages={'required': 'Repite tu contraseña.'},
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
        }),
    )

    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=correo).exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return correo

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        telefono = cleaned_data.get('telefono')
        correo = cleaned_data.get('correo')
        if nombre and telefono and correo:
            clientes_correo = Cliente.objects.filter(correo__iexact=correo)
            if clientes_correo.exists():
                coincidencias = clientes_correo.filter(
                    nombre_c__iexact=nombre.strip(),
                    telefono=telefono.strip(),
                    usuario__isnull=True,
                )
                if clientes_correo.filter(usuario__isnull=False).exists():
                    self.add_error('correo', 'Este correo ya tiene una cuenta.')
                elif coincidencias.count() == 1:
                    cleaned_data['cliente_existente'] = coincidencias.first()
                else:
                    self.add_error(
                        'correo',
                        'Ya hay un perfil con este correo. Verifica nombre y teléfono.',
                    )

        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    password_validation.validate_password(password2)
                except ValidationError as error:
                    self.add_error('password2', error)
        return cleaned_data


class AutenticacionClienteForm(forms.Form):
    correo = forms.EmailField(
        max_length=150,
        label='Correo electrónico',
        error_messages={
            'required': 'Ingresa tu correo electrónico.',
            'invalid': 'Ingresa un correo electrónico válido.',
        },
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        error_messages={'required': 'Ingresa tu contraseña.'},
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
        }),
    )
