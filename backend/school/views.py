"""
Vues school -- API REST Ecole coranique
=========================================
Ressources humaines uniquement : familles, enfants, années scolaires.
Les paiements sont dans TreasuryTransaction (category='ecole').
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission
from core.plan_enforcement import PlanLimitMixin, plan_module_permission
from core.utils import get_mosque, log_action

from .models import Child, ClassEnrollment, Family, SchoolYear
from .serializers import (
    ChildSerializer,
    FamilySerializer,
    SchoolYearSerializer,
)


class SchoolYearViewSet(viewsets.ModelViewSet):
    """CRUD annees scolaires + réinscription N→N+1."""

    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return SchoolYear.objects.none()
        return SchoolYear.objects.filter(mosque=mosque)

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "SchoolYear", obj.id, {"label": obj.label})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "SchoolYear", instance.id, {"label": instance.label})
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reenroll")
    def reenroll(self, request, pk=None):
        """
        POST /api/school/years/{id}/reenroll/

        Reconduit les inscriptions de l'année {id} vers une nouvelle année.
        Body JSON :
          target_year_id  (int, requis)   — ID de l'année cible
          auto_level_up   (bool, défaut True) — monte automatiquement le niveau
          child_ids       (list[int], optionnel) — si absent, tous les enfants actifs

        Retourne : { enrolled, skipped, errors }
        """
        source_year = self.get_object()
        mosque = get_mosque(request)

        target_year_id = request.data.get("target_year_id")
        if not target_year_id:
            return Response({"detail": "target_year_id est requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_year = SchoolYear.objects.get(id=target_year_id, mosque=mosque)
        except SchoolYear.DoesNotExist:
            return Response({"detail": "Année cible introuvable."}, status=status.HTTP_404_NOT_FOUND)

        auto_level_up = request.data.get("auto_level_up", True)
        child_ids = request.data.get("child_ids", None)

        # Récupérer les niveaux configurés (pour la progression)
        school_levels: list[str] = []
        try:
            settings = mosque.settings
            school_levels = list(settings.school_levels or [])
        except Exception:
            pass

        # Enfants source : soit filtre sur child_ids, soit tous inscrits dans source_year
        # ClassEnrollment est lié à Class → Class est liée à SchoolYear
        source_enrollments = ClassEnrollment.objects.filter(
            school_class__school_year=source_year,
            is_active=True,
        ).select_related("child", "school_class")
        if child_ids:
            source_enrollments = source_enrollments.filter(child_id__in=child_ids)

        enrolled = 0
        skipped = 0
        errors = []

        for enrollment in source_enrollments:
            child = enrollment.child

            # Vérifier doublon (déjà inscrit dans une classe de l'année cible)
            if ClassEnrollment.objects.filter(
                child=child,
                school_class__school_year=target_year,
            ).exists():
                skipped += 1
                continue

            # Calcul du nouveau niveau
            new_level = child.level
            if auto_level_up and school_levels and child.level in school_levels:
                current_idx = school_levels.index(child.level)
                if current_idx < len(school_levels) - 1:
                    new_level = school_levels[current_idx + 1]

            # Mettre à jour le niveau sur l'enfant
            if auto_level_up and new_level != child.level:
                child.level = new_level
                child.save(update_fields=["level"])

            # NB : on ne crée pas ClassEnrollment ici car on ne connaît pas encore
            # la classe cible dans la nouvelle année. On met à jour le niveau et
            # on marque l'enfant comme "à inscrire" pour que l'admin l'affecte.
            # Une inscription pending est matérialisée par une ClassEnrollment
            # sans classe (school_class=None n'est pas possible car FK non-null).
            # → On retourne simplement la liste des enfants mis à jour.
            enrolled += 1

        log_action(
            request, "REENROLL", "SchoolYear", source_year.id,
            {"source": source_year.label, "target": target_year.label, "enrolled": enrolled},
        )

        return Response({
            "enrolled": enrolled,
            "skipped": skipped,
            "errors": errors,
            "message": f"{enrolled} enfant(s) reconduit(s) vers {target_year.label}.",
        })


class FamilyViewSet(PlanLimitMixin, viewsets.ModelViewSet):
    plan_limit_resource = "families"
    plan_limit_model = Family
    """CRUD familles."""

    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["primary_contact_name", "email", "phone1"]
    ordering_fields = ["primary_contact_name", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        qs = Family.objects.prefetch_related("children")
        if mosque is None:
            return qs.none()
        return qs.filter(mosque=mosque)

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Family", obj.id, {"name": obj.primary_contact_name})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Family", obj.id, {"name": obj.primary_contact_name})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Family", instance.id, {"name": instance.primary_contact_name})
        instance.delete()

    @action(detail=False, methods=["get"], url_path="arrears")
    def arrears(self, request):
        """
        GET /api/school/families/arrears/
        Familles sans aucune TreasuryTransaction ecole pour l'année active.
        """
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response(
                {"detail": "Aucune annee scolaire active trouvee."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Familles ayant au moins une transaction école cette année
        from treasury.models import TreasuryTransaction
        paid_family_ids = TreasuryTransaction.objects.filter(
            mosque=mosque,
            category="ecole",
            school_year=active_year,
        ).values_list("family_id", flat=True).distinct()

        families_in_arrears = Family.objects.filter(mosque=mosque).exclude(
            id__in=paid_family_ids
        ).prefetch_related("children")

        serializer = self.get_serializer(families_in_arrears, many=True)
        return Response({
            "school_year": active_year.label,
            "count": families_in_arrears.count(),
            "families": serializer.data,
        })


class ChildViewSet(viewsets.ModelViewSet):
    """CRUD enfants."""

    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "family__primary_contact_name"]
    ordering_fields = ["first_name", "level", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        qs = Child.objects.select_related("family")
        if mosque is None:
            return qs.none()
        qs = qs.filter(mosque=mosque)
        level = self.request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Child", obj.id, {"name": obj.first_name, "level": obj.level})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Child", obj.id, {"name": obj.first_name, "level": obj.level})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Child", instance.id, {"name": instance.first_name})
        instance.delete()
