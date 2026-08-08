import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée ou met à jour le compte administrateur depuis les variables Render."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "ADMIN_USERNAME ou ADMIN_PASSWORD absent : aucun compte créé."
                )
            )
            return

        User = get_user_model()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        user.email = email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Compte '{username}' créé.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Compte '{username}' mis à jour.")
            )