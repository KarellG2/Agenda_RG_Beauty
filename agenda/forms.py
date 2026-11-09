from datetime import datetime, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
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


def reserva_se_superpone(servicio, fecha, hora, excluir_reserva=None):
    inicio_nuevo = datetime.combine(fecha, hora)
    fin_nuevo = inicio_nuevo + timedelta(
        minutes=servicio.duracion_aproximada,
    )
    reservas_existentes = Reserva.objects.filter(
        id_personal=servicio.id_personal,
        fecha=fecha,
    ).exclude(estado='cancelado').select_related('id_personal_servicio')

    for reserva in reservas_existentes:
        if excluir_reserva and reserva.pk == excluir_reserva.pk:
            continue
        inicio_existente = datetime.combine(fecha, reserva.hora)
        fin_existente = inicio_existente + timedelta(
            minutes=reserva.id_personal_servicio.duracion_aproximada,
        )
        if inicio_nuevo < fin_existente and inicio_existente < fin_nuevo:
            return True
    return False


class ServicioForm(forms.ModelForm):
    personal = forms.ModelChoiceField(
        queryset=Personal.objects.none(),
        label='Profesional a cargo',
        help_text='Selecciona quién realizará este servicio.',
        error_messages={'required': 'Selecciona al profesional a cargo.'},
        widget=forms.Select(attrs={'class': 'admin-field'}),
    )
    duracion_aproximada = forms.IntegerField(
        min_value=1,
        label='Duración aproximada (minutos)',
        help_text='Tiempo que se reservará en la agenda para este servicio.',
        error_messages={
            'required': 'Indica la duración aproximada.',
            'min_value': 'La duración debe ser de al menos un minuto.',
            'invalid': 'Ingresa una duración válida en minutos.',
        },
        widget=forms.NumberInput(attrs={
            'class': 'admin-field',
            'min': 1,
        }),
    )
    precio = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label='Precio (CLP)',
        help_text='Ingresa el valor del servicio en pesos chilenos.',
        error_messages={
            'required': 'Indica el precio del servicio.',
            'min_value': 'El precio no puede ser negativo.',
            'invalid': 'Ingresa un precio válido.',
        },
        widget=forms.NumberInput(attrs={
            'class': 'admin-field',
            'min': 0,
            'step': '0.01',
        }),
    )

    class Meta:
        model = Servicio
        fields = ['nombre_s', 'descripcion', 'categoria']
        labels = {
            'nombre_s': 'Nombre del servicio',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
        }
        help_texts = {
            'nombre_s': 'Usa un nombre breve y fácil de reconocer al reservar.',
            'descripcion': 'Describe qué incluye el servicio.',
            'categoria': 'Clasifica el servicio para facilitar su búsqueda.',
        }
        widgets = {
            'nombre_s': forms.TextInput(attrs={'class': 'admin-field'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'admin-field admin-textarea',
                'rows': 4,
            }),
            'categoria': forms.Select(attrs={'class': 'admin-field'}),
        }
        error_messages = {
            'nombre_s': {
                'required': 'Ingresa el nombre del servicio.',
                'max_length': 'El nombre no puede superar los 100 caracteres.',
            },
            'descripcion': {
                'required': 'Ingresa una descripción del servicio.',
            },
        }

    def clean_nombre_s(self):
        nombre = self.cleaned_data['nombre_s'].strip()
        if not nombre:
            raise ValidationError('Ingresa el nombre del servicio.')
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if not descripcion:
            raise ValidationError('Ingresa una descripción del servicio.')
        return descripcion

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = CategoriaServicio.objects.order_by(
            'nombre'
        )
        self.fields['personal'].queryset = Personal.objects.select_related(
            'id_rol'
        ).order_by('nombre')
        if self.instance.pk:
            asignacion = self.instance.personal_asignado.order_by(
                'id_personal__nombre'
            ).first()
            if asignacion:
                self.initial.update({
                    'personal': asignacion.id_personal_id,
                    'duracion_aproximada': asignacion.duracion_aproximada,
                    'precio': asignacion.precio,
                })

    def save_asignacion(self, servicio):
        ServicioPersonal.objects.update_or_create(
            id_servicio=servicio,
            id_personal=self.cleaned_data['personal'],
            defaults={
                'duracion_aproximada': self.cleaned_data['duracion_aproximada'],
                'precio': self.cleaned_data['precio'],
            },
        )


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['nombre_rol', 'descripcion']
        labels = {
            'nombre_rol': 'Nombre del cargo o especialidad',
            'descripcion': 'Descripción',
        }
        widgets = {
            'nombre_rol': forms.TextInput(attrs={'class': 'admin-field'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'admin-field admin-textarea',
                'rows': 4,
            }),
        }
        error_messages = {
            'nombre_rol': {
                'required': 'Ingresa el nombre del cargo o especialidad.',
            },
            'descripcion': {'required': 'Ingresa una descripción.'},
        }

    def clean_nombre_rol(self):
        nombre = self.cleaned_data['nombre_rol'].strip()
        if not nombre:
            raise ValidationError('Ingresa el nombre del cargo o especialidad.')
        if Rol.objects.filter(nombre_rol__iexact=nombre).exists():
            raise ValidationError('Ya existe un cargo o especialidad con ese nombre.')
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if not descripcion:
            raise ValidationError('Ingresa una descripción.')
        return descripcion


