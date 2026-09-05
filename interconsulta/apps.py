from django.apps import AppConfig


class InterconsultaConfig(AppConfig):
    name = 'interconsulta'

    def ready(self):
        from . import signals  # noqa: F401
