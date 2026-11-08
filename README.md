# Agenda_RG_Beauty

## Requisitos

- Python 3.10 o superior
- MySQL 8.0 o superior

## Instalación sin entorno virtual

Instala las dependencias directamente en tu instalación de Python:

```powershell
py -m pip install -r requirements.txt
```

Configura en `rg_beauty/settings.py` los datos de conexión a tu base de datos
MySQL. Después, desde la carpeta del proyecto, ejecuta:

```powershell
py manage.py migrate
py manage.py runserver
```

Para ejecutar las pruebas:

```powershell
py manage.py test agenda
```
o desde la cmd