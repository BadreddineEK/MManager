"""
Serializers core — Authentification JWT
=========================================
Enrichit les tokens JWT avec les données utilisateur utiles au frontend :
  - email, role, mosque_id, mosque_slug, username_display

Le serializer résout aussi le préfixage automatique du username :
  l'utilisateur tape "admin", le backend cherche "schema_name__admin"
  selon le tenant actif. Transparent pour le frontend.
"""
from django.db import connection
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MosqueTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Token JWT enrichi avec les informations mosquée.

    Payload supplémentaire :
        email           : adresse email de l'utilisateur
        role            : ADMIN | TRESORIER | ECOLE_MANAGER | ...
        mosque_id       : PK de la mosquée
        mosque_slug     : slug de la mosquée
        username_display: username sans le préfixe interne (affiché côté UI)
    """

    def validate(self, attrs):
        """
        Résolution automatique du username :
        Si l'utilisateur envoie "admin" et qu'on est dans le tenant "mosquee_testv1",
        on cherche "mosquee_testv1__admin" sans que le frontend ait à le savoir.
        """
        schema = connection.schema_name
        username_field = self.username_field
        raw_username = attrs.get(username_field, "")

        # Préfixer uniquement si on est dans un tenant (pas public)
        # et que le username n'est pas déjà préfixé
        if schema and schema != "public" and not raw_username.startswith(f"{schema}__"):
            attrs[username_field] = f"{schema}__{raw_username}"

        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["email"] = user.email
        token["role"] = user.role
        token["mosque_id"] = user.mosque_id
        token["mosque_slug"] = user.mosque.slug if user.mosque_id else None

        # username lisible sans préfixe interne
        raw = user.username
        if user.mosque_id and user.mosque and raw.startswith(f"{user.mosque.schema_name}__"):
            token["username_display"] = raw[len(f"{user.mosque.schema_name}__"):]
        else:
            token["username_display"] = raw

        return token
