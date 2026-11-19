from django.apps import AppConfig


class AgendaConfig(AppConfig):
    name = 'agenda'

    def ready(self):
        from . import signals  # noqa: F401
