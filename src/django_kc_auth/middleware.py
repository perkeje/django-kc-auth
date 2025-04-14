import datetime
import logging
import re

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode

from .keycloak_openid_config import keycloak_openid

logger = logging.getLogger(__name__)


class AutoKeycloakLoginMiddleware:
    """Middleware that tries to auto log in user if they have
    active Keycloak session in browser
    """

    ignored_routes = [
        f"{reverse('kc_auth_logout-listener')}*",
        f"{reverse('kc_auth_callback')}*",
        "/static/*",
        "/favicon.ico",
        "/__reload__/events/*",
    ] + getattr(settings, "KC_SILENT_LOGOUT_IGNORED_ROUTES", [])

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        login_attempts = request.session.get("kc_login_attempts", 0)
        last_attempt = request.session.get("kc_last_attempt_at")
        now = datetime.datetime.now()
        last_attempt_valid = True
        if last_attempt:
            last_attempt = datetime.datetime.strptime(last_attempt, "%Y-%m-%d %H:%M:%S")
            diff = now - last_attempt
            if diff.total_seconds() < getattr(
                settings, "KC_SILENT_LOGIN_TIMEOUT_SECONDS", 3
            ):
                last_attempt_valid = False

        if (
            request.method == "GET"
            and not request.user.is_authenticated
            and not self.is_ignored(request.path)
            and not request.session.get("soft_logout", None)
            and last_attempt_valid
            and login_attempts
            < getattr(settings, "KC_SILENT_LOGIN_ALLOWED_ATTEMPTS", 5)
        ):
            logger.info("Silent authentication attempt.")

            server_url = request.build_absolute_uri("/")[:-1]
            callback_url = f"{server_url}{reverse('kc_auth_callback')}"

            auth_url = (
                keycloak_openid.auth_url(
                    redirect_uri=callback_url,
                    scope="openid email",
                    state=urlsafe_base64_encode(
                        request.get_full_path().encode("utf-8")
                    ),
                )
                + "&prompt=none"
            )
            request.session["kc_login_attempts"] = login_attempts + 1
            request.session["kc_last_attempt_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
            response = redirect(auth_url)
            return response

        return self.get_response(request)

    def is_ignored(self, path):
        for pattern in self.ignored_routes:
            if re.search(pattern, path):
                return True
        return False