class PersonalForm(forms.ModelForm):
    class Meta:
        model = Personal
        fields = ['nombre', 'credenciales', 'años_experiencia', 'id_rol']
        labels = {
            'nombre': 'Nombre del profesional',
            'credenciales': 'Credenciales o formación',
            'años_experiencia': 'Años de experiencia',
            'id_rol': 'Cargo o especialidad',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'admin-field'}),
            'credenciales': forms.TextInput(attrs={'class': 'admin-field'}),
            'años_experiencia': forms.NumberInput(attrs={
                'class': 'admin-field',
                'min': 0,
            }),
            'id_rol': forms.Select(attrs={'class': 'admin-field'}),
        }
        error_messages = {
            'nombre': {'required': 'Ingresa el nombre del profesional.'},
            'credenciales': {'required': 'Ingresa sus credenciales o formación.'},
            'años_experiencia': {
                'required': 'Ingresa los años de experiencia.',
                'invalid': 'Ingresa una cantidad válida de años.',
                'min_value': 'Los años de experiencia no pueden ser negativos.',
            },
            'id_rol': {'required': 'Selecciona un cargo o especialidad.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_rol'].queryset = Rol.objects.order_by('nombre_rol')

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise ValidationError('Ingresa el nombre del profesional.')
        return nombre

    def clean_credenciales(self):
        credenciales = self.cleaned_data['credenciales'].strip()
        if not credenciales:
            raise ValidationError('Ingresa sus credenciales o formación.')
        return credenciales


class EtiquetaForm(forms.ModelForm):
    color = forms.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        label='Color',
        error_messages={
            'required': 'Selecciona un color.',
            'invalid': 'El color debe estar en formato hexadecimal, por ejemplo #D9C7CC.',
        },
        widget=forms.TextInput(attrs={
            'class': 'admin-field tag-color-input',
            'type': 'color',
        }),
    )

    class Meta:
        model = Etiqueta
        fields = ['nombre', 'color']
        labels = {'nombre': 'Nombre de la etiqueta'}
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'admin-field'}),
        }
        error_messages = {
            'nombre': {
                'required': 'Ingresa el nombre de la etiqueta.',
                'max_length': 'El nombre no puede superar los 50 caracteres.',
            },
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise ValidationError('Ingresa el nombre de la etiqueta.')
        if Etiqueta.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError('Ya existe una etiqueta con ese nombre.')
        return nombre


class CategoriaServicioForm(forms.ModelForm):
    class Meta:
        model = CategoriaServicio
        fields = ['nombre', 'descripcion']
        labels = {
            'nombre': 'Nombre de la categoría',
            'descripcion': 'Descripción (opcional)',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'admin-field'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'admin-field admin-textarea',
                'rows': 4,
            }),
        }
        error_messages = {
            'nombre': {
                'required': 'Ingresa el nombre de la categoría.',
                'max_length': 'El nombre no puede superar los 100 caracteres.',
            },
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise ValidationError('Ingresa el nombre de la categoría.')
        if CategoriaServicio.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError('Ya existe una categoría con ese nombre.')
        return nombre

    def clean_descripcion(self):
        return self.cleaned_data['descripcion'].strip()


class ReservaForm(forms.ModelForm):
    hora = forms.ChoiceField(
        choices=HORARIOS_DISPONIBLES,
        label='Horario',
        help_text='Solo se mostrarán horarios disponibles para el profesional.',
        error_messages={'required': 'Selecciona un horario para la cita.'},
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    nombre_cliente = forms.CharField(
        max_length=100,
        label='Ingrese su Nombre',
        help_text='Nombre de la persona que asistirá a la cita.',
        error_messages={'required': 'Ingresa tu nombre.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    telefono_cliente = forms.CharField(
        max_length=20,
        label='Ingrese su Teléfono',
        help_text='Lo usaremos para identificar tu reserva.',
        error_messages={'required': 'Ingresa tu teléfono.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    correo_cliente = forms.EmailField(
        max_length=100,
        label='Ingrese su Correo Electrónico',
        help_text='Ingresa un correo válido para los datos de tu reserva.',
        error_messages={
            'required': 'Ingresa tu correo electrónico.',
            'invalid': 'Ingresa un correo electrónico válido.',
        },
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

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
            'etiquetas': 'Etiquetas (opcional)',
        }

        help_texts = {
            'id_personal_servicio': (
                'Cada opción muestra el servicio, el profesional, el precio '
                'y la duración.'
            ),
            'fecha': 'Elige una fecha desde hoy en adelante.',
            'etiquetas': 'Puedes seleccionar más de una etiqueta.',
        }

        widgets = {
            'id_personal_servicio': forms.Select(attrs={
                'class': 'form-control',
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'etiquetas': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].widget.attrs['min'] = timezone.localdate().isoformat()
        self.fields['id_personal_servicio'].queryset = (
            ServicioPersonal.objects.select_related(
                'id_servicio',
                'id_personal',
            ).order_by('id_servicio__nombre_s', 'id_personal__nombre')
        )
        self.fields['etiquetas'].queryset = Etiqueta.objects.order_by('nombre')
        if cliente:
            for field_name, value in (
                ('nombre_cliente', cliente.nombre_c),
                ('telefono_cliente', cliente.telefono),
                ('correo_cliente', cliente.correo),
            ):
                self.fields[field_name].initial = value
                self.fields[field_name].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        servicio = cleaned_data.get('id_personal_servicio')
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        if fecha and fecha < timezone.localdate():
            self.add_error('fecha', 'La fecha de la cita no puede estar en el pasado.')
        if (
            servicio
            and fecha
            and hora
            and reserva_se_superpone(
                servicio,
                fecha,
                datetime.strptime(hora, '%H:%M').time(),
                excluir_reserva=self.instance if self.instance.pk else None,
            )
        ):
            self.add_error(
                'hora',
                'Ese profesional ya tiene una cita en ese horario.',
            )
        return cleaned_data


class ReservaAdminForm(ReservaForm):
    estado = forms.ChoiceField(
        choices=Reserva.ESTADOS,
        label='Estado de la reserva',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta(ReservaForm.Meta):
        fields = [*ReservaForm.Meta.fields, 'estado']


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


class AutenticacionClienteForm(forms.Form):
    nombre = forms.CharField(
        max_length=100,
        label='Nombre',
        error_messages={
            'required': 'Ingresa tu nombre.',
        },
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'class': 'form-control',
        }),
    )
    password = forms.CharField(
        label='Contraseña (tu teléfono)',
        error_messages={'required': 'Ingresa tu teléfono como contraseña.'},
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
        }),
    )

class ClienteUpdateForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre_c', 'telefono', 'correo']
        labels = {
            'nombre_c': 'Nombre',
            'telefono': 'Teléfono',
            'correo': 'Correo electrónico',
        }
        widgets = {
            'nombre_c': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        
    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()
        if Cliente.objects.filter(correo__iexact=correo).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este correo ya está en uso')
        return correo
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono').strip()
        if Cliente.objects.filter(telefono=telefono).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este teléfono ya está en uso')
        return telefono