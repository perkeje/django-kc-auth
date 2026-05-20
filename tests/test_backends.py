import pytest
from django.contrib.auth.models import Group, User

from django_kc_auth.backends import KeycloakBackend
from django_kc_auth.models import KeycloakUser


@pytest.fixture
def backend():
    return KeycloakBackend()


@pytest.mark.django_db
class TestKeycloakBackendAuthenticate:
    def test_returns_none_without_user_info(self, backend):
        result = backend.authenticate(request=None, user_info=None)
        assert result is None

    def test_returns_none_with_empty_user_info(self, backend):
        result = backend.authenticate(request=None, user_info={})
        assert result is None

    def test_returns_none_without_username(self, backend, user_info):
        user_info.pop("username")
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is None

    def test_creates_user_on_first_login(self, backend, user_info):
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert User.objects.filter(username="testuser").exists()

    def test_creates_keycloak_user_record(self, backend, user_info):
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert KeycloakUser.objects.filter(user=result).exists()

    def test_updates_existing_user_data(self, backend, user_info):
        # First login
        backend.authenticate(request=None, user_info=user_info)

        # Second login with different data
        updated_info = dict(user_info)
        updated_info["firstName"] = "Updated"
        updated_info["email"] = "updated@example.com"
        result = backend.authenticate(request=None, user_info=updated_info)

        assert result is not None
        assert result.first_name == "Updated"
        assert result.email == "updated@example.com"
        # Only one User record should exist
        assert User.objects.filter(username="testuser").count() == 1

    def test_sets_staff_for_employees_role(self, backend, user_info):
        user_info["resource_access"]["test-client"]["roles"] = ["employees"]
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert result.is_staff is True

    def test_sets_superuser_for_admins_role(self, backend, user_info):
        user_info["resource_access"]["test-client"]["roles"] = ["admins"]
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert result.is_superuser is True

    def test_no_roles_when_resource_access_missing(self, backend, user_info):
        del user_info["resource_access"]
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert result.is_staff is False
        assert result.is_superuser is False

    def test_sets_groups_from_roles(self, backend, user_info):
        user_info["resource_access"]["test-client"]["roles"] = ["editors", "viewers"]
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        group_names = list(result.groups.values_list("name", flat=True))
        assert "editors" in group_names
        assert "viewers" in group_names

    def test_new_user_has_unusable_password(self, backend, user_info):
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert not result.has_usable_password()

    def test_sets_backend_attribute(self, backend, user_info):
        result = backend.authenticate(request=None, user_info=user_info)
        assert result is not None
        assert result.backend == "django_kc_auth.backends.KeycloakBackend"


@pytest.mark.django_db
class TestKeycloakBackendGetUser:
    def test_get_user_returns_user_by_id(self, backend):
        user = User.objects.create_user(username="getuser", password="irrelevant")
        result = backend.get_user(user.pk)
        assert result is not None
        assert result.pk == user.pk

    def test_get_user_returns_none_for_missing_id(self, backend):
        result = backend.get_user(99999)
        assert result is None
