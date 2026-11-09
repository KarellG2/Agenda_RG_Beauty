from datetime import date, datetime, timedelta
from uuid import uuid4

from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect
from .forms import *
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Max, Min, Q
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import *

from django.core.paginator import Paginator

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


def _cliente_actual(request):
    if request.user.is_authenticated and not request.user.is_staff:
        cliente = Cliente.objects.filter(usuario=request.user).first()
        if cliente:
            return cliente
    cliente_id = request.session.get('cliente_id')
    if cliente_id:
        return Cliente.objects.filter(id_cliente=cliente_id).first()
    return None


def _reserva_permitida(request, pk):
    cliente = _cliente_actual(request)
    if not request.user.is_staff and cliente is None:
        return None, redirect('login_cliente')

    reserva = get_object_or_404(
        Reserva.objects.select_related(
            'id_cliente',
            'id_personal',
            'id_personal_servicio__id_servicio',
            'id_personal_servicio__id_personal',
        ).prefetch_related('etiquetas'),
        pk=pk,
    )
    if not request.user.is_staff and reserva.id_cliente_id != cliente.pk:
        return None, render(request, 'acceso_denegado.html', status=403)
    return reserva, None


def reserva_detalle(request, pk):
    reserva, respuesta = _reserva_permitida(request, pk)
    if respuesta:
        return respuesta
    return render(request, 'reserva_detalle.html', {'reserva': reserva})


def reserva_editar(request, pk):
    reserva, respuesta = _reserva_permitida(request, pk)
    if respuesta:
        return respuesta

    es_admin = request.user.is_staff
    form_class = ReservaAdminForm if es_admin else ReservaForm
    if request.method == 'POST':
        form = form_class(request.POST, instance=reserva, cliente=reserva.id_cliente)
        if form.is_valid():
            with transaction.atomic():
                reserva = form.save(commit=False)
                reserva.id_personal = reserva.id_personal_servicio.id_personal
                reserva.save()
                form.save_m2m()
            messages.success(request, 'La reserva se actualizó correctamente.')
            return redirect('reserva_detalle', pk=reserva.pk)
    elif request.method == 'GET':
        form = form_class(instance=reserva, cliente=reserva.id_cliente)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])

    return render(request, 'reserva_admin_form.html', {
        'form': form,
        'reserva': reserva,
        'es_admin': es_admin,
    })


