from django.shortcuts import render, redirect
from .forms import *
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from .models import *


def es_staff(user):
    return user.is_authenticated and user.is_staff


# Create your views here.
def home(request):
    citas = Reserva.objects.select_related(
        'id_cliente',
        'id_personal_servicio',
        'id_personal',
    ).all()
    return render(request, 'home_cliente.html', {'citas': citas})


def dashboard(request):
    return render(request, 'dashboard.html')


def agendar_cita(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reserva creada correctamente. Tu cita ha sido registrada.')
            return redirect('home')
    else:
        form = ReservaForm()
    return render(request, 'agendar_cita_cliente.html', {'form': form})


def ver_citas(request):
    return render(request, 'ver_citas_cliente.html')


@user_passes_test(es_staff, login_url='login')
def vista_administracion(request):
    return render(request, 'vista_administracion.html')


@user_passes_test(es_staff, login_url='login')
def agendar_cita_admin(request):
    return render(request, 'agendar_cita_admin.html')


@user_passes_test(es_staff, login_url='login')
def clientes_admin(request):
    query = request.GET.get('q')
    if query:
        resultados = Cliente.objects.filter(Q(nombre_c__icontains=query) | Q(correo__icontains=query))
    else:
        resultados = Cliente.objects.all()
    return render(request, 'clientes_admin.html', {'clientes': resultados})


@user_passes_test(es_staff, login_url='login')
def servicios_admin(request):
    return render(request, 'servicios_admin.html')


@user_passes_test(es_staff, login_url='login')
def notificaciones_admin(request):
    return render(request, 'notificaciones_admin.html')


@user_passes_test(es_staff, login_url='login')
def auditoria_admin(request):
    return render(request, 'auditoria_admin.html')


@user_passes_test(es_staff, login_url='login')
def configuracion_admin(request):
    return render(request, 'configuracion_admin.html')


def acceso_denegado(request):
    return render(request, 'acceso_denegado.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('vista_administracion')

    if request.method == 'POST':
        form = AutenticacionForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            password = form.cleaned_data['password']
            user = authenticate(request, username=nombre, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('vista_administracion')
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionForm()
    return render(request, 'login_admin.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('home')
