from django.conf import settings
from django.urls import path

from . import views

urlpatterns = [
    path(
        getattr(settings, "KC_LOGIN_URL", "login/"),
        views.LoginView.as_view(),
        name="kc_auth_login",
    ),
    path(
        getattr(settings, "KC_CALLBACK_URL", "callback/"),
        views.CallbackView.as_view(),
        name="kc_auth_callback",
    ),
    path(
        getattr(settings, "KC_LOGOUT_URL", "logout/"),
        views.LogoutView.as_view(),
        name="kc_auth_logout",
    ),
    path(
        getattr(settings, "KC_REMOTE_LOGOUT_URL", "remote-logout/"),
        views.RemoteLogoutView.as_view(),
        name="kc_auth_remote-logout",
    ),
    path(
        getattr(settings, "KC_LOGOUT_LISTENER_URL", "logout-listener/"),
        views.LogoutListenerView.as_view(),
        name="kc_auth_logout-listener",
    ),
    path(
        getattr(settings, "KC_DEVICES_URL", "devices/"),
        views.devices,
        name="kc_auth_devices",
    ),
    path(
        getattr(settings, "KC_DEVICES_API_URL", "api/devices/"),
        views.DevicesAPIView.as_view(),
        name="kc_auth_api_devices",
    ),
]