def reserva_eliminar(request, pk):
    reserva, respuesta = _reserva_permitida(request, pk)
    if respuesta:
        return respuesta
    if request.method == 'GET':
        return render(request, 'reserva_confirmar_eliminar.html', {
            'reserva': reserva,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    reserva.delete()
    messages.success(request, 'La reserva se eliminó correctamente.')
    return redirect(
        'agendar_cita_admin' if request.user.is_staff else 'ver_citas_cliente'
    )


def agendar_cita(request):
    cliente = None
    if request.user.is_authenticated and not request.user.is_staff:
        cliente = Cliente.objects.filter(usuario=request.user).first()

    if request.method == 'POST':
        form = ReservaForm(request.POST, cliente=cliente)
        if form.is_valid():
            user_model = get_user_model()
            nuevo_usuario = None
            with transaction.atomic():
                if cliente is None:
                    correo = form.cleaned_data['correo_cliente'].strip().lower()
                    telefono = form.cleaned_data['telefono_cliente'].strip()
                    clientes_por_correo = Cliente.objects.filter(
                        correo__iexact=correo,
                    ).order_by('id_cliente')
                    clientes_por_telefono = Cliente.objects.filter(
                        telefono=telefono,
                    ).order_by('id_cliente')
                    cliente_correo = clientes_por_correo.first()
                    cliente_telefono = clientes_por_telefono.first()
                    if (
                        cliente_correo
                        and cliente_telefono
                        and cliente_correo.pk != cliente_telefono.pk
                    ):
                        form.add_error(
                            'telefono_cliente',
                            'El teléfono y el correo pertenecen a clientes distintos. '
                            'Inicia sesión con tu cuenta antes de reservar.',
                        )
                        return render(
                            request,
                            'agendar_cita_cliente.html',
                            {'form': form},
                        )

                    cliente = cliente_correo or cliente_telefono
                    if cliente and cliente.usuario_id:
                        if cliente.telefono != telefono:
                            form.add_error(
                                'telefono_cliente',
                                'Este cliente ya tiene una cuenta. Inicia sesión para reservar.',
                            )
                            return render(
                                request,
                                'agendar_cita_cliente.html',
                                {'form': form},
                            )
                        if not cliente.usuario.check_password(telefono):
                            form.add_error(
                                'telefono_cliente',
                                'Esta cuenta ya está registrada. Inicia sesión para reservar.',
                            )
                            return render(
                                request,
                                'agendar_cita_cliente.html',
                                {'form': form},
                            )
                        nuevo_usuario = cliente.usuario
                    else:
                        if cliente is None:
                            cliente = Cliente.objects.create(
                                nombre_c=form.cleaned_data['nombre_cliente'].strip(),
                                telefono=telefono,
                                correo=correo,
                            )
                        else:
                            cliente.nombre_c = form.cleaned_data[
                                'nombre_cliente'
                            ].strip()
                            cliente.telefono = telefono
                            cliente.correo = correo
                            cliente.save(update_fields=[
                                'nombre_c',
                                'telefono',
                                'correo',
                            ])

                        nuevo_usuario = user_model.objects.create_user(
                            username=f'cliente_{uuid4().hex}',
                            email=correo,
                            password=telefono,
                        )
                        cliente.usuario = nuevo_usuario
                        cliente.save(update_fields=['usuario'])

                reserva = form.save(commit=False)
                reserva.id_cliente = cliente
                reserva.id_personal = reserva.id_personal_servicio.id_personal
                reserva.save()
                form.save_m2m()

            if nuevo_usuario and not request.user.is_authenticated:
                login(
                    request,
                    nuevo_usuario,
                    backend='django.contrib.auth.backends.ModelBackend',
                )
            request.session['cliente_id'] = cliente.id_cliente
            messages.success(
                request,
                'La cita se guardó correctamente. Tu cuenta está lista y ya iniciaste sesión.',
            )
            return redirect('ver_citas_cliente')
    else:
        form = ReservaForm(cliente=cliente)
    return render(request, 'agendar_cita_cliente.html', {'form': form})
#VISTA ADMINISTRACION


def ver_citas(request):
    return render(request, 'ver_citas_cliente.html')


@user_passes_test(es_staff, login_url='login')
def vista_administracion(request):
    hoy = timezone.localdate()
    citas_hoy = Reserva.objects.filter(fecha=hoy)
    total_reservas = Reserva.objects.count()
    canceladas = Reserva.objects.filter(estado='cancelado').count()
    tasa_cancelacion = (
        round(canceladas * 100 / total_reservas, 1)
        if total_reservas else 0
    )
    return render(request, 'vista_administracion.html', {
        'citas_hoy': citas_hoy.count(),
        'pendientes': Reserva.objects.filter(estado='pendiente').count(),
        'confirmadas': Reserva.objects.filter(estado='confirmado').count(),
        'canceladas': canceladas,
        'total_reservas': total_reservas,
        'clientes_registrados': Cliente.objects.count(),
        'profesionales_registrados': Personal.objects.count(),
        'servicios_registrados': Servicio.objects.count(),
        'tasa_cancelacion': tasa_cancelacion,
    })


@user_passes_test(es_staff, login_url='login')
def agendar_cita_admin(request):
    hoy = timezone.localdate()
    fecha_param = request.GET.get('fecha')
    try:
        fecha_seleccionada = (
            date.fromisoformat(fecha_param) if fecha_param else hoy
        )
    except ValueError:
        fecha_seleccionada = hoy
        messages.warning(request, 'La fecha indicada no es válida; se muestra la fecha de hoy.')

    vista = request.GET.get('vista', 'diaria')
    if vista not in {'diaria', 'semanal'}:
        vista = 'diaria'
    inicio_semana = fecha_seleccionada - timedelta(days=fecha_seleccionada.weekday())
    inicio_periodo = inicio_semana if vista == 'semanal' else fecha_seleccionada
    fin_periodo = inicio_periodo + timedelta(days=6 if vista == 'semanal' else 0)

    query = Reserva.objects.filter(
        fecha__range=(inicio_periodo, fin_periodo),
    ).select_related(
        'id_cliente',
        'id_personal',
        'id_personal_servicio__id_servicio',
    ).prefetch_related('etiquetas')

    cliente_busqueda = request.GET.get('cliente', '').strip()
    if cliente_busqueda:
        query = query.filter(
            Q(id_cliente__nombre_c__icontains=cliente_busqueda)
            | Q(id_cliente__telefono__icontains=cliente_busqueda)
            | Q(id_cliente__correo__icontains=cliente_busqueda)
        )

    servicio_filtro = request.GET.get('servicio', '')
    if servicio_filtro.isdigit():
        query = query.filter(
            id_personal_servicio__id_servicio_id=int(servicio_filtro),
        )
    else:
        servicio_filtro = ''

    estados = Reserva.ESTADOS
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro in dict(estados):
        query = query.filter(estado=estado_filtro)
    else:
        estado_filtro = ''

    asignaciones = list(ServicioPersonal.objects.all())
    dias = []
    for offset in range((fin_periodo - inicio_periodo).days + 1):
        dia = inicio_periodo + timedelta(days=offset)
        reservas_dia = list(
            Reserva.objects.filter(fecha=dia).exclude(
                estado='cancelado',
            ).select_related('id_personal_servicio')
        )
        horas_disponibles = []
        for hora, _ in HORARIOS_DISPONIBLES:
            inicio_hora = datetime.strptime(hora, '%H:%M').time()
            inicio_nuevo = datetime.combine(dia, inicio_hora)
            existe_asignacion_disponible = any(
                not any(
                    reserva.id_personal_id == asignacion.id_personal_id
                    and inicio_nuevo
                    < datetime.combine(dia, reserva.hora) + timedelta(
                        minutes=reserva.id_personal_servicio.duracion_aproximada,
                    )
                    and datetime.combine(dia, reserva.hora)
                    < inicio_nuevo + timedelta(
                        minutes=asignacion.duracion_aproximada,
                    )
                    for reserva in reservas_dia
                )
                for asignacion in asignaciones
            )
            if existe_asignacion_disponible:
                horas_disponibles.append(inicio_hora)
        dias.append({
            'fecha': dia,
            'horas': horas_disponibles,
        })

    return render(request, 'agendar_cita_admin.html', {
        'reservas': query.order_by('fecha', 'hora', 'id_personal__nombre'),
        'servicios': Servicio.objects.order_by('nombre_s'),
        'disponibilidad': dias,
        'fecha_seleccionada': fecha_seleccionada,
        'vista': vista,
        'cliente_busqueda': cliente_busqueda,
        'servicio_filtro': servicio_filtro,
        'estado_filtro': estado_filtro,
        'estados': estados,
    })


@user_passes_test(es_staff, login_url='login')
def clientes_admin(request):
    query = request.GET.get('q')
    if query:
        resultados = Cliente.objects.filter(
            Q(nombre_c__icontains=query)
            | Q(correo__icontains=query)
            | Q(telefono__icontains=query)
        )
    else:
        resultados = Cliente.objects.all()
    resultados = resultados.annotate(
        cantidad_reservas=Count('reservas', distinct=True),
    ).order_by('nombre_c', 'id_cliente')

    paginator = Paginator(resultados, 10)  # 10 RESULTADOS PAGINA
    page_number = request.GET.get('page') # NUMERO PAGINA
    page_obj = paginator.get_page(page_number)

    return render(request, 'clientes_admin.html', {'clientes': page_obj})


@user_passes_test(es_staff, login_url='login')
def servicios_admin(request):
    servicios = Servicio.objects.select_related('categoria').annotate(
        precio_minimo=Min('personal_asignado__precio'),
        precio_maximo=Max('personal_asignado__precio'),
    ).prefetch_related(
        'personal_asignado__id_personal',
    ).order_by('nombre_s')
    
    paginator = Paginator(servicios, 4)  # 4 RESULTADOS PAGINA
    page_number = request.GET.get('page') # NUMERO PAGINA
    page_obj = paginator.get_page(page_number)

    return render(request, 'servicios_admin.html', {'servicios': page_obj})


@user_passes_test(es_staff, login_url='login')
def profesionales_admin(request):
    profesionales = Personal.objects.select_related('id_rol').order_by('nombre')
    paginator = Paginator(profesionales, 10)  # 10 RESULTADOS PAGINA
    page_number = request.GET.get('page') # NUMERO PAGINA
    page_obj = paginator.get_page(page_number)
    return render(request, 'profesionales_admin.html', {
        'profesionales': page_obj,
    })


@user_passes_test(es_staff, login_url='login')
def profesional_crear(request):
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'El profesional se creó correctamente y ya puede asignarse a un servicio.',
            )
            return redirect('servicio_crear')
    else:
        form = PersonalForm()
    return render(request, 'personal_form.html', {
        'form': form,
        'titulo': 'Crear profesional',
        'accion': 'Guardar profesional',
    })


@user_passes_test(es_staff, login_url='login')
def rol_crear(request):
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'El cargo o especialidad se creó. Ahora puedes registrar al profesional.',
            )
            return redirect('profesional_crear')
    else:
        form = RolForm()
    return render(request, 'rol_form.html', {'form': form})


