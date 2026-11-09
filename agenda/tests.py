from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Cliente,
    CategoriaServicio,
    Etiqueta,
    Personal,
    Reserva,
    Rol,
    Servicio,
    ServicioPersonal,
)
from .validators import PasswordRequirementsValidator


class ServicioAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='administradora',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(self.admin)
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        self.personal = Personal.objects.create(
            nombre='Profesional a cargo',
            credenciales='',
            años_experiencia=3,
            id_rol=rol,
        )

    def test_crear_servicio(self):
        categoria = CategoriaServicio.objects.create(nombre='Cuidado de uñas')
        response = self.client.post(reverse('servicio_crear'), {
            'nombre_s': 'Manicure',
            'descripcion': 'Cuidado de uñas',
            'categoria': categoria.pk,
            'personal': self.personal.pk,
            'duracion_aproximada': 45,
            'precio': '18000',
        })

        self.assertRedirects(response, reverse('servicios_admin'))
        servicio = Servicio.objects.get(nombre_s='Manicure')
        self.assertEqual(servicio.categoria, categoria)
        asignacion = ServicioPersonal.objects.get(id_servicio=servicio)
        self.assertEqual(asignacion.id_personal, self.personal)
        self.assertEqual(asignacion.duracion_aproximada, 45)
        self.assertEqual(asignacion.precio, 18000)

    def test_formulario_creacion_muestra_campos_y_es_espanol(self):
        response = self.client.get(reverse('servicio_crear'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nombre del servicio')
        self.assertContains(response, 'Descripción')
        self.assertContains(response, 'Categoría')
        self.assertContains(response, 'Profesional a cargo')
        self.assertContains(response, 'Duración aproximada (minutos)')
        self.assertContains(response, 'Precio (CLP)')
        self.assertContains(response, 'Usa un nombre breve y fácil de reconocer al reservar.')
        self.assertContains(response, 'Selecciona quién realizará este servicio.')
        self.assertContains(response, '¿No encuentras la categoría? Crear una nueva')
        self.assertContains(response, '¿No aparece el profesional? Crear uno nuevo')

    def test_boton_agregar_servicio(self):
        response = self.client.get(reverse('configuracion_admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("servicio_crear")}"',
        )

    def test_crear_profesional_guarda_datos_y_lo_hace_asignable(self):
        response = self.client.post(reverse('profesional_crear'), {
            'nombre': 'Nueva profesional',
            'credenciales': 'Técnica en uñas',
            'años_experiencia': 4,
            'id_rol': self.personal.id_rol_id,
        })

        self.assertRedirects(response, reverse('servicio_crear'))
        profesional = Personal.objects.get(nombre='Nueva profesional')
        self.assertEqual(profesional.credenciales, 'Técnica en uñas')
        self.assertEqual(profesional.años_experiencia, 4)
        formulario_servicio = self.client.get(reverse('servicio_crear'))
        self.assertContains(formulario_servicio, 'Nueva profesional')

    def test_crear_rol_permite_luego_crear_profesional_con_ese_rol(self):
        response_rol = self.client.post(reverse('rol_crear'), {
            'nombre_rol': 'Cosmetóloga',
            'descripcion': 'Especialista en tratamientos faciales.',
        })

        self.assertRedirects(response_rol, reverse('profesional_crear'))
        rol = Rol.objects.get(nombre_rol='Cosmetóloga')
        response_profesional = self.client.post(reverse('profesional_crear'), {
            'nombre': 'Ana Profesional',
            'credenciales': 'Certificación en cosmetología',
            'años_experiencia': 2,
            'id_rol': rol.pk,
        })

        self.assertRedirects(response_profesional, reverse('servicio_crear'))
        self.assertEqual(
            Personal.objects.get(nombre='Ana Profesional').id_rol,
            rol,
        )

    def test_no_crear_profesional_sin_campos_requeridos(self):
        response = self.client.post(reverse('profesional_crear'), {
            'nombre': '',
            'credenciales': '',
            'años_experiencia': '',
            'id_rol': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingresa el nombre del profesional.')
        self.assertContains(response, 'Selecciona un cargo o especialidad.')
        self.assertFalse(Personal.objects.filter(nombre='').exists())

    def test_lista_de_profesionales_es_visible_en_administracion(self):
        response = self.client.get(reverse('profesionales_admin'))

        self.assertContains(response, 'Profesionales')
        self.assertContains(response, 'Profesional a cargo')
        self.assertContains(response, 'Crear profesional')

    def test_crear_servicio_sin_asignacion_no_lo_guarda(self):
        response = self.client.post(reverse('servicio_crear'), {
            'nombre_s': 'Manicure',
            'descripcion': 'Cuidado de uñas',
            'categoria': '',
            'personal': '',
            'duracion_aproximada': '',
            'precio': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecciona al profesional a cargo.')
        self.assertFalse(Servicio.objects.exists())

    def test_crear_categoria_guarda_nombre_y_descripcion(self):
        response = self.client.post(reverse('categoria_servicio_crear'), {
            'nombre': 'Cuidado facial',
            'descripcion': 'Tratamientos para el rostro.',
        })

        self.assertRedirects(response, reverse('servicio_crear'))
        categoria = CategoriaServicio.objects.get(nombre='Cuidado facial')
        self.assertEqual(categoria.descripcion, 'Tratamientos para el rostro.')
        formulario_servicio = self.client.get(reverse('servicio_crear'))
        self.assertContains(formulario_servicio, 'Cuidado facial')

    def test_descripcion_de_categoria_es_opcional(self):
        response = self.client.post(reverse('categoria_servicio_crear'), {
            'nombre': 'Masajes',
            'descripcion': '',
        })

        self.assertRedirects(response, reverse('servicio_crear'))
        self.assertEqual(CategoriaServicio.objects.get().descripcion, '')

    def test_no_crear_categoria_sin_nombre_o_con_nombre_duplicado(self):
        CategoriaServicio.objects.create(nombre='Cuidado facial')

        response_vacia = self.client.post(reverse('categoria_servicio_crear'), {
            'nombre': ' ',
            'descripcion': '',
        })
        response_duplicada = self.client.post(reverse('categoria_servicio_crear'), {
            'nombre': 'CUIDADO FACIAL',
            'descripcion': '',
        })

        self.assertEqual(response_vacia.status_code, 200)
        self.assertContains(response_vacia, 'Ingresa el nombre de la categoría.')
        self.assertEqual(response_duplicada.status_code, 200)
        self.assertContains(response_duplicada, 'Ya existe una categoría con ese nombre.')
        self.assertEqual(CategoriaServicio.objects.count(), 1)

    def test_no_crear_servicio_sin_nombre_o_descripcion(self):
        response = self.client.post(reverse('servicio_crear'), {
            'nombre_s': '   ',
            'descripcion': '',
            'categoria': '',
            'personal': self.personal.pk,
            'duracion_aproximada': 45,
            'precio': '18000',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingresa el nombre del servicio.')
        self.assertContains(response, 'Ingresa una descripción del servicio.')
        self.assertFalse(Servicio.objects.exists())

    def test_editar_servicio(self):
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Descripción inicial',
        )

        response = self.client.post(reverse('servicio_editar', args=[servicio.pk]), {
            'nombre_s': 'Manicure permanente',
            'descripcion': 'Descripción actualizada',
            'categoria': '',
            'personal': self.personal.pk,
            'duracion_aproximada': 50,
            'precio': '20000',
        })

        self.assertRedirects(response, reverse('servicios_admin'))
        servicio.refresh_from_db()
        self.assertEqual(servicio.nombre_s, 'Manicure permanente')
        self.assertEqual(servicio.descripcion, 'Descripción actualizada')
        asignacion = ServicioPersonal.objects.get(id_servicio=servicio)
        self.assertEqual(asignacion.duracion_aproximada, 50)
        self.assertEqual(asignacion.precio, 20000)

    def test_editar_servicio_asigna_categoria(self):
        categoria = CategoriaServicio.objects.create(nombre='Uñas')
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )

        response = self.client.post(
            reverse('servicio_editar', args=[servicio.pk]),
            {
                'nombre_s': 'Manicure',
                'descripcion': 'Cuidado de uñas',
                'categoria': categoria.pk,
                'personal': self.personal.pk,
                'duracion_aproximada': 45,
                'precio': '18000',
            },
        )

        self.assertRedirects(response, reverse('servicios_admin'))
        servicio.refresh_from_db()
        self.assertEqual(servicio.categoria, categoria)

    def test_crear_etiqueta_la_hace_disponible_para_reservas(self):
        response = self.client.post(reverse('etiquetas_admin'), {
            'nombre': 'Primera visita',
            'color': '#D9C7CC',
        })

        self.assertRedirects(response, reverse('etiquetas_admin'))
        self.assertTrue(Etiqueta.objects.filter(nombre='Primera visita').exists())
        self.assertContains(self.client.get(reverse('etiquetas_admin')), 'Primera visita')

    def test_no_crear_etiqueta_con_nombre_duplicado(self):
        Etiqueta.objects.create(nombre='Primera visita')

        response = self.client.post(reverse('etiquetas_admin'), {
            'nombre': 'primera visita',
            'color': '#D9C7CC',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una etiqueta con ese nombre.')
        self.assertEqual(Etiqueta.objects.count(), 1)

    def test_eliminar_servicio_sin_asignaciones(self):
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )

        response = self.client.post(reverse('servicio_eliminar', args=[servicio.pk]))

        self.assertRedirects(response, reverse('servicios_admin'))
        self.assertFalse(Servicio.objects.filter(pk=servicio.pk).exists())

    def test_eliminar_servicio_elimina_asignacion_profesional(self):
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        personal = Personal.objects.create(
            nombre='Profesional',
            credenciales='',
            años_experiencia=1,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )
        ServicioPersonal.objects.create(
            id_personal=personal,
            id_servicio=servicio,
            duracion_aproximada=30,
            precio=18000,
        )

        response = self.client.post(
            reverse('servicio_eliminar', args=[servicio.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('servicios_admin'))
        self.assertFalse(Servicio.objects.filter(pk=servicio.pk).exists())
        self.assertFalse(ServicioPersonal.objects.filter(id_servicio=servicio).exists())

    def test_no_eliminar_servicio_con_reservas(self):
        cliente = Cliente.objects.create(
            nombre_c='Cliente con reserva',
            telefono='123456',
            correo='reserva@example.com',
        )
        servicio = Servicio.objects.create(
            nombre_s='Servicio reservado',
            descripcion='Servicio con reserva asociada',
        )
        asignacion = ServicioPersonal.objects.create(
            id_personal=self.personal,
            id_servicio=servicio,
            duracion_aproximada=30,
            precio=18000,
        )
        reserva = Reserva.objects.create(
            id_cliente=cliente,
            id_personal=self.personal,
            id_personal_servicio=asignacion,
            fecha='2027-01-15',
            hora='10:00',
        )

        response = self.client.post(
            reverse('servicio_eliminar', args=[servicio.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse('servicios_admin'))
        self.assertTrue(Servicio.objects.filter(pk=servicio.pk).exists())
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())
        self.assertContains(response, 'tiene reservas asociadas')

    def test_listado_muestra_servicios_guardados(self):
        categoria = CategoriaServicio.objects.create(nombre='Uñas')
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
            categoria=categoria,
        )

        response = self.client.get(reverse('servicios_admin'))

        self.assertContains(response, 'Manicure')
        self.assertContains(response, 'Uñas')
        self.assertContains(response, 'Precio pendiente de asignar')

    def test_listado_muestra_precio_asignado_a_profesional(self):
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        personal = Personal.objects.create(
            nombre='Profesional',
            credenciales='',
            años_experiencia=1,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )
        ServicioPersonal.objects.create(
            id_personal=personal,
            id_servicio=servicio,
            duracion_aproximada=30,
            precio=18000,
        )

        response = self.client.get(reverse('servicios_admin'))

        self.assertContains(response, '$18000 CLP')

    def test_eliminar_servicio_solo_acepta_post(self):
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )

        response = self.client.get(
            reverse('servicio_eliminar', args=[servicio.pk]),
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Servicio.objects.filter(pk=servicio.pk).exists())

    def test_gestion_de_servicios_requiere_sesion_de_administrador(self):
        self.client.logout()

        response = self.client.get(reverse('servicio_crear'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("servicio_crear")}',
        )


class ClienteReservaTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username='cliente@example.com',
            email='cliente@example.com',
            password='test-password',
        )
        self.cliente = Cliente.objects.create(
            nombre_c='Cliente de reserva',
            telefono='+56912345678',
            correo='cliente@example.com',
            usuario=user,
        )
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        personal = Personal.objects.create(
            nombre='Profesional',
            credenciales='',
            años_experiencia=2,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )
        self.asignacion = ServicioPersonal.objects.create(
            id_personal=personal,
            id_servicio=servicio,
            duracion_aproximada=45,
            precio=18000,
        )
        self.etiqueta = Etiqueta.objects.create(
            nombre='Primera visita',
            color='#D9C7CC',
        )
        self.client.force_login(user)

    def test_cliente_puede_reservar_servicio_y_guardar_etiquetas(self):
        response = self.client.post(reverse('agendar_cita'), {
            'id_personal_servicio': self.asignacion.pk,
            'fecha': '2027-01-15',
            'hora': '10:00',
            'etiquetas': [self.etiqueta.pk],
        })

        reserva = Reserva.objects.get()
        self.assertRedirects(response, reverse('ver_citas_cliente'))
        self.assertEqual(reserva.id_cliente, self.cliente)
        self.assertEqual(reserva.id_personal_servicio, self.asignacion)
        self.assertEqual(reserva.id_personal, self.asignacion.id_personal)
        self.assertEqual(list(reserva.etiquetas.all()), [self.etiqueta])
        self.assertContains(
            self.client.get(reverse('ver_citas_cliente')),
            'Primera visita',
        )

    def test_cliente_sin_cuenta_se_crea_automaticamente_al_reservar(self):
        self.client.logout()
        response = self.client.post(reverse('agendar_cita'), {
            'id_personal_servicio': self.asignacion.pk,
            'nombre_cliente': 'Cliente generado',
            'telefono_cliente': '+56987654321',
            'correo_cliente': 'generado@example.com',
            'fecha': '2027-01-15',
            'hora': '10:00',
            'etiquetas': [self.etiqueta.pk],
        })

        cliente = Cliente.objects.get(correo='generado@example.com')
        reserva = Reserva.objects.get(id_cliente=cliente)
        self.assertRedirects(response, reverse('ver_citas_cliente'))
        self.assertEqual(cliente.nombre_c, 'Cliente generado')
        self.assertEqual(cliente.telefono, '+56987654321')
        self.assertEqual(reserva.id_personal_servicio, self.asignacion)
        self.assertEqual(list(reserva.etiquetas.all()), [self.etiqueta])

    def test_cliente_no_puede_reservar_horario_ya_ocupado(self):
        fecha_cita = timezone.localdate() + timedelta(days=1)
        Reserva.objects.create(
            id_cliente=self.cliente,
            id_personal_servicio=self.asignacion,
            id_personal=self.asignacion.id_personal,
            fecha=fecha_cita,
            hora='09:00',
        )
        response = self.client.post(reverse('agendar_cita'), {
            'id_personal_servicio': self.asignacion.pk,
            'fecha': fecha_cita.isoformat(),
            'hora': '09:00',
            'etiquetas': [self.etiqueta.pk],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ese profesional ya tiene una cita en ese horario.')
        self.assertEqual(Reserva.objects.count(), 1)

    def test_fecha_pasada_no_permitida(self):
        fecha_pasada = timezone.localdate() - timedelta(days=1)
        response = self.client.post(reverse('agendar_cita'), {
            'id_personal_servicio': self.asignacion.pk,
            'fecha': fecha_pasada.isoformat(),
            'hora': '10:00',
            'etiquetas': [self.etiqueta.pk],
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La fecha de la cita no puede estar en el pasado.')
        self.assertFalse(Reserva.objects.exists())

    def test_formulario_cliente_muestra_profesionales_y_etiquetas_disponibles(self):
        response = self.client.get(reverse('agendar_cita'))

        self.assertContains(response, 'Manicure - Profesional')
        self.assertContains(response, 'Primera visita')
        self.assertContains(response, 'type="checkbox"')
        self.assertContains(response, 'Elige una fecha desde hoy en adelante.')
        self.assertContains(response, 'Puedes seleccionar más de una etiqueta.')
        self.assertContains(
            response,
            f'min="{timezone.localdate().isoformat()}"',
        )


class ReservaCrudTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username='cliente-crud',
            password='test-password',
        )
        self.cliente = Cliente.objects.create(
            nombre_c='Cliente CRUD',
            telefono='+56912345678',
            correo='crud@example.com',
            usuario=user,
        )
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        self.personal = Personal.objects.create(
            nombre='Profesional CRUD',
            credenciales='Certificación',
            años_experiencia=3,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Manicure CRUD',
            descripcion='Servicio para pruebas',
        )
        self.asignacion = ServicioPersonal.objects.create(
            id_personal=self.personal,
            id_servicio=servicio,
            duracion_aproximada=45,
            precio=18000,
        )
        self.etiqueta = Etiqueta.objects.create(nombre='Cliente frecuente')
        self.reserva = Reserva.objects.create(
            id_cliente=self.cliente,
            id_personal=self.personal,
            id_personal_servicio=self.asignacion,
            fecha='2027-01-15',
            hora='10:00',
        )
        self.reserva.etiquetas.add(self.etiqueta)
        self.client.force_login(user)

    def test_detalle_muestra_reserva_y_etiqueta(self):
        response = self.client.get(
            reverse('reserva_detalle', args=[self.reserva.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manicure CRUD')
        self.assertContains(response, 'Profesional CRUD')
        self.assertContains(response, 'Cliente frecuente')

    def test_editar_reserva_guarda_cambios_y_etiquetas(self):
        etiqueta_nueva = Etiqueta.objects.create(nombre='Reagendada')
        response = self.client.post(
            reverse('reserva_editar', args=[self.reserva.pk]),
            {
                'id_personal_servicio': self.asignacion.pk,
                'fecha': '2027-01-16',
                'hora': '10:00',
                'etiquetas': [etiqueta_nueva.pk],
            },
        )

        self.assertRedirects(
            response,
            reverse('reserva_detalle', args=[self.reserva.pk]),
        )
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.fecha.isoformat(), '2027-01-16')
        self.assertEqual(list(self.reserva.etiquetas.all()), [etiqueta_nueva])
        self.assertEqual(self.reserva.id_cliente, self.cliente)

    def test_editar_reserva_rechaza_horario_ocupado(self):
        Reserva.objects.create(
            id_cliente=self.cliente,
            id_personal=self.personal,
            id_personal_servicio=self.asignacion,
            fecha='2027-01-15',
            hora='11:00',
        )
        response = self.client.post(
            reverse('reserva_editar', args=[self.reserva.pk]),
            {
                'id_personal_servicio': self.asignacion.pk,
                'fecha': '2027-01-15',
                'hora': '11:00',
                'etiquetas': [self.etiqueta.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ese profesional ya tiene una cita en ese horario.')
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.hora.strftime('%H:%M'), '10:00')

    def test_eliminar_reserva_pide_confirmacion_y_usa_post(self):
        url = reverse('reserva_eliminar', args=[self.reserva.pk])
        confirmacion = self.client.get(url)

        self.assertEqual(confirmacion.status_code, 200)
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())
        eliminacion = self.client.post(url)
        self.assertRedirects(eliminacion, reverse('ver_citas_cliente'))
        self.assertFalse(Reserva.objects.filter(pk=self.reserva.pk).exists())

    def test_cliente_no_accede_a_reserva_ajena(self):
        otro_usuario = get_user_model().objects.create_user(
            username='otro-cliente',
            password='test-password',
        )
        Cliente.objects.create(
            nombre_c='Otro cliente',
            telefono='+56987654321',
            correo='otro@example.com',
            usuario=otro_usuario,
        )
        self.client.force_login(otro_usuario)

        for ruta in ('reserva_detalle', 'reserva_editar', 'reserva_eliminar'):
            with self.subTest(ruta=ruta):
                response = self.client.get(
                    reverse(ruta, args=[self.reserva.pk]),
                )
                self.assertEqual(response.status_code, 403)


class AdminLiveDataTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='administradora',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(self.admin)
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        self.personal = Personal.objects.create(
            nombre='Profesional real',
            credenciales='Certificación',
            años_experiencia=5,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Servicio real',
            descripcion='Servicio para prueba',
        )
        asignacion = ServicioPersonal.objects.create(
            id_personal=self.personal,
            id_servicio=servicio,
            duracion_aproximada=60,
            precio=25000,
        )
        self.cliente = Cliente.objects.create(
            nombre_c='Cliente real',
            telefono='+56911112222',
            correo='real@example.com',
        )
        self.reserva = Reserva.objects.create(
            id_cliente=self.cliente,
            id_personal=self.personal,
            id_personal_servicio=asignacion,
            fecha=timezone.localdate(),
            hora='09:00',
            estado='confirmado',
        )

    def test_dashboard_muestra_metricas_calculadas_de_la_base(self):
        response = self.client.get(reverse('vista_administracion'))

        self.assertContains(response, 'Citas de hoy')
        self.assertContains(response, 'Clientes registrados')
        self.assertContains(response, 'Profesionales')
        self.assertContains(response, 'Servicios')
        self.assertContains(response, '1')
        self.assertNotContains(response, 'DATOS DE DEMOSTRACIÓN')
        self.assertNotContains(response, '68 %')
        self.assertNotContains(response, '4,5 h')

    def test_admin_agenda_muestra_citas_y_servicios_reales(self):
        response = self.client.get(reverse('agendar_cita_admin'))

        self.assertContains(response, 'Cliente real')
        self.assertContains(response, 'Servicio real')
        self.assertContains(response, 'Profesional real')
        self.assertNotContains(response, 'Registrar una cita manualmente')

    def test_agenda_admin_no_incluye_formulario_para_crear_clientes(self):
        response = self.client.get(reverse('agendar_cita_admin'))

        self.assertNotContains(response, 'Registrar una cita manualmente')
        self.assertNotContains(response, 'Nombre del cliente')
        self.assertContains(response, 'Cliente real')

    def test_clientes_usa_mismo_formato_de_tarjetas_que_profesionales(self):
        response = self.client.get(reverse('clientes_admin'))

        self.assertContains(response, 'class="services-grid"')
        self.assertContains(response, 'class="admin-card service-item"')
        self.assertContains(response, 'Cliente real')
        self.assertContains(response, '1 reserva')

    def test_busqueda_de_clientes_acepta_telefono(self):
        response = self.client.get(
            reverse('clientes_admin'),
            {'q': '11112222'},
        )

        self.assertContains(response, 'Cliente real')

    def test_dashboard_actualiza_contadores_al_guardar_cancelacion(self):
        self.reserva.estado = 'cancelado'
        self.reserva.save(update_fields=['estado'])

        response = self.client.get(reverse('vista_administracion'))

        self.assertEqual(response.context['canceladas'], 1)
        self.assertEqual(response.context['tasa_cancelacion'], 100.0)
        self.assertEqual(response.context['citas_hoy'], 1)


class AdminLoginRedirectTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='administradora',
            password='test-password',
            is_staff=True,
        )

    def test_login_admin_redirige_directamente_a_la_agenda(self):
        response = self.client.post(reverse('login'), {
            'nombre': 'administradora',
            'password': 'test-password',
        })

        self.assertRedirects(response, reverse('agendar_cita_admin'))

    def test_enlace_de_administracion_abre_la_agenda(self):
        response = self.client.get(reverse('home'))

        self.assertContains(
            response,
            f'href="{reverse("acceso")}"',
        )

    def test_portada_publica_muestra_catalogo_testimonios_demostrativos_y_sin_menu(self):
        categoria = CategoriaServicio.objects.create(nombre='Uñas')
        Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado y esmaltado de uñas.',
            categoria=categoria,
        )

        response = self.client.get(reverse('home'))
        header = response.content.partition(b'</header>')[0].decode('utf-8')

        self.assertContains(response, 'Un momento para ti, una belleza que se siente.')
        self.assertContains(response, 'Manicure')
        self.assertContains(response, 'Cuidado y esmaltado de uñas.')
        self.assertContains(response, 'Uñas')
        self.assertContains(response, 'Testimonios de ejemplo')
        self.assertIn(b'class="landing-topbar"', response.content)
        self.assertLess(
            response.content.index(b'class="landing-topbar"'),
            response.content.index(b'class="landing-hero"'),
        )
        self.assertNotIn(b'Iniciar sesi\xc3\xb3n</a></footer>', response.content)
        self.assertNotIn('Agendar cita', header)
        self.assertNotIn('Ver citas', header)
        self.assertNotIn('Crear cuenta', header)
        self.assertContains(response, '¿Quieres agendar una cita?')
        self.assertContains(response, f'href="{reverse("agendar_cita")}"')

    def test_pagina_de_acceso_ofrece_login_admin_cliente_y_registro(self):
        response = self.client.get(reverse('acceso'))

        self.assertContains(response, '¿Eres administrador?')
        self.assertContains(response, '¿Eres cliente?')
        self.assertContains(response, reverse('login'))
        self.assertContains(response, reverse('login_cliente'))
        self.assertContains(response, 'Agenda una cita y tu cuenta se creará automáticamente.')
        self.assertNotContains(response, 'Crea tu cuenta')

    def test_dashboard_usa_navegacion_admin_compartida(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('vista_administracion'))

        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Volver al panel de administración')
        self.assertContains(response, 'admin-navbar')
        self.assertContains(response, 'class="is-active" href="/vista_administracion/"')
        self.assertContains(response, 'Agenda')
        self.assertNotContains(response, 'Agendar cita')
        self.assertNotContains(response, 'Ver citas')
        self.assertNotContains(response, 'Iniciar Sesión')
        self.assertNotContains(response, 'Login Administración')

    def test_navegacion_admin_no_muestra_accesos_de_cliente(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('home'))
        header = response.content.partition(b'</header>')[0].decode('utf-8')

        self.assertNotIn('Login Administración', header)
        self.assertNotIn('Agendar cita', header)
        self.assertNotIn('Ver citas', header)
        self.assertNotIn('Iniciar Sesión', header)
        self.assertNotIn('Vista cliente', header)
        self.assertIn('Cerrar sesión', header)


class ClienteAccountTests(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre_rol='Estilista', descripcion='')
        personal = Personal.objects.create(
            nombre='Profesional',
            credenciales='Certificación',
            años_experiencia=3,
            id_rol=rol,
        )
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )
        self.asignacion = ServicioPersonal.objects.create(
            id_personal=personal,
            id_servicio=servicio,
            duracion_aproximada=45,
            precio=18000,
        )

    def reservar(self, **overrides):
        data = {
            'id_personal_servicio': self.asignacion.pk,
            'nombre_cliente': 'Cliente de prueba',
            'telefono_cliente': '+56912345678',
            'correo_cliente': 'cliente@example.com',
            'fecha': '2027-01-15',
            'hora': '10:00',
        }
        data.update(overrides)
        return self.client.post(reverse('agendar_cita'), data)

    def test_reserva_crea_cuenta_cliente_y_deja_sesion_iniciada(self):
        response = self.reservar()

        cliente = Cliente.objects.get(correo='cliente@example.com')
        user = cliente.usuario
        self.assertRedirects(response, reverse('ver_citas_cliente'))
        self.assertEqual(cliente.telefono, '+56912345678')
        self.assertTrue(user.check_password('+56912345678'))
        self.assertEqual(
            str(self.client.session['_auth_user_id']),
            str(user.pk),
        )
        self.assertEqual(Reserva.objects.get().id_cliente, cliente)

    def test_cliente_puede_iniciar_sesion_con_nombre_y_telefono_como_clave(self):
        self.reservar()
        self.client.logout()

        response = self.client.post(reverse('login_cliente'), {
            'nombre': 'Cliente de prueba',
            'password': '+56912345678',
        })

        self.assertRedirects(response, reverse('agendar_cita'))
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_login_con_nombre_repetido_valida_el_telefono_de_la_cuenta(self):
        self.reservar()
        self.client.logout()
        usuario = get_user_model().objects.create_user(
            username='cliente-duplicado',
            password='223344',
        )
        Cliente.objects.create(
            nombre_c='Cliente de prueba',
            telefono='223344',
            correo='duplicado@example.com',
            usuario=usuario,
        )

        response = self.client.post(reverse('login_cliente'), {
            'nombre': 'Cliente de prueba',
            'password': '223344',
        })

        self.assertRedirects(response, reverse('agendar_cita'))
        self.assertEqual(
            str(self.client.session['_auth_user_id']),
            str(usuario.pk),
        )

    def test_reserva_reutiliza_perfil_existente_y_lo_vincula_a_cuenta(self):
        cliente = Cliente.objects.create(
            nombre_c='Nombre anterior',
            telefono='111',
            correo='cliente@example.com',
        )

        response = self.reservar()

        cliente.refresh_from_db()
        self.assertRedirects(response, reverse('ver_citas_cliente'))
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(cliente.nombre_c, 'Cliente de prueba')
        self.assertEqual(cliente.telefono, '+56912345678')
        self.assertTrue(cliente.usuario.check_password('+56912345678'))

    def test_login_cliente_muestra_errores_en_espanol(self):
        response = self.client.post(reverse('login_cliente'), {
            'nombre': '',
            'password': '',
        })

        self.assertContains(response, 'Ingresa tu nombre.')
        self.assertContains(response, 'Ingresa tu teléfono como contraseña.')

    def test_login_cliente_rechaza_contrasena_incorrecta(self):
        self.reservar()
        self.client.logout()

        response = self.client.post(reverse('login_cliente'), {
            'nombre': 'Cliente de prueba',
            'password': 'incorrecta',
        })

        self.assertContains(response, 'Nombre o contraseña incorrectos.')

    def test_crear_cuenta_manual_redirige_al_login(self):
        response = self.client.get(reverse('registro_cliente'))

        self.assertRedirects(response, reverse('login_cliente'))
        self.assertFalse(Cliente.objects.exists())

    def test_landing_cliente_muestra_saludo_y_solo_requiere_sesion_cliente(self):
        response_reserva = self.reservar()
        self.assertRedirects(response_reserva, reverse('ver_citas_cliente'))

        response = self.client.get(reverse('landing_cliente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hola, Cliente de prueba')
        self.assertContains(response, 'Próximas citas')

    def test_landing_cliente_redirige_a_login_si_no_hay_sesion(self):
        response = self.client.get(reverse('landing_cliente'))

        self.assertRedirects(
            response,
            f'{reverse("login_cliente")}?next={reverse("landing_cliente")}',
        )


class PasswordRequirementsTests(TestCase):
    def setUp(self):
        self.validator = PasswordRequirementsValidator()

    def test_contrasena_con_todos_los_requisitos_es_valida(self):
        self.validator.validate('Clave!23')

    def test_contrasena_corta_muestra_error_en_espanol(self):
        with self.assertRaises(ValidationError) as error:
            self.validator.validate('Ab!1234')

        self.assertIn('al menos 8 caracteres', str(error.exception))

    def test_contrasena_debe_tener_mayuscula_numero_y_especial(self):
        cases = [
            ('clave!23', 'una mayúscula'),
            ('Clave!ab', 'un número'),
            ('Clave123', 'un carácter especial'),
        ]
        for password, expected_message in cases:
            with self.subTest(password=password):
                with self.assertRaises(ValidationError) as error:
                    self.validator.validate(password)
                self.assertIn(expected_message, str(error.exception))
