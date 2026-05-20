import datetime
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils.http import urlsafe_base64_encode

from django_kc_auth.models import KeycloakSession, KeycloakUser
from keycloak.exceptions import KeycloakError

from django_kc_auth.keycloak_openid_config import (
    BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL,
    BACKCHANNEL_LOGOUT_EVENT_URL,
    REALM_URL,
)


# ---------------------------------------------------------------------------
# LoginView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLoginView:
    def test_redirects_to_keycloak(self, client):
        mock_auth_url = "http://localhost:8080/auth?response_type=code"
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = mock_auth_url
            response = client.get("/login/")
        assert response.status_code == 302
        assert response["Location"] == mock_auth_url

    def test_encodes_next_url_in_state(self, client):
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.auth_url.return_value = "http://kc/auth"
            client.get("/login/?next=/dashboard/")
            _, kwargs = mock_kc.auth_url.call_args
            state = kwargs.get("state") or mock_kc.auth_url.call_args[1].get("state")
            decoded = urlsafe_base64_encode("/dashboard/".encode("utf-8"))
            assert state == decoded


# ---------------------------------------------------------------------------
# CallbackView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallbackView:
    def test_no_code_redirects(self, client):
        response = client.get("/callback/")
        assert response.status_code == 302

    def test_successful_login_redirects(self, client, user_info, kc_tokens):
        encoded_state = urlsafe_base64_encode("/dashboard/".encode("utf-8"))
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.token.return_value = kc_tokens
            mock_kc.userinfo.return_value = user_info
            response = client.get(f"/callback/?code=authcode&state={encoded_state}")
        assert response.status_code == 302
        assert response["Location"] == "/dashboard/"
        assert User.objects.filter(username="testuser").exists()

    def test_successful_login_stores_tokens(self, client, user_info, kc_tokens):
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.token.return_value = kc_tokens
            mock_kc.userinfo.return_value = user_info
            client.get("/callback/?code=authcode")
        assert client.session.get("access_token") == "fake-access-token"
        assert client.session.get("id_token") == "fake-id-token"

    def test_keycloak_error_redirects(self, client):
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.token.side_effect = KeycloakError("token error")
            response = client.get("/callback/?code=badcode")
        assert response.status_code == 302

    def test_auth_failure_redirects(self, client, user_info, kc_tokens):
        # Remove username so authenticate() returns None
        bad_user_info = dict(user_info)
        bad_user_info.pop("username")
        with patch("django_kc_auth.views.keycloak_openid") as mock_kc:
            mock_kc.token.return_value = kc_tokens
            mock_kc.userinfo.return_value = bad_user_info
            response = client.get("/callback/?code=authcode")
        assert response.status_code == 302
        assert not User.objects.filter(username="testuser").exists()


# ---------------------------------------------------------------------------
# LogoutView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogoutView:
    def test_logout_requires_authentication(self, client):
        response = client.post("/logout/")
        assert response.status_code == 302
        # Should redirect to login, not to Keycloak logout
        assert "logout" not in response["Location"] or "login" in response["Location"]

    def test_logout_with_id_token_redirects_to_keycloak(self, client):
        user = User.objects.create_user(username="logoutuser", password="pw")
        client.force_login(user)
        session = client.session
        session["id_token"] = "fake-id-token"
        session.save()

        mock_logout_url = "http://localhost:8080/realms/test-realm/protocol/openid-connect/logout?id_token_hint=fake-id-token"
        with patch("django_kc_auth.views.get_logout_url", return_value=mock_logout_url):
            response = client.post("/logout/")

        assert response.status_code == 302
        assert response["Location"] == mock_logout_url

    def test_logout_without_id_token_redirects_locally(self, client):
        user = User.objects.create_user(username="logoutuser2", password="pw")
        client.force_login(user)
        # No id_token in session
        with patch("django_kc_auth.views.get_logout_url") as mock_get_url:
            response = client.post("/logout/")

        assert response.status_code == 302
        mock_get_url.assert_not_called()

    def test_logout_clears_django_auth(self, client):
        user = User.objects.create_user(username="logoutuser3", password="pw")
        client.force_login(user)
        with patch("django_kc_auth.views.get_logout_url", return_value="/"):
            client.post("/logout/")
        assert "_auth_user_id" not in client.session


