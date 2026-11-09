"""
URL configuration for rg_beauty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from agenda import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('landing_cliente/', views.landing_cliente, name='landing_cliente'),
    path('agendar_cita/', views.agendar_cita, name='agendar_cita'),
    path('ver_citas_cliente/', views.ver_citas_cliente, name='ver_citas_cliente'),
    path('reservas/<int:pk>/', views.reserva_detalle, name='reserva_detalle'),
    path('reservas/<int:pk>/editar/', views.reserva_editar, name='reserva_editar'),
    path('reservas/<int:pk>/eliminar/', views.reserva_eliminar, name='reserva_eliminar'),
    path('vista_administracion/', views.vista_administracion, name='vista_administracion'),
    path('agendar_cita_admin/', views.agendar_cita_admin, name='agendar_cita_admin'),
    path('clientes_admin/', views.clientes_admin, name='clientes_admin'),
    path('profesionales_admin/', views.profesionales_admin, name='profesionales_admin'),
    path('profesionales_admin/crear/', views.profesional_crear, name='profesional_crear'),
    path('roles_admin/crear/', views.rol_crear, name='rol_crear'),
    path('servicios_admin/', views.servicios_admin, name='servicios_admin'),
    path('servicios_admin/crear/', views.servicio_crear, name='servicio_crear'),
    path('servicios_admin/<int:pk>/editar/', views.servicio_editar, name='servicio_editar'),
    path('servicios_admin/<int:pk>/eliminar/', views.servicio_eliminar, name='servicio_eliminar'),
    path('categorias_servicio/crear/', views.categoria_servicio_crear, name='categoria_servicio_crear'),
    path('etiquetas_admin/', views.etiquetas_admin, name='etiquetas_admin'),
    path('notificaciones_admin/', views.notificaciones_admin, name='notificaciones_admin'),
    path('auditoria_admin/', views.auditoria_admin, name='auditoria_admin'),
    path('configuracion_admin/', views.configuracion_admin, name='configuracion_admin'),
    path('acceso_denegado/', views.acceso_denegado, name='acceso_denegado'),
    path('acceso/', views.acceso, name='acceso'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login_cliente/', views.login_cliente, name='login_cliente'),
    path('registro_cliente/', views.registro_cliente, name='registro_cliente'),

]
