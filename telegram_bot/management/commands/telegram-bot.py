from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Implemented to Django application telegram bot setup command'

    def handle(self, *args, **kwargs):
        pass
