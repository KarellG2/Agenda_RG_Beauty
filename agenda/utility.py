from agenda.models import Personal, RegistrosAuditoria


def registrar_accion(usuario, accion):
    personal = Personal.objects.filter(usuario=usuario).first()
    return RegistrosAuditoria.objects.create(
        accion=accion.strip(),
        id_personal=personal,
    )