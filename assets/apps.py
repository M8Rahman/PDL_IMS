# assets/apps.py
from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assets'
    verbose_name = 'Asset Management'
    
    def ready(self):
        """Import signals when app is ready."""
        import assets.signals  # We'll create this for auto-creating assets from GRN