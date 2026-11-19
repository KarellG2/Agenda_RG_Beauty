from datetime import date, datetime, timedelta
from uuid import uuid4

from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect
from .forms import *
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Max, Min, Q
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from .models import *
from .utility import registrar_accion
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from functools import wraps
from django.contrib.auth.views import redirect_to_login

def es_admin(user):
    return user.is_authenticated and user.is_staff

def es_profesional(user):
    return (
        user.is_authenticated
        and not user.is_staff
        and Personal.objects.filter(usuario=user).exists()
    )

def es_staff(user):
    return (
        user.is_authenticated
        and (
            user.is_staff
            or Personal.objects.filter(usuario=user).exists()
        )
    )

def es_personal(user):
    return es_admin(user) or es_profesional(user)

def es_cliente(user):
    return (
        user.is_authenticated
        and not user.is_staff
        and Cliente.objects.filter(usuario=user).exists()
    )

# IA
def es_usuario_reservas(user):
    # Usuarios que pueden ver la colección general de reservas: administradores y clientes.
    return es_admin(user) or es_cliente(user)

def es_usuario_reserva(user):
    # Usuarios autorizados para entrar al detalle o edición de una reserva individual.
    return es_personal(user) or es_cliente(user)

def requiere_rol(test_func, login_url='login'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(),login_url=login_url)
            if not test_func(request.user):
                return render(request, 'acceso_denegado.html', status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Create your views here.
def home(request):
    if es_cliente(request.user):
        return redirect('landing_cliente')

    servicios = Servicio.objects.select_related('categoria').annotate(
        precio_minimo=Min('personal_asignado__precio'),
        precio_maximo=Max('personal_asignado__precio'),
    ).order_by('nombre_s')
    return render(request, 'landing_publica.html', {'servicios': servicios})

@never_cache
@user_passes_test(es_cliente, login_url='login_cliente')
def landing_cliente(request):
    cliente = get_object_or_404(Cliente, usuario=request.user)
    citas = Reserva.objects.filter(
            id_cliente=cliente
        ).select_related(
            'id_personal',
            'id_personal_servicio__id_servicio',
            'id_personal_servicio__id_personal'
        ).prefetch_related('etiquetas').order_by('fecha', 'hora')
        
    return render(
        request,
        'home_cliente.html',
        {'citas': citas, 'cliente': cliente, 'landing_cliente': True},
    )


def dashboard(request):
    return render(request, 'dashboard.html')

@never_cache
@user_passes_test(es_cliente, login_url='login_cliente')
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
    ).prefetch_related('etiquetas').order_by('fecha', 'hora') #<- prefetch optimizar
    
    q = request.GET.get('q', '').strip()
    if q:
        citas = citas.filter(
            # filtro servicio o profesional
            Q(id_personal_servicio__id_servicio__nombre_s__icontains=q) |
            Q(id_personal__nombre__icontains=q)
        ).distinct()
        
    servicio_id = request.GET.get('servicio', '')
    if servicio_id.isdigit():
        citas = citas.filter(
            id_personal_servicio__id_servicio_id=int(servicio_id)
        )
    
    paginator = Paginator(citas, 5)  # 5 citas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    servicios = Servicio.objects.order_by('nombre_s')
    
    return render(request, 
                'ver_citas_cliente.html', {
                'citas': page_obj,
                'servicios': servicios,
                'servicio_id': servicio_id,
                'q': q,
            })


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
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            'id_cliente',
            'id_personal',
            'id_personal_servicio__id_servicio',
            'id_personal_servicio__id_personal',
        ).prefetch_related('etiquetas'),
        pk=pk,
    )

    if request.user.is_staff:
        return reserva, None

    if es_profesional(request.user):
        personal = Personal.objects.filter(usuario=request.user).first()
        if personal is None or reserva.id_personal_id != personal.pk:
            return None, render(request, 'acceso_denegado.html', status=403)
        return reserva, None

    cliente = _cliente_actual(request)
    if cliente is None:
        return None, redirect('login_cliente')
    if reserva.id_cliente_id != cliente.pk:
        return None, render(request, 'acceso_denegado.html', status=403)
    return reserva, None

