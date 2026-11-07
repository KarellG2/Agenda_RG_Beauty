from django.shortcuts import render
from .forms import ReservaForm
from django.contrib.auth import login
from django.contrib import messages
from .models import Reserva
# Create your views here.

def home(request):
    return render(request, 'home.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def agendar_cita(request):
    return render(request, 'agendar_cita.html')

def ver_citas(request):
    return render(request, 'ver_citas.html')

def agendar_cita(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'cita_agendada.html')  # REDIRIGE PAGINA CONFIRMACION
    else:
        form = ReservaForm()
    return render(request, 'agendar_cita.html', {'form': form})

def vista_administracion(request):
    return render(request, 'dashboard_admin.html')


def agendar_cita_admin(request):
    return render(request, 'agendar_cita_admin.html')


def clientes_admin(request):
    return render(request, 'clientes_admin.html')


def servicios_admin(request):
    return render(request, 'servicios_admin.html')


def notificaciones_admin(request):
    return render(request, 'notificaciones_admin.html')


def auditoria_admin(request):
    return render(request, 'auditoria_admin.html')


def configuracion_admin(request):
    return render(request, 'configuracion_admin.html')