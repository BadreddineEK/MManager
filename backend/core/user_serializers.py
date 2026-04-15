"""
Serializers — Gestion des utilisateurs
========================================
UserListSerializer   : lecture (liste + détail), sans mot de passe
UserCreateSerializer : création avec mot de passe obligatoire
UserUpdateSerializer : modification (mot de passe optionnel, permissions granulaires)
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, _default_permissions


class UserListSerializer(serializers.ModelSerializer):
    """Lecture seule — utilisé pour GET list et GET detail."""

    mosque_name = serializers.CharField(source="mosque.name", read_only=True, default=None)
    effective_permissions = serializers.SerializerMethodField()
    username_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "username_display",
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

    def get_username_display(self, obj):
        raw = obj.username
        if obj.mosque_id and obj.mosque:
            prefix = f"{obj.mosque.schema_name}__"
            if raw.startswith(prefix):
                return raw[len(prefix):]
        return raw


class UserCreateSerializer(serializers.ModelSerializer):
    """Création d'un utilisateur — mot de passe obligatoire."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "password", "role", "is_active", "permissions_data",
        ]

    def validate_username(self, value):
        """Vérifie l'unicité du username (vérifié dans le schéma public)."""
        request = self.context.get("request")
        mosque = getattr(request, "mosque", None)
        if mosque:
            internal = f"{mosque.schema_name}__{value}"
            from django_tenants.utils import schema_context
            with schema_context("public"):
                if User.objects.filter(username=internal).exists():
                    raise serializers.ValidationError(
                        "Ce nom d'utilisateur existe déjà pour cette mosquée."
                    )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        if "permissions_data" not in validated_data:
            validated_data["permissions_data"] = _default_permissions()
        mosque = self.context["request"].mosque
        raw_username = validated_data.pop("username")
        internal_username = f"{mosque.schema_name}__{raw_username}" if mosque else raw_username
        user = User(**validated_data)
        user.username = internal_username
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
