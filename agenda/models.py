
from django.db import models


# TABLA CLIENTE

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre_c = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField(max_length=150)

    class Meta:
        db_table = 'cliente'

    def __str__(self):
        return self.nombre_c


# TABLA ROL

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=100)
    descripcion = models.TextField()

    class Meta:
        db_table = 'rol'

    def __str__(self):
        return self.nombre_rol


# TABLA PERSONAL

class Personal(models.Model):
    id_personal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    credenciales = models.CharField(max_length=255)
    anios_experiencia = models.PositiveIntegerField()

    id_rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        db_column='id_rol',
        related_name='personal'
    )

    class Meta:
        db_table = 'personal'

    def __str__(self):
        return self.nombre


# TABLA SERVICIO

class Servicio(models.Model):
    id_servicio = models.AutoField(primary_key=True)
    nombre_s = models.CharField(max_length=100)
    descripcion = models.TextField()

    class Meta:
        db_table = 'servicio'

    def __str__(self):
        return self.nombre_s


# TABLA SERVICIO_PERSONAL

class ServicioPersonal(models.Model):
    id_personal_servicio = models.AutoField(primary_key=True)

    id_personal = models.ForeignKey(
        Personal,
        on_delete=models.PROTECT,
        db_column='id_personal',
        related_name='servicios_asignados'
    )

    id_servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        db_column='id_servicio',
        related_name='personal_asignado'
    )

    duracion_aproximada = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'servicio_personal'

    def __str__(self):
        return f"{self.id_servicio} - {self.id_personal}"


# TABLA PAGO_ABONO

class PagoAbono(models.Model):
    id_abono = models.AutoField(primary_key=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    class Meta:
        db_table = 'pago_abono'

    def __str__(self):
        return str(self.valor)


# TABLA RESERVA

class Reserva(models.Model):

    ESTADOS = [
        ('confirmado', 'Confirmado'),
        ('pendiente', 'Pendiente'),
        ('cancelado', 'Cancelado'),
    ]

    id_reserva = models.AutoField(primary_key=True)
    fecha = models.DateField()
    hora = models.TimeField()

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='pendiente'
    )

    id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column='id_cliente',
        related_name='reservas'
    )

    id_personal_servicio = models.ForeignKey(
        ServicioPersonal,
        on_delete=models.PROTECT,
        db_column='id_personal_servicio',
        related_name='reservas'
    )

    id_personal = models.ForeignKey(
        Personal,
        on_delete=models.PROTECT,
        db_column='id_personal',
        related_name='reservas'
    )

    id_abono = models.OneToOneField(
        PagoAbono,
        on_delete=models.SET_NULL,
        db_column='id_abono',
        null=True,
        blank=True,
        related_name='reserva'
    )

    class Meta:
        db_table = 'reserva'

    def __str__(self):
        return f"Reserva {self.id_reserva}"


# TABLA NOTIFICACION

class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)

    id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column='id_cliente',
        related_name='notificaciones'
    )

    id_reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        db_column='id_reserva',
        related_name='notificaciones'
    )

    mensaje = models.TextField()
    fecha = models.DateTimeField()
    tipo = models.CharField(max_length=50)

    class Meta:
        db_table = 'notificacion'

    def __str__(self):
        return f"Notificación {self.id_notificacion}"


# TABLA OFICIO

class Oficio(models.Model):
    id_oficio = models.AutoField(primary_key=True)
    nombre_oficio = models.CharField(max_length=100)
    descripcion = models.TextField()

    class Meta:
        db_table = 'oficio'

    def __str__(self):
        return self.nombre_oficio


# TABLA OFICIO_PERSONAL

class OficioPersonal(models.Model):
    id_oficio_personal = models.AutoField(primary_key=True)

    id_oficio = models.ForeignKey(
        Oficio,
        on_delete=models.CASCADE,
        db_column='id_oficio',
        related_name='personal_oficio'
    )

    id_personal = models.ForeignKey(
        Personal,
        on_delete=models.CASCADE,
        db_column='id_personal',
        related_name='oficios'
    )

    class Meta:
        db_table = 'oficio_personal'

    def __str__(self):
        return f"{self.id_oficio} - {self.id_personal}"


# TABLA REGISTROS_AUDITORIA

class RegistrosAuditoria(models.Model):
    id_registro = models.AutoField(primary_key=True)
    accion = models.TextField()
    fecha = models.DateTimeField()

    id_personal = models.ForeignKey(
        Personal,
        on_delete=models.PROTECT,
        db_column='id_personal',
        related_name='registros_auditoria'
    )

    class Meta:
        db_table = 'registros_auditoria'

    def __str__(self):
        return f"Registro {self.id_registro}"
