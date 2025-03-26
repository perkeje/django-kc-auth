from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path(settings.KC_LOGIN_URL or "/login", views.LoginView.as_view(), name="login"),
    path("callback/", views.CallbackView.as_view(), name="callback"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("remote-logout/", views.RemoteLogoutView.as_view(), name="remote-logout"),
    path(
        "logout-listener/",
        views.LogoutListenerView.as_view(),
        name="logout-listener",
    ),
    path("devices/", views.devices, name="devices"),
]
