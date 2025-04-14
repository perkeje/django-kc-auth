from django.conf import settings
from keycloak import KeycloakOpenID, KeycloakOpenIDConnection
from keycloak.exceptions import (
    KeycloakDeleteError,
    KeycloakGetError,
    raise_error_from_response,
)

BACKCHANNEL_LOGOUT_EVENT_URL = "http://schemas.openid.net/event/backchannel-logout"
BACKCHANNEL_LOGOUT_EVENT_HTTPS_URL = (
    "https://schemas.openid.net/event/backchannel-logout"
)
REALM_URL = f"{settings.KC_SERVER_URL}/realms/{settings.KC_REALM}"


keycloak_connection = KeycloakOpenIDConnection(
    server_url=settings.KC_SERVER_URL,
    realm_name=settings.KC_REALM,
    user_realm_name="master",
    username="admin",
    password="admin",
    verify=True,
)

keycloak_openid = KeycloakOpenID(
    server_url=settings.KC_SERVER_URL,
    realm_name=settings.KC_REALM,
    client_id=settings.KC_CLIENT_ID,
    client_secret_key=settings.KC_CLIENT_SECRET,
)


def delete_session(session_id):
    path = "admin/realms/{realm-name}/sessions/{session_id}"
    params_path = {
        "realm-name": keycloak_connection.realm_name,
        "session_id": session_id,
    }
    data_raw = keycloak_connection.raw_delete(path.format(**params_path))
    return raise_error_from_response(data_raw, KeycloakDeleteError)


def get_logout_url(id_token, post_logout_redirect_uri):
    return (
        f"{REALM_URL}/protocol/openid-connect/logout"
        f"?id_token_hint={id_token}"
        f"&post_logout_redirect_uri={post_logout_redirect_uri}"
        f"&client_id={settings.KC_CLIENT_ID}"
    )


def get_active_devices(access_token):
    connection = keycloak_openid.connection
    path = "realms/{realm-name}/account/sessions/devices"
    orig_bearer = connection.headers.get("Authorization")
    connection.add_param_headers("Authorization", "Bearer " + access_token)
    connection.add_param_headers("Content-Type", "application/json")

    params_path = {"realm-name": keycloak_openid.realm_name}
    data_raw = connection.raw_get(path.format(**params_path))
    (
        connection.add_param_headers("Authorization", orig_bearer)
        if orig_bearer is not None
        else connection.del_param_headers("Authorization")
    )
    return raise_error_from_response(data_raw, KeycloakGetError)