@never_cache
@requiere_rol(es_usuario_reserva, login_url='login_cliente')
def reserva_detalle(request, pk):
    reserva, respuesta = _reserva_permitida(request, pk)
    if respuesta:
        return respuesta
    return render(request, 'reserva_detalle.html', {'reserva': reserva})

@never_cache
@requiere_rol(es_usuario_reserva, login_url='login_cliente')
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
            if request.user.is_staff:
                registrar_accion(
                    request.user,
                    f'Se actualizó la reserva #{reserva.pk}.',
                )
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

@never_cache
@requiere_rol(es_usuario_reserva, login_url='login_cliente')
def reserva_eliminar(request, pk):
    if (
        request.user.is_authenticated
        and not request.user.is_staff
        and Personal.objects.filter(usuario=request.user).exists()
    ):
        return render(request, 'acceso_denegado.html', status=403)

    reserva, respuesta = _reserva_permitida(request, pk)
    if respuesta:
        return respuesta
    if request.method == 'GET':
        return render(request, 'reserva_confirmar_eliminar.html', {
            'reserva': reserva,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    reserva_id = reserva.pk
    reserva.delete()
    if request.user.is_staff:
        registrar_accion(
            request.user,
            f'Se eliminó la reserva #{reserva_id}.',
        )
    messages.success(request, 'La reserva se eliminó correctamente.')
    return redirect(
        'agendar_cita_admin' if request.user.is_staff else 'ver_citas_cliente'
    )

@never_cache
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

            if request.user.is_staff:
                registrar_accion(
                    request.user,
                    f'Se creó la reserva #{reserva.pk}.',
                )
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

@never_cache
@user_passes_test(es_staff, login_url='login')
def ver_citas(request):
    return render(request, 'ver_citas_cliente.html')

@never_cache
@requiere_rol(es_personal)
def vista_administracion(request):
    hoy = timezone.localdate()
    reservas = Reserva.objects.all()
    personal_actual = None
    if es_profesional(request.user):
        personal_actual = get_object_or_404(Personal, usuario=request.user)
        reservas = reservas.filter(id_personal=personal_actual)

    citas_hoy = reservas.filter(fecha=hoy)
    total_reservas = reservas.count()
    canceladas = reservas.filter(estado='cancelado').count()
    tasa_cancelacion = (
        round(canceladas * 100 / total_reservas, 1)
        if total_reservas else 0
    )
    return render(request, 'vista_administracion.html', {
        'citas_hoy': citas_hoy.count(),
        'pendientes': reservas.filter(estado='pendiente').count(),
        'confirmadas': reservas.filter(estado='confirmado').count(),
        'canceladas': canceladas,
        'total_reservas': total_reservas,
        'clientes_registrados': (
            reservas.values('id_cliente').distinct().count()
            if personal_actual
            else Cliente.objects.count()
        ),
        'profesionales_registrados': (
            1 if personal_actual
            else Personal.objects.count()
        ),
        'servicios_registrados': (
            Servicio.objects.filter(
                personal_asignado__id_personal=personal_actual
            ).distinct().count()
            if personal_actual
            else Servicio.objects.count()
        ),
        'tasa_cancelacion': tasa_cancelacion,
    })

@never_cache
@requiere_rol(es_personal)
def agendar_cita_admin(request):
    hoy = timezone.localdate()
    fecha_param = request.GET.get('fecha')
    personal_actual = None
    if es_profesional(request.user):
        personal_actual = get_object_or_404(Personal, usuario=request.user)

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

    if personal_actual:
        query = query.filter(id_personal=personal_actual)

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

    asignaciones_query = ServicioPersonal.objects.all()
    if personal_actual:
        asignaciones_query = asignaciones_query.filter(id_personal = personal_actual)
    asignaciones = list(asignaciones_query)
    dias = []
    for offset in range((fin_periodo - inicio_periodo).days + 1):
        dia = inicio_periodo + timedelta(days=offset)
        reservas_dia_query = Reserva.objects.filter(
            fecha=dia
            ).exclude(
                estado='cancelado'
                ).select_related(
                    'id_personal_servicio'
                    )
        if personal_actual:
            reservas_dia_query = reservas_dia_query.filter(id_personal=personal_actual)
        reservas_dia = list(
            reservas_dia_query
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
    servicios = Servicio.objects.order_by('nombre_s')

    if personal_actual:
        servicios = servicios.filter(
            personal_asignado__id_personal=personal_actual
        ).distinct()

    return render(request, 'agendar_cita_admin.html', {
        'reservas': query.order_by('fecha', 'hora', 'id_personal__nombre'),
        'servicios': servicios,
        'disponibilidad': dias,
        'fecha_seleccionada': fecha_seleccionada,
        'vista': vista,
        'cliente_busqueda': cliente_busqueda,
        'servicio_filtro': servicio_filtro,
        'estado_filtro': estado_filtro,
        'estados': estados,
    })

@never_cache
@requiere_rol(es_admin)
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

@never_cache
@requiere_rol(es_admin)
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

@never_cache
@requiere_rol(es_admin)
def profesionales_admin(request):
    profesionales = Personal.objects.select_related('id_rol').order_by('nombre')
    paginator = Paginator(profesionales, 10)  # 10 RESULTADOS PAGINA
    page_number = request.GET.get('page') # NUMERO PAGINA
    page_obj = paginator.get_page(page_number)
    return render(request, 'profesionales_admin.html', {
        'profesionales': page_obj,
    })

@never_cache
@requiere_rol(es_admin)
def profesional_crear(request):

    puede_otorgar_accesos = request.user.is_superuser

    if request.method == 'POST':
        form = PersonalForm(
            request.POST,
            puede_otorgar_accesos=puede_otorgar_accesos,
        )
        if form.is_valid():
            tiene_acceso_admin = (
                puede_otorgar_accesos
                and
                form.cleaned_data.get(
                    'puede_administrar',
                    False)
            )

            with transaction.atomic():
                personal = form.save(commit=False)
                usuario = get_user_model()(
                    username=personal.nombre,
                    is_staff=tiene_acceso_admin,
                )
                usuario.set_password(form.cleaned_data['password'])
                usuario.save()

                personal.usuario = usuario
                personal.save()

            registrar_accion(
                request.user,
                f'Se creó el profesional "{personal.nombre}".',
            )
            messages.success(
                request,
                'El profesional se creó correctamente y ya puede asignarse a un servicio.',
            )
            return redirect('servicio_crear')
    else:
        form = PersonalForm(
            puede_otorgar_accesos=puede_otorgar_accesos
        )
    return render(request, 'personal_form.html', {
        'form': form,
        'titulo': 'Crear profesional',
        'accion': 'Guardar profesional',
    })

@never_cache
@requiere_rol(es_admin)
def profesionales_editar(request, pk):
    profesional = get_object_or_404(Personal, pk=pk)
    if request.method == 'POST':
        form = PersonalUpdateForm(request.POST, instance= profesional)
        if form.is_valid():
            with transaction.atomic():
                profesional = form.save()
            registrar_accion(
                request.user,
                f'Se actualizó el profesional "{profesional.nombre}".',
            )
            messages.success(request, 'El profesional se actualizó correctamente.')
            return redirect('profesionales_admin')
    else:
        form = PersonalUpdateForm(instance = profesional)
    return render(request, 'personal_form.html', {
        'form': form,
        'titulo': 'Editar profesional',
        'accion': 'Guardar cambios',
    })

@never_cache
@requiere_rol(es_admin)
def profesional_eliminar(request, pk):
    profesional = get_object_or_404(Personal, pk=pk)
    if request.method == 'GET':
        return render(request, 'forms/profesionales_eliminar.html', {
            'profesional': profesional,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    if Reserva.objects.filter(id_personal=profesional).exists():
        messages.error(
            request,
            'No se puede eliminar este profesional porque tiene reservas asociadas. '
            'Primero gestiona o elimina esas reservas.',
        )
        return redirect('profesionales_admin')

    nombre_profesional = profesional.nombre
    with transaction.atomic():
        ServicioPersonal.objects.filter(id_personal=profesional).delete()
        RegistrosAuditoria.objects.filter(
            id_personal=profesional,
        ).update(id_personal=None)
        profesional.delete()

    messages.success(request, 'El profesional se eliminó correctamente.')
    registrar_accion(
        request.user,
        f'Se eliminó el profesional "{nombre_profesional}".',
    )
    return redirect('profesionales_admin')

@never_cache
@requiere_rol(es_admin)
def rol_crear(request):
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            rol = form.save()
            registrar_accion(
                request.user,
                f'Se creó el rol "{rol.nombre_rol}".',
            )
            messages.success(
                request,
                'El cargo o especialidad se creó. Ahora puedes registrar al profesional.',
            )
            return redirect('profesional_crear')
    else:
        form = RolForm()
    return render(request, 'rol_form.html', {'form': form})

@never_cache
@requiere_rol(es_admin)
def servicio_crear(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                servicio = form.save()
                form.save_asignacion(servicio)
            registrar_accion(
                request.user,
                f'Se creó el servicio "{servicio.nombre_s}".',
            )
            messages.success(request, 'El servicio se creó correctamente.')
            return redirect('servicios_admin')
    else:
        form = ServicioForm()
    return render(request, 'servicio_form.html', {
        'form': form,
        'titulo': 'Agregar servicio',
        'accion': 'Crear servicio',
    })

@never_cache
@requiere_rol(es_admin)
def servicio_editar(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            with transaction.atomic():
                servicio = form.save()
                form.save_asignacion(servicio)
            registrar_accion(
                request.user,
                f'Se actualizó el servicio "{servicio.nombre_s}".',
            )
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

@never_cache
@requiere_rol(es_admin)
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteUpdateForm(request.POST, instance=cliente)
        if form.is_valid():
            with transaction.atomic():
                cliente = form.save()
            registrar_accion(
                request.user,
                f'Se actualizó el cliente "{cliente.nombre_c}".',
            )
            messages.success(request, 'El cliente se actualizó correctamente.')
            return redirect('clientes_admin')
    else:
        form = ClienteUpdateForm(instance=cliente)
    return render(request, 'forms/editar_clientes.html', {'form': form, 'cliente': cliente})

@never_cache
@requiere_rol(es_admin)
def servicio_eliminar(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method == 'GET':
        return render(request, 'forms/servicio_eliminar.html', {
            'servicio': servicio,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])
    try:
        servicio.delete()
    except ProtectedError:
        messages.error(
            request,
            'No se puede eliminar este servicio porque tiene reservas asociadas. '
            'Primero gestiona o elimina esas reservas.',
        )
    else:
        registrar_accion(
            request.user,
            f'Se eliminó el servicio "{servicio.nombre_s}".',
        )
        messages.success(request, 'El servicio se eliminó correctamente.')
    return redirect('servicios_admin')


@never_cache
@requiere_rol(es_admin)
def categoria_servicio_crear(request):
    if request.method == 'POST':
        form = CategoriaServicioForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            registrar_accion(
                request.user,
                f'Se creó la categoría "{categoria.nombre}".',
            )
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

@never_cache
@requiere_rol(es_admin)
def etiquetas_admin(request):
    if request.method == 'POST':
        form = EtiquetaForm(request.POST)
        if form.is_valid():
            etiqueta = form.save()
            registrar_accion(
                request.user,
                f'Se creó la etiqueta "{etiqueta.nombre}".',
            )
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

@never_cache
@requiere_rol(es_admin)
def etiqueta_editar(request, pk):
    etiqueta = get_object_or_404(Etiqueta, pk=pk)
    if request.method == 'POST':
        form = EtiquetaForm(request.POST, instance=etiqueta)
        if form.is_valid():
            with transaction.atomic():
                etiqueta = form.save()
            registrar_accion(
                request.user,
                f'Se actualizó la etiqueta "{etiqueta.nombre}".',
            )
            messages.success(request, 'La etiqueta se actualizó correctamente.')
            return redirect('etiquetas_admin')
    else:
        form = EtiquetaForm(instance=etiqueta)
    return render(request, 'etiqueta/etiquetas_editar.html', {'form': form, 'etiqueta': etiqueta})

@never_cache
@requiere_rol(es_admin)
def etiqueta_eliminar(request, pk):
    etiqueta = get_object_or_404(Etiqueta, pk=pk)
    if request.method == 'GET':
        return render(request, 'etiqueta/etiqueta_confirmar_eliminar.html', {
            'etiqueta': etiqueta,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    nombre_etiqueta = etiqueta.nombre
    etiqueta.delete()
    registrar_accion(
        request.user,
        f'Se eliminó la etiqueta "{nombre_etiqueta}".',
    )

    messages.success(request, 'La etiqueta se eliminó correctamente.')
    return redirect('etiquetas_admin')


@never_cache
@requiere_rol(es_admin)
def notificaciones_admin(request):
    notificacion = Notificacion.objects.select_related(
        'id_cliente',
        'id_reserva__id_personal_servicio__id_servicio',
    ).order_by('-fecha')
    paginator = Paginator(notificacion, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'notificaciones_admin.html', {
        'notificaciones': page_obj,
    })

@never_cache
@requiere_rol(es_admin)
def auditoria_admin(request):
    auditoria = RegistrosAuditoria.objects.order_by('-fecha').select_related('id_personal')
    paginator = Paginator(auditoria, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'auditoria_admin.html', {
        'registros_auditoria': page_obj,
    })


@never_cache
@requiere_rol(es_admin)
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
        if request.user.is_staff:
            return redirect('agendar_cita_admin')
        if Personal.objects.filter(usuario=request.user).exists():
            return redirect('agendar_cita_admin')
        return redirect('home')

    if request.method == 'POST':
        form = AutenticacionForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            password = form.cleaned_data['password']
            user = authenticate(request, username=nombre, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('agendar_cita_admin')
            if user is not None and Personal.objects.filter(usuario=user).exists():
                login(request, user)
                messages.success(request, 'Sesión iniciada correctamente.')
                return redirect('agendar_cita_admin')
            messages.error(
                request,
                'Nombre de usuario o contraseña incorrectos.',
            )
    else:
        form = AutenticacionForm()
    return render(request, 'login_admin.html', {'form': form})

def verificar_codigo(request):
    return render(request, 'forms/codigo_verificacion.html')

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

@never_cache
@user_passes_test(es_cliente, login_url='login_cliente')
def mi_cuenta(request):
    cliente = get_object_or_404(Cliente, usuario=request.user)
    if request.method == 'POST':
        telefono_anterior = cliente.telefono
        form = ClienteUpdateForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente_actualizado = form.save(commit=False)
            telefono_nuevo = cliente_actualizado.telefono.strip()
            cliente_actualizado.telefono = telefono_nuevo
            cliente_actualizado.save()

            if cliente.usuario:
                cliente.usuario.set_password(telefono_nuevo)
                cliente.usuario.save(update_fields=['password'])
                update_session_auth_hash(request, cliente.usuario)

            if telefono_nuevo != telefono_anterior:
                messages.success(
                    request,
                    'Datos actualizados correctamente. Tu teléfono y contraseña de acceso se han actualizado.',
                )
            else:
                messages.success(request, 'Datos actualizados correctamente.')
            return redirect('mi_cuenta')
    else:
        form = ClienteUpdateForm(instance=cliente)
    return render(request, 'mi_cuenta.html', {'form': form, 'cliente': cliente})

@never_cache
@user_passes_test(es_cliente, login_url='login_cliente')
def eliminar_cuenta_cliente(request):
    cliente = get_object_or_404(Cliente, usuario=request.user)
    if request.method == 'GET':
        return render(request, 'forms/eliminar_cuenta_cliente.html', {
            'cliente': cliente,
        })
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])
    if Reserva.objects.filter(id_cliente=cliente).exists():
        messages.error(
            request,
            'No se puede eliminar esta cuenta porque tiene reservas asociadas. '
            'Primero gestiona o elimina esas reservas.',
        )
        return redirect('mi_cuenta')
    
    with transaction.atomic():
        if cliente.usuario:
            cliente.usuario.delete()
        cliente.delete()
    messages.success(request, 'La cuenta se eliminó correctamente.')
    return redirect('home')
