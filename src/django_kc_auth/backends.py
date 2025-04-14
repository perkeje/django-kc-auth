import logging

from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import Group, User
from django.db import transaction

from .models import KeycloakUser

# Custom authentication backend for Keycloak integration, open to other customization
logger = logging.getLogger(__name__)


class KeycloakBackend(BaseBackend):

    @transaction.atomic
    def authenticate(self, request, user_info=None):
        """
        Authenticate a user based on Keycloak-provided user information.

        Parameters:
            request: The HTTP request object (optional, can be None).
            user_info: A dictionary containing user data from Keycloak.

        Returns:
            A Django User object if authentication is successful, or None otherwise.
        """
        if not user_info:
            logger.warning("Authentication failed: No user_info provided.")
            return None

        # Extract user data from the Keycloak-provided dictionary
        sub = user_info.get("sub")
        username = user_info.get("username")
        first_name = user_info.get("firstName")
        last_name = user_info.get("lastName")
        email = user_info.get("email")

        try:
            roles = (
                user_info.get("resource_access")
                .get(settings.KC_CLIENT_ID)
                .get("roles", [])
            )
        except:
            roles = []

        if not username:
            logger.warning("Authentication failed: Missing username in user_info.")
            return None

        try:
            user, created = User.objects.get_or_create(username=username)
            if created:
                logger.info("Created new user: %s", username)
                user.set_unusable_password()
            user.first_name = first_name or ""
            user.last_name = last_name or ""
            user.email = email or ""
            user.is_staff = "employees" in roles
            user.is_superuser = "admins" in roles

            kc_roles = settings.KC_ROLES
            current_groups = [group.name for group in user.groups.all()]
            current_groups = [
                group for group in current_groups if group not in kc_roles
            ]
            roles = current_groups + roles

            required_groups = [
                Group.objects.get_or_create(name=group_name)[0] for group_name in roles
            ]

            user.groups.set(required_groups)
            user.save()

            KeycloakUser.objects.get_or_create(sub=sub, user=user)

            user.backend = "django_kc_auth.backends.KeycloakBackend"
            return user

        except Exception as e:
            logger.error(
                "Error during authentication for user %s: %s", username, str(e)
            )
            return None

    def get_user(self, user_id):
        """
        Retrieve a User object by its ID.

        Parameters:
            user_id: The primary key of the User object to retrieve.

        Returns:
            A User object if found, or None otherwise.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
