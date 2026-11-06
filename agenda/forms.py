from django import forms
from .models import Reserva, Cliente

class ReservaForm(forms.ModelForm):
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
    model = Cliente
    fields = [
        'nombre_c',
        'token',
    ]
    labels= {
        'nombre_c': 'Ingrese su Nombre',
        'token': 'Ingrese su Token de Acceso',
    }