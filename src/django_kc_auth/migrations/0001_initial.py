import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("sessions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KeycloakUser",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sub",
                    models.UUIDField(db_index=True, primary_key=True, serialize=False),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="KeycloakSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "keycloak_session_id",
                    models.UUIDField(db_index=True, editable=False),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "django_session",
                    models.OneToOneField(
                        editable="False",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sessions.session",
                    ),
                ),
                (
                    "keycloak_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="django_kc_auth.keycloakuser",
                    ),
                ),
            ],
        ),
    ]
