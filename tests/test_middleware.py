import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory

from django_kc_auth.middleware import AutoKeycloakLoginMiddleware


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def get_response():
    return lambda req: HttpResponse("OK")


def make_middleware(get_response):
    return AutoKeycloakLoginMiddleware(get_response)


def make_session():
    """Return a minimal dict acting as a session."""
    return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutoKeycloakLoginMiddleware:
    def test_authenticated_user_passes_through(self, factory, get_response):
        request = factory.get("/")
        request.session = make_session()
        user = User(username="auth_user")
        request.user = user

        middleware = make_middleware(get_response)
        response = middleware(request)
        assert response.status_code == 200

    def test_unauthenticated_get_redirects_to_keycloak(self, factory, get_response):
        request = factory.get("/some-protected-page/")
        request.session = make_session()
        request.user = AnonymousUser()

        mock_auth_url = "http://localhost:8080/auth?prompt=none"
        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = mock_auth_url
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 302

    def test_ignores_callback_path(self, factory, get_response):
        request = factory.get("/callback/")
        request.session = make_session()
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200

    def test_ignores_logout_listener_path(self, factory, get_response):
        request = factory.get("/logout-listener/")
        request.session = make_session()
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200

    def test_ignores_static_path(self, factory, get_response):
        request = factory.get("/static/app.js")
        request.session = make_session()
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200

    def test_soft_logout_passes_through(self, factory, get_response):
        request = factory.get("/")
        session = make_session()
        session["soft_logout"] = True
        request.session = session
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200

    def test_max_attempts_passes_through(self, factory, get_response):
        request = factory.get("/")
        session = make_session()
        session["kc_login_attempts"] = 5
        request.session = session
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200

    def test_recent_attempt_passes_through(self, factory, get_response):
        now = datetime.datetime.now()
        request = factory.get("/")
        session = make_session()
        session["kc_login_attempts"] = 1
        session["kc_last_attempt_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        request.session = session
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        # Within timeout window (default 3s), should pass through
        assert response.status_code == 200

    def test_increments_login_attempts(self, factory, get_response):
        request = factory.get("/some-page/")
        session = make_session()
        request.session = session
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth?prompt=none"
            middleware = make_middleware(get_response)
            middleware(request)

        assert request.session.get("kc_login_attempts") == 1

    def test_post_request_passes_through(self, factory, get_response):
        request = factory.post("/")
        request.session = make_session()
        request.user = AnonymousUser()

        with patch("django_kc_auth.middleware.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            middleware = make_middleware(get_response)
            response = middleware(request)

        assert response.status_code == 200
