"""
Serializers core — Authentification JWT
=========================================
Enrichit les tokens JWT avec les données utilisateur utiles au frontend :
  - email, role, mosque_id, mosque_slug

Ainsi le client n'a pas besoin d'un appel /me/ supplémentaire.
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MosqueTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Token JWT enrichi avec les informations mosquée.

    Payload supplémentaire :
        email      : adresse email de l'utilisateur
        role       : ADMIN | TRESORIER | ECOLE_MANAGER | ""
        mosque_id  : PK de la mosquée (null pour superuser sans mosquée)
        mosque_slug: slug de la mosquée (null pour superuser sans mosquée)
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Données injectées dans le payload JWT
        token["email"] = user.email
        token["role"] = user.role
        token["mosque_id"] = user.mosque_id
        token["mosque_slug"] = user.mosque.slug if user.mosque_id else None

        return token
