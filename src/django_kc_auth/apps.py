from django.apps import AppConfig


class KeycloakAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_kc_auth"

    def ready(self):
        import logging

        import jwt
        from django.conf import settings

        from .keycloak_openid_config import keycloak_openid

        logger = logging.getLogger(__name__)

        try:
            keys = keycloak_openid.certs()["keys"]
            jwt_dict = next((key for key in keys if key.get("use") == "sig"), None)
            verifying_key = jwt.jwk_from_dict(jwt_dict)
            settings.KC_VERIFYING_KEY = verifying_key
            logger.info("Keycloak verifying key set up.")
        except Exception:
            logger.error("Initialization failed.", exc_info=True)
