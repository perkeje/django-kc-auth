from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import models


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class KeycloakUser(Timestamped):
    """
    This model represents a Keycloak user and associates them with a corresponding Django user.
    """

    sub = models.UUIDField(primary_key=True, db_index=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"Keycloak user id: {self.sub} linked to Django user: {self.user}"


class KeycloakSession(models.Model):
    """
    This model is used to track and combine created Keycloak and Django sessions together.
    """

    keycloak_session_id = models.UUIDField(editable=False, db_index=True)
    keycloak_user = models.ForeignKey(KeycloakUser, on_delete=models.CASCADE)
    django_session = models.OneToOneField(
        Session, on_delete=models.CASCADE, editable="False", unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Keycloak user id: {self.keycloak_user_id} linked to Django session: {self.django_session.session_key} and Keycloak session: {self.keycloak_session_id}"
