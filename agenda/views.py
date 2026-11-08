from datetime import date

from django.shortcuts import get_object_or_404, render, redirect
from .forms import *
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Max, Min, Q
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_POST
from .models import *


def es_staff(user):
    return user.is_authenticated and user.is_staff


def es_cliente(user):
    return (
        user.is_authenticated
        and not user.is_staff
        and Cliente.objects.filter(usuario=user).exists()
    )


# Create your views here.
def home(request):
    if es_cliente(request.user):
        return redirect('landing_cliente')

    servicios = Servicio.objects.select_related('categoria').annotate(
        precio_minimo=Min('personal_asignado__precio'),
        precio_maximo=Max('personal_asignado__precio'),
    ).order_by('nombre_s')
    return render(request, 'landing_publica.html', {'servicios': servicios})


@user_passes_test(es_cliente, login_url='login_cliente')
def landing_cliente(request):
    cliente = get_object_or_404(Cliente, usuario=request.user)
    citas = Reserva.objects.filter(
        id_cliente=cliente,
        fecha__gte=date.today(),
    ).select_related(
        'id_personal',
        'id_personal_servicio__id_servicio',
    ).order_by('fecha', 'hora')
    return render(
        request,
        'home_cliente.html',
        {'citas': citas, 'cliente': cliente, 'landing_cliente': True},
    )


def dashboard(request):
    return render(request, 'dashboard.html')

def agendar_cita(request):
    return render(request, 'agendar_cita_cliente.html')

def ver_citas_cliente(request):
    cliente = None
    if request.user.is_authenticated and not request.user.is_staff:
        cliente = Cliente.objects.filter(usuario=request.user).first()
    if cliente is None:
        cliente_id = request.session.get('cliente_id')
        if cliente_id:
            cliente = Cliente.objects.filter(id_cliente=cliente_id).first()
    if cliente is None:
        return redirect('login_cliente')

    citas = Reserva.objects.filter(
        id_cliente=cliente
    ).select_related(
        'id_personal',
        'id_personal_servicio__id_servicio',
        'id_personal_servicio__id_personal'
    ).order_by('fecha', 'hora')
    
    return render(request, 'ver_citas_cliente.html', {'citas': citas})

def agendar_cita(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            cliente = None
            if request.user.is_authenticated and not request.user.is_staff:
                cliente = Cliente.objects.filter(usuario=request.user).first()
            if cliente is None:
                cliente, _ = Cliente.objects.get_or_create(
                    correo=form.cleaned_data['correo_cliente'],
                    defaults={
                        'nombre_c': form.cleaned_data['nombre_cliente'],
                        'telefono': form.cleaned_data['telefono_cliente'],
                    },
                )
            reserva = form.save(commit=False)
            reserva.id_cliente = cliente
            reserva.id_personal = reserva.id_personal_servicio.id_personal
            reserva.save()
            form.save_m2m()
            messages.success(request, 'La cita se guardó correctamente.')
            return redirect('home')

    else:
        form = ReservaForm()
    return render(request, 'agendar_cita_cliente.html', {'form': form})
#VISTA ADMINISTRACION


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
        resultados = Cliente.objects.filter(
            Q(nombre_c__icontains=query) | Q(correo__icontains=query)
        )
    else:
        resultados = Cliente.objects.all()
    resultados = resultados.order_by('nombre_c', 'id_cliente')
    return render(request, 'clientes_admin.html', {'clientes': resultados})


@user_passes_test(es_staff, login_url='login')
def servicios_admin(request):
    servicios = Servicio.objects.all()
    return render(request, 'servicios_admin.html', {'servicios': servicios})

@user_passes_test(es_staff, login_url='login')
def notificaciones_admin(request):
    return render(request, 'notificaciones_admin.html')


@user_passes_test(es_staff, login_url='login')
def auditoria_admin(request):
    return render(request, 'auditoria_admin.html')


@user_passes_test(es_staff, login_url='login')
def configuracion_admin(request):
    return render(request, 'configuracion_admin.html')

#MANEJO LOGIN Y LOGOUT 

def acceso_denegado(request):
    return render(request, 'acceso_denegado.html')


def acceso(request):
    if request.user.is_authenticated:
        return redirect(
            'agendar_cita_admin' if request.user.is_staff else 'agendar_cita'
        )
    return render(request, 'acceso.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('agendar_cita_admin')

    if request.method == 'POST':
        form = AutenticacionForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            password = form.cleaned_data['password']
            user = authenticate(request, username=nombre, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('agendar_cita_admin')
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionForm()
    return render(request, 'login_admin.html', {'form': form})


def logout_view(request):
    logout(request)
    request.session.pop('cliente_id', None)
    return redirect('home')

def login_cliente(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('agendar_cita_admin')
    if es_cliente(request.user):
        return redirect('agendar_cita')

    if request.method == 'POST':
        form = AutenticacionClienteForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            user = authenticate(
                request,
                username=correo,
                password=form.cleaned_data['password'],
            )
            if (
                user is not None
                and not user.is_staff
                and Cliente.objects.filter(usuario=user).exists()
            ):
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('agendar_cita')
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionClienteForm()
    return render(request, 'login_cliente.html', {'form': form})


def registro_cliente(request):
    if request.user.is_authenticated:
        return redirect('agendar_cita_admin' if request.user.is_staff else 'home')

    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            user_model = get_user_model()
            with transaction.atomic():
                user = user_model.objects.create_user(
                    username=correo,
                    email=correo,
                    password=form.cleaned_data['password1'],
                )
                cliente_existente = form.cleaned_data.get('cliente_existente')
                if cliente_existente:
                    cliente_existente.usuario = user
                    cliente_existente.save(update_fields=['usuario'])
                else:
                    Cliente.objects.create(
                        nombre_c=form.cleaned_data['nombre'],
                        telefono=form.cleaned_data['telefono'],
                        correo=correo,
                        usuario=user,
                    )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Tu cuenta de cliente se creó correctamente.')
            return redirect('agendar_cita')
    else:
        form = RegistroClienteForm()
    return render(request, 'registro_cliente.html', {'form': form})
