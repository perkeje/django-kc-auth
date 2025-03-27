from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Add custom permissions"

    def handle(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(Permission)
        custom_permissions = [
            {"codename": "view_dashboard", "name": "Can view dashboard"},
        ]

        for perm in custom_permissions:
            _, created = Permission.objects.get_or_create(
                codename=perm["codename"],
                name=perm["name"],
                content_type=content_type,
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Permission '{perm['name']}' created.")
                )
            else:
                self.stdout.write(f"Permission '{perm['name']}' already exists.")
