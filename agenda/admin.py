from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin 
# Register your models here.

class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'id_cliente', 
        'nombre_c', 
        'telefono', 
        'correo')
    search_fields = ('nombre_c', 'telefono', 'correo')
    list_filter = ('nombre_c', 'telefono', 'correo')
    
    