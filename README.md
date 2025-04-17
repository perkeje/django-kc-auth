# Django Keycloak Authentication (django-kc-auth)
A Django package for seamless integration with Keycloak authentication services.

## Overview
Django Keycloak Authentication provides a complete solution for integrating Keycloak identity and access management with Django applications. This package handles user authentication, session management, and device tracking while providing customizable URLs and error messages.
## Requirements
- Python 3.10+
- Django 5.0.1+
- A running Keycloak server with a configured realm and client

## Installation

```shell 
pip install django-kc-auth
```

## Quick Setup

1. **Add to `INSTALLED_APPS` in ``settings.py``**:

```python
INSTALLED_APPS = [
    # ...
    'django_kc_auth',
    # ...
]
```
2. **Configure Keycloak settings in your Django ``settings.py``**:

```python
# Required Keycloak settings
KC_SERVER_URL = 'https://your-keycloak-server/auth'
KC_REALM = 'your-realm'
KC_CLIENT_ID = 'your-client-id'
KC_CLIENT_SECRET = 'your-client-secret'
# KC_VERIFYING_KEY is set programmatically during app initialization
```
3. **Run migrations**:

```shell
python manage.py migrate
```
4. **Include URLs in your project's `urls.py`**:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("kc/", include("django_kc_auth.urls")),
    # ...
]
```
## URL Configuration

**The package provides the following default URL paths:**
|Default Path|View|URL Name|
|:---:|:---:|:---:|
|/login/|LoginView|kc_auth_login|
|/callback/|CallbackView|kc_auth_callback|
|/logout/|LogoutView|kc_auth_logout|
|/remote-logout/|RemoteLogoutView|kc_auth_remote-logout|
|/logout-listener/|LogoutListenerView|kc_auth_logout-listener|
|/devices/|devices|kc_auth_devices|
|/api/devices/|DevicesAPIView|kc_auth_api_devices|

## Backend
Add this backend to your `AUTHENTICATION_BACKENDS`. You can also use your own adaptaion. Be sure to check how it is implemented here to override it.
```python
AUTHENTICATION_BACKENDS = [
    "django_kc_auth.backends.KeycloakBackend",
    # ... other backends
]
```
Also set default groups in settings if using default backend.
```python
KC_ROLES = [
    "employees",
    "admins",
    # ...
]
```


## Customization Options
**URL Paths**

You can customize URL paths in your `settings.py`:

```python
# URL path customization
KC_LOGIN_URL = "custom-login/"
KC_CALLBACK_URL = "custom-callback/"
KC_LOGOUT_URL = "custom-logout/"
KC_REMOTE_LOGOUT_URL = "custom-remote-logout/"
KC_LOGOUT_LISTENER_URL = "custom-logout-listener/"
KC_DEVICES_URL = "custom-devices/"
KC_DEVICES_API_URL = "custom-api/devices/"
```
## Redirection Settings

**Configure where users are redirected after login/logout:**

```python
# Redirection settings
KC_SUCCESSFUL_LOGIN_REDIRECT = "dashboard"  # Default: "home"
KC_LOGOUT_REDIRECT = "landing-page"         # Default: "home"
```

## Error Messages

**Customize error messages displayed to users:**

```python
# Custom error messages
KC_ERROR_MESSAGES = {
    "redirect_error": "There was a problem with the authentication service. Please try again.",
    "login_failed": "Login failed. Please check your credentials and try again.",
    "user_not_found": "User account not found.",
    "remote_logout_failed": "Failed to log out from remote session.",
}
```
## Silent Authentication

Silent authentication allows automatic login for users with active Keycloak sessions in other applications.

**To enable this feature:**

1. Add the Keycloak middleware to your middlewares:

```python
MIDDLEWARE = [
    #... previous, needs to go after:
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_kc_auth.middleware.AutoKeycloakLoginMiddleware",
    # ...other
]
```
2. Configure silent login settings (optional):

```python
# Silent login configuration
KC_SILENT_LOGIN_ALLOWED_ATTEMPTS = 5  # Maximum number of silent login attempts
KC_SILENT_LOGIN_TIMEOUT_SECONDS = 3   # Timeout between silent login attempts
KC_SILENT_LOGOUT_IGNORED_ROUTES = [   # Routes to ignore for silent login
    "/api/health-check/",
    "/static/*",
]
```
3. Soft logout
If you are using soft logout(logout only from django app but not from keycloak), you should set `request.session["soft_logout"] = True` after logging out.
```python
class SoftLogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        request.session["soft_logout"] = True
        return redirect("home")

```
## Devices
You can fetch devices and applications attached to current session with devices. There are API call and template return options. To use template option you need to put your `devices.html` template inside your root `TEMPLATE` directory.
## Post logout
You can use your custom post logout logic catching the signal.<br>
Example:
```python
from django_kc_auth.signals import post_keycloak_login
from django.dispatch import receiver

@receiver(post_keycloak_login)
def handle_post_login(sender, request, user, access_token, **kwargs):
    # Your custom post-login logic here
    user.profile.last_login_source = 'keycloak'
    user.profile.save()
    
    # You can also perform other actions like:
    # - Update user metadata
    # - Sync user permissions from Keycloak roles
    # - Record login analytics
    # - Set up user-specific session data
```
## License
MIT License
