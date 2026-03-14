"""
Serializers — Gestion des utilisateurs (étape 10)
===================================================
UserListSerializer   : lecture (liste + détail), sans mot de passe
UserCreateSerializer : création avec mot de passe obligatoire
UserUpdateSerializer : modification (mot de passe optionnel)
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User


class UserListSerializer(serializers.ModelSerializer):
    """Lecture seule — utilisé pour GET list et GET detail."""

    mosque_name = serializers.CharField(source="mosque.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "mosque_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """Création d'un utilisateur — mot de passe obligatoire."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Cet email est déjà utilisé.")],
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "role", "is_active"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # Rattacher à la mosquée de l'admin qui crée
        mosque = self.context["request"].mosque  # injecté par get_mosque() dans la vue
        user = User(**validated_data)
        user.mosque = mosque
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Modification — mot de passe optionnel."""

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "is_active", "password"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
