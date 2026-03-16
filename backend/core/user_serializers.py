"""
Serializers — Gestion des utilisateurs
========================================
UserListSerializer   : lecture (liste + détail), sans mot de passe
UserCreateSerializer : création avec mot de passe obligatoire
UserUpdateSerializer : modification (mot de passe optionnel, permissions granulaires)
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User, _default_permissions


class UserListSerializer(serializers.ModelSerializer):
    """Lecture seule — utilisé pour GET list et GET detail."""

    mosque_name = serializers.CharField(source="mosque.name", read_only=True, default=None)
    effective_permissions = serializers.SerializerMethodField()

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
            "permissions_data",
            "effective_permissions",
        ]
        read_only_fields = fields

    def get_effective_permissions(self, obj):
        return obj.get_effective_permissions()


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
        fields = [
            "username", "email", "first_name", "last_name",
            "password", "role", "is_active", "permissions_data",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        if "permissions_data" not in validated_data:
            validated_data["permissions_data"] = _default_permissions()
        mosque = self.context["request"].mosque
        user = User(**validated_data)
        user.mosque = mosque
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Modification — mot de passe optionnel, permissions granulaires."""

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name",
            "role", "is_active", "password", "permissions_data",
        ]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