# ---------------------------------------------------------------------------
# LogoutListenerView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogoutListenerView:
    def _make_claims(self, sid, events=None, iss=None):
        if events is None:
            events = {BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL: {}}
        if iss is None:
            iss = REALM_URL
        return {"events": events, "iss": iss, "sid": sid}

    def _create_keycloak_session(self, sid):
        user = User.objects.create_user(username=f"kcuser-{sid[:8]}", password="pw")
        kc_user = KeycloakUser.objects.create(
            sub=uuid.uuid4(),
            user=user,
        )
        django_session = Session.objects.create(
            session_key="abc123456789012345678901234567",
            session_data="{}",
            expire_date=datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
        )
        kc_session = KeycloakSession.objects.create(
            keycloak_session_id=sid,
            keycloak_user=kc_user,
            django_session=django_session,
        )
        return django_session, kc_session

    def test_valid_logout_deletes_session(self, client):
        sid = "cccccccc-dddd-eeee-ffff-000000000000"
        django_session, _ = self._create_keycloak_session(sid)
        claims = self._make_claims(sid)

        with patch("django_kc_auth.views.jwt") as mock_jwt:
            mock_instance = MagicMock()
            mock_instance.decode.return_value = claims
            mock_jwt.JWT.return_value = mock_instance
            response = client.post(
                "/logout-listener/",
                data=f"logout_token=fake.jwt.token",
                content_type="application/x-www-form-urlencoded",
            )

        assert response.status_code == 200
        assert not Session.objects.filter(session_key=django_session.session_key).exists()

    def test_wrong_event_type_returns_400(self, client):
        sid = "dddddddd-eeee-ffff-0000-111111111111"
        claims = self._make_claims(sid, events={"http://wrong-event-type": {}})

        with patch("django_kc_auth.views.jwt") as mock_jwt:
            mock_instance = MagicMock()
            mock_instance.decode.return_value = claims
            mock_jwt.JWT.return_value = mock_instance
            response = client.post(
                "/logout-listener/",
                data="logout_token=fake.jwt.token",
                content_type="application/x-www-form-urlencoded",
            )

        assert response.status_code == 400

    def test_issuer_mismatch_returns_400(self, client):
        sid = "eeeeeeee-ffff-0000-1111-222222222222"
        claims = self._make_claims(
            sid,
            events={BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL: {}},
            iss="http://wrong-issuer/realms/wrong",
        )

        with patch("django_kc_auth.views.jwt") as mock_jwt:
            mock_instance = MagicMock()
            mock_instance.decode.return_value = claims
            mock_jwt.JWT.return_value = mock_instance
            response = client.post(
                "/logout-listener/",
                data="logout_token=fake.jwt.token",
                content_type="application/x-www-form-urlencoded",
            )

        assert response.status_code == 400

    def test_decode_error_returns_500(self, client):
        with patch("django_kc_auth.views.jwt") as mock_jwt:
            mock_instance = MagicMock()
            mock_instance.decode.side_effect = Exception("decode failure")
            mock_jwt.JWT.return_value = mock_instance
            response = client.post(
                "/logout-listener/",
                data="logout_token=fake.jwt.token",
                content_type="application/x-www-form-urlencoded",
            )

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# RemoteLogoutView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRemoteLogoutView:
    def test_remote_logout_calls_delete_session(self, client):
        user = User.objects.create_user(username="remoteuser", password="pw")
        KeycloakUser.objects.create(sub=uuid.uuid4(), user=user)
        client.force_login(user)

        with patch("django_kc_auth.views.delete_session") as mock_delete:
            response = client.post(
                "/remote-logout/",
                data={"session_id": "some-session-id"},
            )

        mock_delete.assert_called_once_with("some-session-id")
        assert response.status_code == 302

    def test_remote_logout_no_keycloak_user_redirects(self, client):
        user = User.objects.create_user(username="remoteuser2", password="pw")
        # No KeycloakUser record for this user
        client.force_login(user)

        with patch("django_kc_auth.views.delete_session") as mock_delete:
            response = client.post(
                "/remote-logout/",
                data={"session_id": "some-session-id"},
            )

        mock_delete.assert_not_called()
        assert response.status_code == 302
