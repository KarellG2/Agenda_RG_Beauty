-- Esquema funcional de Agenda RG Beauty para MySQL 8.0+
-- Importar este archivo desde MySQL Workbench o:
-- mysql -u root -p < schema_agenda.sql

CREATE DATABASE IF NOT EXISTS sistema_reservas
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sistema_reservas;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS agenda_reserva_etiquetas;
DROP TABLE IF EXISTS notificacion;
DROP TABLE IF EXISTS registros_auditoria;
DROP TABLE IF EXISTS reserva;
DROP TABLE IF EXISTS pago_abono;
DROP TABLE IF EXISTS servicio_personal;
DROP TABLE IF EXISTS oficio_personal;
DROP TABLE IF EXISTS servicio;
DROP TABLE IF EXISTS etiqueta;
DROP TABLE IF EXISTS categoria_servicio;
DROP TABLE IF EXISTS oficio;
DROP TABLE IF EXISTS personal;
DROP TABLE IF EXISTS cliente;
DROP TABLE IF EXISTS rol;
DROP TABLE IF EXISTS django_session;
DROP TABLE IF EXISTS auth_user;

SET FOREIGN_KEY_CHECKS = 1;


-- Cuenta de Django utilizada por cliente y personal
CREATE TABLE auth_user (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME(6) NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY auth_user_username_unique (username)
) ENGINE=InnoDB;


CREATE TABLE rol (
    id_rol INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_rol VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    PRIMARY KEY (id_rol)
) ENGINE=InnoDB;

