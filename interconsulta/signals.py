from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profesional


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_profesional(sender, instance, created, **kwargs):
    if created and not instance.is_superuser and not hasattr(instance, 'profesional'):
        Profesional.objects.create(user=instance, rol=Profesional.Rol.MEDICO_GENERAL)
