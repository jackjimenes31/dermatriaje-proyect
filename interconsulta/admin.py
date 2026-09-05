from django.contrib import admin

from .models import CasoTriaje, ColaInterconsulta, EstablecimientoSalud, Paciente, Profesional


@admin.register(EstablecimientoSalud)
class EstablecimientoSaludAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nivel', 'departamento', 'provincia', 'distrito', 'tiene_conectividad_estable')
    list_filter = ('nivel', 'departamento', 'tiene_conectividad_estable')
    search_fields = ('nombre', 'codigo_renaes')


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol', 'establecimiento', 'especialidad')
    list_filter = ('rol', 'establecimiento')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'tipo_documento', 'numero_documento', 'edad', 'sexo', 'creado_en')
    list_filter = ('sexo', 'tipo_documento')
    search_fields = ('nombres', 'apellidos', 'numero_documento')


@admin.register(CasoTriaje)
class CasoTriajeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'paciente', 'tipo_lesion_predicho', 'confianza_modelo',
        'clasificacion_riesgo', 'estado', 'establecimiento', 'fecha_evaluacion',
        'profesional_resuelve', 'fecha_resolucion',
    )
    list_filter = ('tipo_lesion_predicho', 'clasificacion_riesgo', 'estado', 'establecimiento')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'paciente__numero_documento')


@admin.register(ColaInterconsulta)
class ColaInterconsultaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'caso', 'prioridad', 'estado', 'especialista_asignado',
        'fecha_ingreso', 'fecha_atencion',
    )
    list_filter = ('prioridad', 'estado')
