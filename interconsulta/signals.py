from django.conf import settings
from django.db.models import Count, Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CasoTriaje, ColaInterconsulta, Profesional

PRIORIDAD_POR_RIESGO = {
    CasoTriaje.ClasificacionRiesgo.ALTO: ColaInterconsulta.Prioridad.URGENTE,
    CasoTriaje.ClasificacionRiesgo.MEDIO: ColaInterconsulta.Prioridad.ALTA,
}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_profesional(sender, instance, created, **kwargs):
    if created and not instance.is_superuser and not hasattr(instance, 'profesional'):
        Profesional.objects.create(user=instance, rol=Profesional.Rol.MEDICO_GENERAL)


def _especialista_menos_cargado():
    carga_activa = Q(casos_asignados__estado__in=[
        ColaInterconsulta.Estado.EN_ESPERA,
        ColaInterconsulta.Estado.EN_ATENCION,
    ])
    return (
        Profesional.objects.filter(rol=Profesional.Rol.ESPECIALISTA)
        .annotate(carga=Count('casos_asignados', filter=carga_activa))
        .order_by('carga', 'id')
        .first()
    )


@receiver(post_save, sender=CasoTriaje)
def encolar_caso_alto_riesgo(sender, instance, created, **kwargs):
    if not created:
        return
    prioridad = PRIORIDAD_POR_RIESGO.get(instance.clasificacion_riesgo)
    if prioridad is None:
        return

    ColaInterconsulta.objects.create(
        caso=instance,
        prioridad=prioridad,
        especialista_asignado=_especialista_menos_cargado(),
    )

    CasoTriaje.objects.filter(pk=instance.pk).update(
        estado=CasoTriaje.Estado.EN_COLA_INTERCONSULTA
    )
