"""
Vues Settings + Onboarding -- configuration mosquee
====================================================
GET  /api/settings/         -> lire la config (ADMIN)
PUT  /api/settings/         -> modifier la config (ADMIN)
POST /api/settings/onboarding/ -> premiere configuration (ADMIN, superuser)
GET  /api/settings/status/  -> verifier si la mosquee est configuree (auth requise)
"""
import re

from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminRole
from core.utils import get_mosque

from .models import Mosque, MosqueSettings
from .settings_serializer import MosqueSettingsSerializer, OnboardingSerializer


class SettingsView(APIView):
    """
    GET  /api/settings/  -> retourne MosqueSettings de la mosquee courante
    PUT  /api/settings/  -> met a jour MosqueSettings (champs partiels OK)
    ADMIN uniquement.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response(
                {"detail": "Aucune mosquee configuree. Utilisez /api/settings/onboarding/"},
                status=status.HTTP_404_NOT_FOUND,
            )
        settings_obj, _ = MosqueSettings.objects.get_or_create(
            mosque=mosque,
            defaults={
                "school_levels": ["NP", "N1", "N2", "N3", "N4", "N5", "N6"],
                "school_fee_default": 0,
                "school_fee_mode": "annual",
                "membership_fee_amount": 0,
                "membership_fee_mode": "per_person",
                "active_school_year_label": "",
            },
        )
        serializer = MosqueSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def put(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response(
                {"detail": "Aucune mosquee configuree."},
                status=status.HTTP_404_NOT_FOUND,
            )
        settings_obj, _ = MosqueSettings.objects.get_or_create(
            mosque=mosque,
            defaults={
                "school_levels": ["NP", "N1", "N2", "N3", "N4", "N5", "N6"],
                "school_fee_default": 0,
                "school_fee_mode": "annual",
                "membership_fee_amount": 0,
                "membership_fee_mode": "per_person",
                "active_school_year_label": "",
            },
        )

        # Mise a jour du nom / timezone de la mosquee si fournis
        mosque_name = request.data.get("mosque_name")
        mosque_timezone = request.data.get("mosque_timezone")
        if mosque_name:
            mosque.name = mosque_name
            mosque.save(update_fields=["name"])
        if mosque_timezone:
            mosque.timezone = mosque_timezone
            mosque.save(update_fields=["timezone"])

        # Mise a jour des settings (on exclut les champs read-only de la mosquee)
        settings_data = {k: v for k, v in request.data.items()
                         if k not in ("mosque_name", "mosque_slug", "mosque_timezone")}
        serializer = MosqueSettingsSerializer(
            settings_obj, data=settings_data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()

        # Recharger pour avoir les champs mosque_* a jour
        settings_obj.refresh_from_db()
        return Response(MosqueSettingsSerializer(settings_obj).data)


class OnboardingView(APIView):
    """
    POST /api/settings/onboarding/
    Cree la mosquee + ses settings en une seule requete.
    Accessible au superuser ou a un ADMIN sans mosquee encore configuree.
    Idempotent : si la mosquee existe deja, met a jour.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Seul superuser ou ADMIN peut onboarder
        user = request.user
        if not (user.is_superuser or user.role == "ADMIN"):
            return Response(
                {"detail": "Seul un ADMIN peut effectuer l'onboarding."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        mosque_name = data["mosque_name"]
        base_slug = slugify(mosque_name)

        # Mosquee existante ou creation
        mosque = get_mosque(request)
        if mosque is None:
            # Generer un slug unique
            slug = base_slug
            counter = 1
            while Mosque.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            mosque = Mosque.objects.create(
                name=mosque_name,
                slug=slug,
                timezone=data.get("mosque_timezone", "Europe/Paris"),
            )
            # Rattacher l'user a la nouvelle mosquee
            if not user.is_superuser:
                user.mosque = mosque
                user.save(update_fields=["mosque"])
        else:
            mosque.name = mosque_name
            mosque.timezone = data.get("mosque_timezone", mosque.timezone)
            mosque.save(update_fields=["name", "timezone"])

        # Creer ou mettre a jour les settings
        MosqueSettings.objects.update_or_create(
            mosque=mosque,
            defaults={
                "school_levels": data.get("school_levels", ["NP", "N1", "N2", "N3", "N4", "N5", "N6"]),
                "school_fee_default": data.get("school_fee_default", 0),
                "school_fee_mode": data.get("school_fee_mode", "annual"),
                "membership_fee_amount": data.get("membership_fee_amount", 0),
                "membership_fee_mode": data.get("membership_fee_mode", "per_person"),
                "active_school_year_label": data.get("active_school_year_label", ""),
            },
        )

        settings_obj = MosqueSettings.objects.get(mosque=mosque)
        return Response(
            MosqueSettingsSerializer(settings_obj).data,
            status=status.HTTP_201_CREATED,
        )


class SettingsStatusView(APIView):
    """
    GET /api/settings/status/
    Retourne si la mosquee de l'utilisateur est configuree.
    Utilise par le frontend pour decider si onboarding est necessaire.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({
                "configured": False,
                "mosque": None,
            })
        has_settings = MosqueSettings.objects.filter(mosque=mosque).exists()
        return Response({
            "configured": has_settings,
            "mosque": {
                "id": mosque.id,
                "name": mosque.name,
                "slug": mosque.slug,
            },
        })