@user_passes_test(es_staff, login_url='login')
def servicio_crear(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                servicio = form.save()
                form.save_asignacion(servicio)
            messages.success(request, 'El servicio se creó correctamente.')
            return redirect('servicios_admin')
    else:
        form = ServicioForm()
    return render(request, 'servicio_form.html', {
        'form': form,
        'titulo': 'Agregar servicio',
        'accion': 'Crear servicio',
    })


@user_passes_test(es_staff, login_url='login')
def servicio_editar(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            with transaction.atomic():
                servicio = form.save()
                form.save_asignacion(servicio)
            messages.success(request, 'El servicio se actualizó correctamente.')
            return redirect('servicios_admin')
    else:
        form = ServicioForm(instance=servicio)
    return render(request, 'servicio_form.html', {
        'form': form,
        'titulo': 'Editar servicio',
        'accion': 'Guardar cambios',
        'servicio': servicio,
    })


@user_passes_test(es_staff, login_url='login')
@require_POST
def servicio_eliminar(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    try:
        servicio.delete()
    except ProtectedError:
        messages.error(
            request,
            'No se puede eliminar este servicio porque tiene reservas asociadas. '
            'Primero gestiona o elimina esas reservas.',
        )
    else:
        messages.success(request, 'El servicio se eliminó correctamente.')
    return redirect('servicios_admin')


@user_passes_test(es_staff, login_url='login')
def categoria_servicio_crear(request):
    if request.method == 'POST':
        form = CategoriaServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'La categoría se creó correctamente. Ya puedes asignarla al servicio.',
            )
            return redirect('servicio_crear')
    else:
        form = CategoriaServicioForm()
    return render(request, 'categoria_servicio_form.html', {
        'form': form,
    })


@user_passes_test(es_staff, login_url='login')
def etiquetas_admin(request):
    if request.method == 'POST':
        form = EtiquetaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'La etiqueta se creó correctamente y ya está disponible para las reservas.',
            )
            return redirect('etiquetas_admin')
    else:
        form = EtiquetaForm()
    return render(request, 'etiquetas_admin.html', {
        'form': form,
        'etiquetas': Etiqueta.objects.order_by('nombre'),
    })


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
            nombre = form.cleaned_data['nombre'].strip()
            password = form.cleaned_data['password']
            clientes = Cliente.objects.select_related('usuario').filter(
                nombre_c__iexact=nombre,
                usuario__isnull=False,
            ).order_by('id_cliente')
            user = None
            for cliente in clientes:
                user = authenticate(
                    request,
                    username=cliente.usuario.get_username(),
                    password=password,
                )
                if user is not None and not user.is_staff:
                    break
                user = None
            if user is not None:
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('agendar_cita')
            messages.error(request, 'Nombre o contraseña incorrectos.')
    else:
        form = AutenticacionClienteForm()
    return render(request, 'login_cliente.html', {'form': form})


def registro_cliente(request):
    return redirect('login_cliente')
