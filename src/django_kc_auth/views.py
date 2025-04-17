import json
import logging

import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sessions.models import Session
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from keycloak import KeycloakError
from rest_framework import permissions
from rest_framework.views import APIView

from .keycloak_openid_config import (
    BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL,
    BACKCHANNEL_LOGOUT_EVENT_URL,
    REALM_URL,
    delete_session,
    get_active_devices,
    get_logout_url,
    keycloak_openid,
)
from .models import KeycloakSession, KeycloakUser
from .signals import post_keycloak_login

logger = logging.getLogger(__name__)


class LoginView(View):
    def get(self, request):
        """
        Handles user login by redirecting to the Keycloak authentication URL.

        The method constructs the Keycloak authentication URL with a redirect URI and state.
        The `state` parameter encodes the next URL the user should be redirected to after authentication.

        Parameters:
            request: The HTTP request object.

        Returns:
            HttpResponseRedirect: A response redirecting the user to the Keycloak authentication URL.
        """
        next_url = request.GET.get(
            "next", getattr(settings, "KC_SUCCESSFUL_LOGIN_REDIRECT", "/")
        )
        server_url = request.build_absolute_uri("/")[:-1]
        callback_url = f"{server_url}{reverse('kc_auth_callback')}"

        auth_url = keycloak_openid.auth_url(
            redirect_uri=callback_url,
            scope="openid email",
            state=urlsafe_base64_encode(next_url.encode("utf-8")),
        )
        logger.info("Redirecting user to Keycloak authentication URL")
        return redirect(auth_url)


class CallbackView(View):
    def get(self, request):
        """
        Processes the Keycloak callback after authentication.

        Parameters:
            request: The HTTP request object.

        Workflow:
            - Extracts `code` and `state` parameters from the request.
            - Decodes `state` to determine the redirection URL after login.
            - If no `code` is provided, redirects to the home or the state-defined URL.
            - Exchanges the authorization code for tokens via Keycloak.
            - Retrieves user information from Keycloak.
            - Authenticates and logs in the user.
            - Creates a Keycloak session record linked to the Django session.
            - Redirects the user to the state-defined URL or the home page.

        Returns:
            HttpResponseRedirect: Redirects to the appropriate URL based on the state or home page.
        """
        code = request.GET.get("code")
        state = request.GET.get("state")
        redirect_url = None

        if state:
            try:
                redirect_url = urlsafe_base64_decode(state).decode("ascii")
            except Exception:
                redirect_url = (
                    getattr(settings, "KC_SUCCESSFUL_LOGIN_REDIRECT", "home"),
                )
        print(redirect_url)
        redirect_url = redirect_url if redirect_url else "home"
        if not code:
            return redirect(redirect_url)

        callback_url = request.build_absolute_uri(request.path)

        try:
            token = keycloak_openid.token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=callback_url,
            )
            id_token = token.get("id_token")
            access_token = token.get("access_token")
            keycloak_session_id = token.get("session_state")

            user_info = keycloak_openid.userinfo(access_token)
        except KeycloakError:
            redirect_error_message = getattr(settings, "KC_ERROR_MESSAGES", {}).get(
                "redirect_error"
            )
            logger.error("Error redirecting user %s", callback_url)
            if redirect_error_message:
                messages.error(
                    request,
                    redirect_error_message,
                )
            return redirect(redirect_url)

        user = authenticate(request, user_info=user_info)
        if not user:
            login_failed_message = getattr(settings, "KC_ERROR_MESSAGES", {}).get(
                "login_failed"
            )
            logger.error("Login in Django failed for user %s", user_info.get("sub"))
            if login_failed_message:
                messages.error(
                    request,
                    login_failed_message,
                )
            return redirect(redirect_url)

        login(request, user)
        logger.info("User %s logged in successfully", user.username)

        request.session["id_token"] = id_token
        request.session["access_token"] = access_token

        try:
            KeycloakSession.objects.get_or_create(
                keycloak_session_id=keycloak_session_id,
                keycloak_user=KeycloakUser.objects.get(user=user),
                django_session=Session.objects.get(
                    session_key=request.session.session_key
                ),
            )
        except Exception as e:
            logger.error("Failed to create Keycloak session record: %s", e)

        post_keycloak_login.send(
            sender=self.__class__,
            request=request,
            user=user,
            access_token=access_token,
        )

        return redirect(redirect_url)


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        """
        Handles the logout process by invalidating the Django session and redirecting
        to the Keycloak logout URL or the application homepage.

        Parameters:
            request: The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to the Keycloak logout URL or the homepage.
        """
        server_url = request.build_absolute_uri("/")[:-1]
        post_logout_redirect_uri = (
            f"{server_url}{getattr(settings, 'KC_LOGOUT_REDIRECT', '/')}"
        )
        id_token = request.session.get("id_token")

        user = request.user.username
        logout(request)
        logger.info("%s logged out", user)

        if not id_token:
            return redirect(post_logout_redirect_uri)

        redirect_url = get_logout_url(id_token, post_logout_redirect_uri)
        logger.info("Redirecting %s to Keycloak logout URL", user)

        return redirect(redirect_url)