CREATE TABLE cliente (
    id_cliente INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_c VARCHAR(100) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    usuario_id INT UNSIGNED NULL,
    PRIMARY KEY (id_cliente),
    UNIQUE KEY cliente_usuario_unique (usuario_id),
    CONSTRAINT cliente_usuario_fk
        FOREIGN KEY (usuario_id) REFERENCES auth_user (id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE personal (
    id_personal INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    credenciales VARCHAR(255) NOT NULL,
    años_experiencia INT UNSIGNED NOT NULL,
    id_rol INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NULL,
    PRIMARY KEY (id_personal),
    UNIQUE KEY personal_usuario_unique (usuario_id),
    CONSTRAINT personal_id_rol_fk
        FOREIGN KEY (id_rol) REFERENCES rol (id_rol)
        ON DELETE RESTRICT,
    CONSTRAINT personal_usuario_fk
        FOREIGN KEY (usuario_id) REFERENCES auth_user (id)
        ON DELETE SET NULL,
    CONSTRAINT personal_experiencia_check
        CHECK (años_experiencia >= 0)
) ENGINE=InnoDB;

CREATE TABLE categoria_servicio (
    id_categoria INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    PRIMARY KEY (id_categoria)
) ENGINE=InnoDB;

CREATE TABLE servicio (
    id_servicio INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_s VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    id_categoria INT UNSIGNED NULL,
    PRIMARY KEY (id_servicio),
    CONSTRAINT servicio_categoria_fk
        FOREIGN KEY (id_categoria) REFERENCES categoria_servicio (id_categoria)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE etiqueta (
    id_etiqueta INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    color VARCHAR(20) NOT NULL DEFAULT '#d9c7cc',
    PRIMARY KEY (id_etiqueta),
    UNIQUE KEY etiqueta_nombre_unique (nombre)
) ENGINE=InnoDB;

CREATE TABLE oficio (
    id_oficio INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_oficio VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    PRIMARY KEY (id_oficio)
) ENGINE=InnoDB;

CREATE TABLE oficio_personal (
    id_oficio_personal INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_oficio INT UNSIGNED NOT NULL,
    id_personal INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_oficio_personal),
    CONSTRAINT oficio_personal_oficio_fk
        FOREIGN KEY (id_oficio) REFERENCES oficio (id_oficio)
        ON DELETE CASCADE,
    CONSTRAINT oficio_personal_personal_fk
        FOREIGN KEY (id_personal) REFERENCES personal (id_personal)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE servicio_personal (
    id_personal_servicio INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_personal INT UNSIGNED NOT NULL,
    id_servicio INT UNSIGNED NOT NULL,
    duracion_aproximada INT UNSIGNED NOT NULL,
    precio DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id_personal_servicio),
    CONSTRAINT servicio_personal_personal_fk
        FOREIGN KEY (id_personal) REFERENCES personal (id_personal)
        ON DELETE RESTRICT,
    CONSTRAINT servicio_personal_servicio_fk
        FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio)
        ON DELETE CASCADE,
    CONSTRAINT servicio_personal_duracion_check
        CHECK (duracion_aproximada >= 0),
    CONSTRAINT servicio_personal_precio_check
        CHECK (precio >= 0)
) ENGINE=InnoDB;

CREATE TABLE pago_abono (
    id_abono INT UNSIGNED NOT NULL AUTO_INCREMENT,
    valor DECIMAL(10, 2) NOT NULL,
    fecha DATE NOT NULL,
    PRIMARY KEY (id_abono),
    CONSTRAINT pago_abono_valor_check
        CHECK (valor >= 0)
) ENGINE=InnoDB;

CREATE TABLE reserva (
    id_reserva INT UNSIGNED NOT NULL AUTO_INCREMENT,
    fecha DATE NOT NULL,
    hora TIME(6) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    id_cliente INT UNSIGNED NOT NULL,
    id_personal INT UNSIGNED NOT NULL,
    id_personal_servicio INT UNSIGNED NOT NULL,
    id_abono INT UNSIGNED NULL,
    PRIMARY KEY (id_reserva),
    UNIQUE KEY reserva_abono_unique (id_abono),
    CONSTRAINT reserva_cliente_fk
        FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
        ON DELETE RESTRICT,
    CONSTRAINT reserva_personal_fk
        FOREIGN KEY (id_personal) REFERENCES personal (id_personal)
        ON DELETE RESTRICT,
    CONSTRAINT reserva_servicio_personal_fk
        FOREIGN KEY (id_personal_servicio) REFERENCES servicio_personal (id_personal_servicio)
        ON DELETE RESTRICT,
    CONSTRAINT reserva_abono_fk
        FOREIGN KEY (id_abono) REFERENCES pago_abono (id_abono)
        ON DELETE SET NULL,
    CONSTRAINT reserva_estado_check
        CHECK (estado IN ('confirmado', 'pendiente', 'cancelado'))
) ENGINE=InnoDB;

CREATE TABLE agenda_reserva_etiquetas (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    reserva_id INT UNSIGNED NOT NULL,
    etiqueta_id INT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY reserva_etiqueta_unique (reserva_id, etiqueta_id),
    CONSTRAINT reserva_etiquetas_reserva_fk
        FOREIGN KEY (reserva_id) REFERENCES reserva (id_reserva)
        ON DELETE CASCADE,
    CONSTRAINT reserva_etiquetas_etiqueta_fk
        FOREIGN KEY (etiqueta_id) REFERENCES etiqueta (id_etiqueta)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE notificacion (
    id_notificacion INT UNSIGNED NOT NULL AUTO_INCREMENT,
    mensaje TEXT NOT NULL,
    fecha DATETIME(6) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    id_cliente INT UNSIGNED NOT NULL,
    id_reserva INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_notificacion),
    CONSTRAINT notificacion_cliente_fk
        FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente)
        ON DELETE CASCADE,
    CONSTRAINT notificacion_reserva_fk
        FOREIGN KEY (id_reserva) REFERENCES reserva (id_reserva)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE registros_auditoria (
    id_registro INT UNSIGNED NOT NULL AUTO_INCREMENT,
    accion VARCHAR(255) NOT NULL,
    fecha DATETIME(6) NOT NULL,
    id_personal INT UNSIGNED NULL,
    PRIMARY KEY (id_registro),
    CONSTRAINT registros_auditoria_personal_fk
        FOREIGN KEY (id_personal) REFERENCES personal (id_personal)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE django_session (
    session_key VARCHAR(40) NOT NULL,
    session_data LONGTEXT NOT NULL,
    expire_date DATETIME(6) NOT NULL,
    PRIMARY KEY (session_key),
    KEY django_session_expire_date_idx (expire_date)
) ENGINE=InnoDB;
