--
-- Create model Cliente
--
CREATE TABLE `cliente` (`id_cliente` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre_c` varchar(100) NOT NULL, `telefono` varchar(20) NOT NULL, `correo` varchar(150) NOT NULL);
--
-- Create model Oficio
--
CREATE TABLE `oficio` (`id_oficio` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre_oficio` varchar(100) NOT NULL, `descripcion` longtext NOT NULL);
--
-- Create model PagoAbono
--
CREATE TABLE `pago_abono` (`id_abono` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `valor` numeric(10, 2) NOT NULL, `fecha` date NOT NULL);
--
-- Create model Personal
--
CREATE TABLE `personal` (`id_personal` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre` varchar(100) NOT NULL, `credenciales` varchar(255) NOT NULL, `años_experiencia` integer UNSIGNED NOT NULL CHECK (`años_experiencia` >= 0));
--
-- Create model Rol
--
CREATE TABLE `rol` (`id_rol` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre_rol` varchar(100) NOT NULL, `descripcion` longtext NOT NULL);
--
-- Create model Servicio
--
CREATE TABLE `servicio` (`id_servicio` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `nombre_s` varchar(100) NOT NULL, `descripcion` longtext NOT NULL);
--
-- Create model OficioPersonal
--
CREATE TABLE `oficio_personal` (`id_oficio_personal` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `id_oficio` integer NOT NULL, `id_personal` integer NOT NULL);
--
-- Create model RegistrosAuditoria
--
CREATE TABLE `registros_auditoria` (`id_registro` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `accion` longtext NOT NULL, `fecha` datetime(6) NOT NULL, `id_personal` integer NOT NULL);
--
-- Create model Reserva
--
CREATE TABLE `reserva` (`id_reserva` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `fecha` date NOT NULL, `hora` time(6) NOT NULL, `estado` varchar(20) NOT NULL, `id_abono` integer NULL UNIQUE, `id_cliente` integer NOT NULL, `id_personal` integer NOT NULL);
--
-- Create model Notificacion
--
CREATE TABLE `notificacion` (`id_notificacion` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `mensaje` longtext NOT NULL, `fecha` datetime(6) NOT NULL, `tipo` varchar(50) NOT NULL, `id_cliente` integer NOT NULL, `id_reserva` integer NOT NULL);
--
-- Add field id_rol to personal
--
ALTER TABLE `personal` ADD COLUMN `id_rol` integer NOT NULL , ADD CONSTRAINT `personal_id_rol_ce5f7404_fk_rol_id_rol` FOREIGN KEY (`id_rol`) REFERENCES `rol`(`id_rol`);
--
-- Create model ServicioPersonal
--
CREATE TABLE `servicio_personal` (`id_personal_servicio` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `duracion_aproximada` integer UNSIGNED NOT NULL CHECK (`duracion_aproximada` >= 0), `precio` numeric(10, 2) NOT NULL, `id_personal` integer NOT NULL, `id_servicio` integer NOT NULL);
--
-- Add field id_personal_servicio to reserva
--
ALTER TABLE `reserva` ADD COLUMN `id_personal_servicio` integer NOT NULL , ADD CONSTRAINT `reserva_id_personal_servicio_cec44f27_fk_servicio_` FOREIGN KEY (`id_personal_servicio`) REFERENCES `servicio_personal`(`id_personal_servicio`);
ALTER TABLE `oficio_personal` ADD CONSTRAINT `oficio_personal_id_oficio_ec7c0cfb_fk_oficio_id_oficio` FOREIGN KEY (`id_oficio`) REFERENCES `oficio` (`id_oficio`);
ALTER TABLE `oficio_personal` ADD CONSTRAINT `oficio_personal_id_personal_41fd48a9_fk_personal_id_personal` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`);
ALTER TABLE `registros_auditoria` ADD CONSTRAINT `registros_auditoria_id_personal_675b6c4d_fk_personal_id_personal` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`);
ALTER TABLE `reserva` ADD CONSTRAINT `reserva_id_abono_b4628753_fk_pago_abono_id_abono` FOREIGN KEY (`id_abono`) REFERENCES `pago_abono` (`id_abono`);
ALTER TABLE `reserva` ADD CONSTRAINT `reserva_id_cliente_54ffb038_fk_cliente_id_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`);
ALTER TABLE `reserva` ADD CONSTRAINT `reserva_id_personal_fa0ee867_fk_personal_id_personal` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`);
ALTER TABLE `notificacion` ADD CONSTRAINT `notificacion_id_cliente_22959eac_fk_cliente_id_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `cliente` (`id_cliente`);
ALTER TABLE `notificacion` ADD CONSTRAINT `notificacion_id_reserva_bdfb628e_fk_reserva_id_reserva` FOREIGN KEY (`id_reserva`) REFERENCES `reserva` (`id_reserva`);
ALTER TABLE `servicio_personal` ADD CONSTRAINT `servicio_personal_id_personal_2b482213_fk_personal_id_personal` FOREIGN KEY (`id_personal`) REFERENCES `personal` (`id_personal`);
ALTER TABLE `servicio_personal` ADD CONSTRAINT `servicio_personal_id_servicio_445f0f8a_fk_servicio_id_servicio` FOREIGN KEY (`id_servicio`) REFERENCES `servicio` (`id_servicio`);
