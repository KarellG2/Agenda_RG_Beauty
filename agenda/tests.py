from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CategoriaServicio, Personal, Rol, Servicio, ServicioPersonal


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
