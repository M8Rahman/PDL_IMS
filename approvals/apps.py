
# approvals/apps.py
from django.apps import AppConfig


class ApprovalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'approvals'
    verbose_name = 'Approval Workflows'
    
    def ready(self):
        """Import signals when app is ready."""
        import approvals.signals