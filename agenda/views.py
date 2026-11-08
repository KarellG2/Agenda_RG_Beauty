from django.shortcuts import render, redirect
from .forms import *
from django.contrib.admin.views.decorators import staff_member_required
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
        'id_personal'
        ).all()
    
    return render(request, 'home_cliente.html', {'citas': citas})

def dashboard(request):
    return render(request, 'dashboard.html')

def agendar_cita(request):
    return render(request, 'agendar_cita_cliente.html')

def ver_citas_cliente(request):

    cliente_id = request.session.get('cliente_id')
    if not cliente_id:
        return redirect('login_cliente')

    cliente_actual = Cliente.objects.get(id_cliente=cliente_id)

    citas = Reserva.objects.filter(
        id_cliente=cliente_actual
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
            cliente = Cliente.objects.get_or_create(
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
            return redirect('home')

    else:
        form = ReservaForm()
    return render(request, 'agendar_cita_cliente.html', {'form': form})
#VISTA ADMINISTRACION

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
                return redirect('vista_administracion')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionForm()
    return render(request, 'login_admin.html', {'form': form})

def logout_view(request):
    logout(request)
    request.session.pop('cliente_id', None)
    return redirect('home')
def login_cliente_legacy(request):
    if request.user.is_authenticated:
        return redirect('home')  

    if request.method == 'POST':
        form = AutenticacionForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            password = form.cleaned_data['telefono']
            user = authenticate(request, username=nombre, password=password)
            if user is not None:
                login(request, user)
                return redirect('home') 
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionForm()
    return render(request, 'login_cliente.html', {'form': form})


def login_cliente(request):
    if request.user.is_authenticated or request.session.get('cliente_id'):
        return redirect('home')

    if request.method == 'POST':
        form = AutenticacionClienteForm(request.POST)
        if form.is_valid():
            cliente = Cliente.objects.filter(
                nombre_c=form.cleaned_data['nombre'],
                telefono=form.cleaned_data['password'],
            ).first()
            if cliente is not None:
                request.session['cliente_id'] = cliente.id_cliente
                return redirect('home')
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    else:
        form = AutenticacionClienteForm()
    return render(request, 'login_cliente.html', {'form': form})