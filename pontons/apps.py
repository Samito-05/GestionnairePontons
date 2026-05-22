from django.apps import AppConfig


class PontonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pontons'

    def ready(self):
        import pontons.models  # noqa — registers post_save signal for UserProfile
