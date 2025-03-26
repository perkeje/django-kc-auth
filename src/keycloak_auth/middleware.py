import fnmatch
import logging

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
        reverse("logout-listener"),
        reverse("callback"),
        "/static/",
        "/favicon.ico",
        "/__reload__/events/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method == "GET"
            and not request.session.get("silent_login", None)
            and not request.user.is_authenticated
            and not self.is_ignored(request.path)
        ):
            logger.info("Silent authentication attempt.")

            server_url = request.build_absolute_uri("/")[:-1]
            callback_url = f"{server_url}{reverse("callback")}"

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
            response = redirect(auth_url)
            request.session["silent_login"] = True
            return response

        return self.get_response(request)

    def is_ignored(self, path):
        for pattern in self.ignored_routes:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
