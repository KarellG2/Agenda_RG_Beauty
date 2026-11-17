import logging

from agenda.models import Personal, RegistrosAuditoria

logger = logging.getLogger(__name__)


def registrar_accion(usuario, accion):
    personal = Personal.objects.filter(usuario=usuario).first()
    if personal is None:
        logger.warning(
            'No se registró la auditoría porque el usuario %s '
            'no tiene un Personal asociado.',
            usuario.get_username(),
        )
        return None

    return RegistrosAuditoria.objects.create(
        accion=accion.strip(),
        id_personal=personal,
    )