from django.urls import include, path
from django.http import HttpResponse


def home(request):
    return HttpResponse("home")


urlpatterns = [
    path("", include("django_kc_auth.urls")),
    path("home/", home, name="home"),
]
