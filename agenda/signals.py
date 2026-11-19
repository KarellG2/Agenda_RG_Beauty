from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Personal, Rol


@receiver(post_save, sender=get_user_model())
def crear_personal_para_superusuario(sender, instance, created, **kwargs):
    if not instance.is_superuser:
        return

    if Personal.objects.filter(usuario=instance).exists():
        return

    rol, _ = Rol.objects.get_or_create(
        nombre_rol='Superadministrador',
        defaults={
            'descripcion': 'Rol creado automáticamente para superusuarios.',
        },
    )
    Personal.objects.create(
        nombre=instance.get_username(),
        credenciales='Superusuario',
        años_experiencia=0,
        id_rol=rol,
        usuario=instance,
    )
