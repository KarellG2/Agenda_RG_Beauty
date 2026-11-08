from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Cliente,
    CategoriaServicio,
    Personal,
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

    def test_crear_servicio(self):
        response = self.client.post(reverse('servicio_crear'), {
            'nombre_s': 'Manicure',
            'descripcion': 'Cuidado de uñas',
            'categoria': '',
        })

        self.assertRedirects(response, reverse('servicios_admin'))
        self.assertTrue(Servicio.objects.filter(nombre_s='Manicure').exists())

    def test_editar_servicio(self):
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Descripción inicial',
        )

        response = self.client.post(reverse('servicio_editar', args=[servicio.pk]), {
            'nombre_s': 'Manicure permanente',
            'descripcion': 'Descripción actualizada',
            'categoria': '',
        })

        self.assertRedirects(response, reverse('servicios_admin'))
        servicio.refresh_from_db()
        self.assertEqual(servicio.nombre_s, 'Manicure permanente')
        self.assertEqual(servicio.descripcion, 'Descripción actualizada')

    def test_eliminar_servicio_sin_asignaciones(self):
        servicio = Servicio.objects.create(
            nombre_s='Manicure',
            descripcion='Cuidado de uñas',
        )

        response = self.client.post(reverse('servicio_eliminar', args=[servicio.pk]))

        self.assertRedirects(response, reverse('servicios_admin'))
        self.assertFalse(Servicio.objects.filter(pk=servicio.pk).exists())

    def test_no_eliminar_servicio_asignado_a_profesional(self):
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
        self.assertTrue(Servicio.objects.filter(pk=servicio.pk).exists())
        self.assertContains(response, 'No se puede eliminar este servicio')

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

    def test_pagina_de_acceso_ofrece_login_admin_cliente_y_registro(self):
        response = self.client.get(reverse('acceso'))

        self.assertContains(response, '¿Eres administrador?')
        self.assertContains(response, '¿Eres cliente?')
        self.assertContains(response, reverse('login'))
        self.assertContains(response, reverse('login_cliente'))
        self.assertContains(response, reverse('registro_cliente'))

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
    registration_data = {
        'nombre': 'Cliente de prueba',
        'telefono': '+56912345678',
        'correo': 'cliente@example.com',
        'password1': 'Cliente-segura-2026!',
        'password2': 'Cliente-segura-2026!',
    }

    def test_registro_guarda_cuenta_y_cliente_vinculados(self):
        response = self.client.post(
            reverse('registro_cliente'),
            self.registration_data,
        )

        self.assertRedirects(response, reverse('agendar_cita'))
        user = get_user_model().objects.get(username='cliente@example.com')
        cliente = Cliente.objects.get(correo='cliente@example.com')
        self.assertEqual(cliente.usuario, user)
        self.assertTrue(user.check_password(self.registration_data['password1']))
        self.assertNotEqual(user.password, self.registration_data['password1'])
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))
        self.assertEqual(response.url, reverse('agendar_cita'))

    def test_correo_duplicado_no_crea_otra_cuenta(self):
        self.client.post(reverse('registro_cliente'), self.registration_data)
        self.client.logout()

        response = self.client.post(
            reverse('registro_cliente'),
            self.registration_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta con este correo.')
        self.assertEqual(Cliente.objects.filter(correo='cliente@example.com').count(), 1)

    def test_registro_vincula_perfil_preexistente_con_datos_coincidentes(self):
        cliente_existente = Cliente.objects.create(
            nombre_c=self.registration_data['nombre'],
            telefono=self.registration_data['telefono'],
            correo=self.registration_data['correo'],
        )

        response = self.client.post(
            reverse('registro_cliente'),
            self.registration_data,
        )

        self.assertRedirects(response, reverse('agendar_cita'))
        cliente_existente.refresh_from_db()
        self.assertIsNotNone(cliente_existente.usuario_id)
        self.assertEqual(Cliente.objects.filter(correo='cliente@example.com').count(), 1)

    def test_cliente_registrado_aparece_en_listado_admin(self):
        self.client.post(reverse('registro_cliente'), self.registration_data)
        admin = get_user_model().objects.create_user(
            username='administradora',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('clientes_admin'))

        self.assertContains(response, 'Cliente de prueba')
        self.assertContains(response, 'cliente@example.com')
        self.assertContains(response, 'Cuenta registrada')

    def test_login_cliente_usa_correo_y_contrasena(self):
        self.client.post(reverse('registro_cliente'), self.registration_data)
        self.client.logout()

        response = self.client.post(reverse('login_cliente'), {
            'correo': self.registration_data['correo'],
            'password': self.registration_data['password1'],
        })

        self.assertRedirects(response, reverse('agendar_cita'))
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_login_cliente_muestra_errores_en_espanol(self):
        response = self.client.post(reverse('login_cliente'), {
            'correo': 'no-es-un-correo',
            'password': '',
        })

        self.assertContains(response, 'Ingresa un correo electrónico válido.')
        self.assertContains(response, 'Ingresa tu contraseña.')

    def test_login_cliente_con_credenciales_incorrectas_muestra_error_en_espanol(self):
        self.client.post(reverse('registro_cliente'), self.registration_data)
        self.client.logout()

        response = self.client.post(reverse('login_cliente'), {
            'correo': self.registration_data['correo'],
            'password': 'incorrecta',
        })

        self.assertContains(response, 'Nombre de usuario o contraseña incorrectos.')

    def test_landing_cliente_muestra_saludo_y_solo_requiere_sesion_cliente(self):
        self.client.post(reverse('registro_cliente'), self.registration_data)

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
