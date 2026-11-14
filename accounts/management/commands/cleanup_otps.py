from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import PhoneOTP

class Command(BaseCommand):
    help = 'Remove obsolete OTP records and pending registration payloads.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=getattr(settings, "OTP_RETENTION_DAYS", 7))
        deleted, _ = PhoneOTP.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Removed {deleted} obsolete OTP records.'))
