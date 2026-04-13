import re
from rest_framework import serializers


class RegisterMosqueSerializer(serializers.Serializer):
    mosque_name    = serializers.CharField(max_length=200)
    slug           = serializers.SlugField(max_length=63)
    timezone       = serializers.CharField(max_length=50, default='Europe/Paris')
    admin_username = serializers.CharField(max_length=150)
    admin_email    = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, write_only=True)
    base_domain    = serializers.CharField(max_length=200, default='nidham.local')

    def validate_slug(self, value):
        from core.models import Mosque
        value = value.lower().strip()
        RESERVED = {'admin', 'api', 'www', 'mail', 'static', 'media', 'public', 'nidham', 'superadmin'}
        if value in RESERVED:
            raise serializers.ValidationError(f"'{value}' est un slug reserve.")
        if len(value) > 1 and not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', value):
            raise serializers.ValidationError('Slug invalide: lettres minuscules, chiffres, tirets.')
        if Mosque.objects.filter(slug=value).exists():
            raise serializers.ValidationError(f"Le slug '{value}' est deja utilise.")
        schema = value.replace('-', '_')
        if Mosque.objects.filter(schema_name=schema).exists():
            raise serializers.ValidationError('Ce schema existe deja.')
        return value

    def validate_admin_username(self, value):
        return value.strip()