class RemoteLogoutView(LoginRequiredMixin, View):
    def post(self, request):
        """
        Invalidates a remote Keycloak session associated with the authenticated user.

        Parameters:
            request: The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to the referring page or home on failure.
        """
        session_id = request.POST.get("session_id") or json.loads(request.body).get(
            "session_id"
        )
        keycloak_user = KeycloakUser.objects.filter(user=request.user).first()
        if not keycloak_user:
            logger.error(
                "User with %s session not found.",
                session_id,
            )
            user_not_found_message = getattr(settings, "KC_ERROR_MESSAGES", {}).get(
                "user_not_found"
            )
            if user_not_found_message:
                messages.error(
                    request,
                    user_not_found_message,
                )
            return redirect(request.META.get("HTTP_REFERER", "/"))
        try:
            if keycloak_user.user == request.user:
                delete_session(session_id)
                logger.info(
                    "Successfully deleted Keycloak session: %s for user: %s",
                    session_id,
                    request.user.username,
                )
            else:
                raise KeycloakError("Users mismatch!")
        except KeycloakError as e:
            logger.error(
                "Failed to delete Keycloak session: %s for user: %s. Error: %s",
                session_id,
                request.user.username,
                str(e),
            )
            remote_logout_failed_message = getattr(
                settings, "KC_ERROR_MESSAGES", {}
            ).get("remote_logout_failed")
            if remote_logout_failed_message:
                messages.error(
                    request,
                    remote_logout_failed_message,
                )

        return redirect(request.META.get("HTTP_REFERER", "/"))


@method_decorator(csrf_exempt, name="dispatch")
class LogoutListenerView(View):
    def post(self, request):
        """
        Listens for Keycloak backchannel logout events and invalidates corresponding Django sessions.

        Parameters:
            request: The HTTP request object.

        Returns:
            JsonResponse: A success or failure response based on the processing result.
        """
        instance = jwt.JWT()
        logout_token = request.body.decode().split("=")[-1]
        logger.info("Received logout token from Keycloak.")

        try:
            logout_token = instance.decode(
                logout_token, settings.KC_VERIFYING_KEY, do_time_check=True
            )
            events = logout_token.get("events", {})
            iss = logout_token.get("iss", "")
            if (
                BACKCHANNEL_LOGOUT_EVENT_URL in events
                or BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL in events
            ) and REALM_URL == iss:

                sid = logout_token.get("sid")

                session_keys = KeycloakSession.objects.filter(
                    keycloak_session_id=sid
                ).values_list("django_session", flat=True)

                deleted_sessions = Session.objects.filter(
                    session_key__in=session_keys
                ).delete()
                logger.info(
                    "Deleted %d Django session(s) for Keycloak session ID: %s",
                    deleted_sessions[0],
                    sid,
                )

                return JsonResponse({"status": "success"})
            else:
                logger.warning("Invalid logout event or issuer mismatch")
                return JsonResponse(
                    {"status": "failure", "reason": "Invalid logout event"}, status=400
                )
        except Exception as e:
            logger.error("Unexpected error processing logout token: %s", str(e))
            return JsonResponse(
                {"status": "failure", "reason": "Unexpected error"}, status=500
            )


@login_required
def devices(request):
    """
    Fetches active sessions and devices for the logged-in user from Keycloak.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: Renders a template with session and device information.

    Raises:
        Http404: If the access token is not found in the user's session.
    """
    template_name = "devices.html"
    session_data = []
    error = False
    access_token = request.session.get("access_token")
    if not access_token:
        logger.warning("Access token not found for user: %s", request.user.username)
        raise Http404
    try:
        session_data = get_active_devices(access_token)
        logger.info("Retrieved devices for user: %s", request.user.username)
    except KeycloakError as e:
        logger.error(
            "Failed to fetch active devices for user %s: %s",
            request.user.username,
            str(e),
        )
        error = True
    return render(
        request, template_name, {"session_data": session_data, "error": error}
    )


class DevicesAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser)

    def get(self, request):
        """
        API endpoint that returns active sessions and devices for the logged-in user from Keycloak.

        Parameters:
            request: The HTTP request object.

        Returns:
            JsonResponse: JSON response containing session data or error information.
            - On success: Returns a JSON object with 'session_data' containing device information.
            - On error: Returns a JSON object with 'error' set to true and 'message' explaining the issue.

        HTTP Status Codes:
            200: Successfully retrieved device information.
            401: Access token not found.
            500: Error occurred while fetching device information from Keycloak.
        """
        session_data = []
        access_token = request.session.get("access_token")

        if not access_token:
            logger.warning("Access token not found for user: %s", request.user.username)
            return JsonResponse(
                {"error": True, "message": "Authentication required"}, status=401
            )

        try:
            session_data = get_active_devices(access_token)
            logger.info("Retrieved devices for user: %s", request.user.username)
            return JsonResponse({"session_data": session_data, "error": False})

        except KeycloakError as e:
            logger.error(
                "Failed to fetch active devices for user %s: %s",
                request.user.username,
                str(e),
            )
            return JsonResponse(
                {"error": True, "message": "Failed to retrieve device information"},
                status=500,
            )
