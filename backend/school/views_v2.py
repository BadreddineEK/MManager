"""
Views school v2 — Classes, Appel, Coran, Bulletins
====================================================
GET/POST /api/school/classes/
GET/POST /api/school/classes/{id}/enroll/
POST     /api/school/sessions/          — creer une seance d'appel
POST     /api/school/sessions/{id}/submit/  — soumettre l'appel
GET      /api/school/sessions/{id}/     — detail seance + presences
GET      /api/school/children/{id}/quran/     — progression Coran enfant
PUT      /api/school/children/{id}/quran/{surah}/
GET      /api/school/children/{id}/absences/  — stats absences
GET/POST /api/school/periods/           — periodes d'appreciation
POST     /api/school/periods/{id}/grades/  — saisir les appreciations
GET      /api/school/children/{id}/bulletin/{period_id}/  — bulletin
"""
import logging
from datetime import date

from django.db.models import Count, Q
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission
from core.plan_enforcement import plan_module_permission
from core.utils import get_mosque, log_action

from .models import (
    Attendance,
    AttendanceSession,
    Child,
    Class,
    ClassEnrollment,
    Family,
    Grade,
    GradePeriod,
    QuranProgress,
    SchoolYear,
    SURAH_CHOICES,
)
from .serializers_v2 import (
    AttendanceSerializer,
    AttendanceSessionSerializer,
    AttendanceSessionDetailSerializer,
    ClassEnrollmentSerializer,
    ClassSerializer,
    GradeSerializer,
    GradePeriodSerializer,
    QuranProgressSerializer,
)

logger = logging.getLogger("school")


def _mosque(request):
    return get_mosque(request)


def _send_absence_alert(child, threshold, school_class, mosque):
    """
    Envoie un email d'alerte a la famille quand un enfant atteint
    le seuil d'absences consecutives configure dans MosqueSettings.
    """
    from core.notification_views import _get_smtp_settings, _send_email

    smtp_cfg = _get_smtp_settings(mosque)
    if not smtp_cfg or not smtp_cfg.get("host"):
        logger.info(
            "ABSENCE ALERT: SMTP non configure pour %s — email non envoye",
            mosque.name,
        )
        return

    family = child.family
    to_email = family.email if family and family.email else None
    if not to_email:
        logger.info(
            "ABSENCE ALERT: pas d'email pour famille de %s — alerte non envoyee",
            child.first_name,
        )
        return

    subject = "[{}] Alerte absence — {}".format(mosque.name, child.first_name)
    html_body = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #e74c3c;">&#9888;&#65039; Alerte absence</h2>
      <p>Bonjour,</p>
      <p>Nous vous informons que <strong>{}</strong> a accumulé
      <strong>{} absences consécutives</strong> dans la classe
      <strong>{}</strong>.</p>
      <p>Merci de prendre contact avec nous si vous souhaitez nous informer d'une
      situation particulière.</p>
      <p style="margin-top: 30px;">Cordialement,<br>
      <strong>{}</strong></p>
    </div>
    """.format(child.first_name, threshold, school_class.name, mosque.name)

    ok, err = _send_email(smtp_cfg, to_email, subject, html_body)
    if ok:
        logger.info(
            "ABSENCE ALERT EMAIL: envoye a %s pour %s (%d absences)",
            to_email, child.first_name, threshold,
        )
    else:
        logger.error(
            "ABSENCE ALERT EMAIL ERREUR: %s — %s", to_email, err,
        )

# ─────────────────────────────────────────────────────────────────────────────
# Classes
# ─────────────────────────────────────────────────────────────────────────────

class ClassViewSet(viewsets.ModelViewSet):
    """
    CRUD classes.
    GET  /api/school/classes/
    POST /api/school/classes/
    """
    serializer_class = ClassSerializer
    permission_classes = [
        IsAuthenticated,
        HasMosquePermission,
        plan_module_permission("school_basic"),
    ]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "level_code"]
    ordering_fields = ["order", "name"]

    def get_queryset(self):
        mosque = _mosque(self.request)
        if mosque is None:
            return Class.objects.none()
        qs = Class.objects.filter(mosque=mosque).select_related("teacher", "school_year")
        year_id = self.request.query_params.get("year")
        if year_id:
            qs = qs.filter(school_year_id=year_id)
        else:
            # Par defaut : annee active
            active = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
            if active:
                qs = qs.filter(school_year=active)
        return qs

    def get_permissions(self):
        """TEACHER peut lire les classes mais pas les creer/modifier/supprimer."""
        write_actions = ("create", "update", "partial_update", "destroy")
        if self.action in write_actions:
            role = getattr(self.request.user, "role", "")
            if role == "TEACHER":
                from rest_framework.exceptions import PermissionDenied
                self.permission_denied(self.request, message="Les professeurs ne peuvent pas modifier les classes.")
        return super().get_permissions()

    def perform_create(self, serializer):
        mosque = _mosque(self.request)
        obj = serializer.save(mosque=mosque)
        log_action(self.request, "CREATE", "Class", obj.id, {"name": obj.name})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Class", obj.id, {"name": obj.name})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Class", instance.id, {"name": instance.name})
        instance.delete()

    @action(detail=True, methods=["get", "post"], url_path="enroll")
    def enroll(self, request, pk=None):
        """
        GET  /api/school/classes/{id}/enroll/ — liste des inscrits
        POST /api/school/classes/{id}/enroll/ — inscrire un enfant
              body: {"child_id": 42, "notes": "..."}
        """
        school_class = self.get_object()
        mosque = _mosque(request)

        if request.method == "GET":
            enrollments = ClassEnrollment.objects.filter(
                school_class=school_class, is_active=True
            ).select_related("child__family")
            s = ClassEnrollmentSerializer(enrollments, many=True)
            return Response({
                "class": school_class.name,
                "count": enrollments.count(),
                "students": s.data,
            })

        # POST — inscrire
        child_id = request.data.get("child_id")
        if not child_id:
            return Response({"error": "child_id requis."}, status=400)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        enrollment, created = ClassEnrollment.objects.get_or_create(
            school_class=school_class,
            child=child,
            defaults={"mosque": mosque, "notes": request.data.get("notes", "")},
        )
        if not created:
            enrollment.is_active = True
            enrollment.save()
        log_action(request, "CREATE", "ClassEnrollment", enrollment.id,
                   {"child": child.first_name, "class": school_class.name})
        return Response(ClassEnrollmentSerializer(enrollment).data, status=201 if created else 200)

    @action(detail=True, methods=["delete"], url_path="enroll/(?P<child_id>[0-9]+)")
    def unenroll(self, request, pk=None, child_id=None):
        """DELETE /api/school/classes/{id}/enroll/{child_id}/ — desinscrire."""
        school_class = self.get_object()
        mosque = _mosque(request)
        try:
            enrollment = ClassEnrollment.objects.get(
                school_class=school_class, child_id=child_id, mosque=mosque
            )
            enrollment.is_active = False
            enrollment.save()
            log_action(request, "UPDATE", "ClassEnrollment", enrollment.id, {"status": "unenrolled"})
            return Response({"detail": "Desinscrit."})
        except ClassEnrollment.DoesNotExist:
            return Response({"error": "Inscription introuvable."}, status=404)


# ─────────────────────────────────────────────────────────────────────────────
# Appel / Presences
# ─────────────────────────────────────────────────────────────────────────────

class AttendanceSessionViewSet(viewsets.ModelViewSet):
    """
    Seances d'appel.
    POST /api/school/sessions/          — nouvelle seance
    GET  /api/school/sessions/          — historique
    GET  /api/school/sessions/{id}/     — detail + presences
    POST /api/school/sessions/{id}/submit/ — soumettre l'appel
    """
    serializer_class = AttendanceSessionSerializer
    permission_classes = [
        IsAuthenticated,
        HasMosquePermission,
        plan_module_permission("school_basic"),
    ]

    def get_queryset(self):
        mosque = _mosque(self.request)
        if mosque is None:
            return AttendanceSession.objects.none()
        qs = AttendanceSession.objects.filter(mosque=mosque).select_related("school_class")
        class_id = self.request.query_params.get("class")
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        return qs

    def retrieve(self, request, *args, **kwargs):
        """Detail : seance + liste presences."""
        session = self.get_object()
        s = AttendanceSessionDetailSerializer(session, context={"request": request})
        return Response(s.data)

    def perform_create(self, serializer):
        mosque = _mosque(self.request)
        session = serializer.save(mosque=mosque, created_by=self.request.user)
        # Auto-creer les lignes de presence pour tous les eleves inscrits
        enrollments = ClassEnrollment.objects.filter(
            school_class=session.school_class, is_active=True
        )
        Attendance.objects.bulk_create([
            Attendance(session=session, child=e.child, status=Attendance.STATUS_PRESENT)
            for e in enrollments
        ], ignore_conflicts=True)
        log_action(self.request, "CREATE", "AttendanceSession", session.id,
                   {"class": session.school_class.name, "date": str(session.date)})

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """
        POST /api/school/sessions/{id}/submit/
        body: {"attendances": [{"child_id": 1, "status": "absent", "note": "..."}, ...]}
        Ecrase les presences de la seance.
        """
        session = self.get_object()
        data = request.data.get("attendances", [])
        if not data:
            return Response({"error": "attendances[] requis."}, status=400)

        # Batch upsert
        updates = 0
        errors = []
        for item in data:
            child_id = item.get("child_id")
            att_status = item.get("status", Attendance.STATUS_PRESENT)
            note = item.get("note", "")
            if att_status not in dict(Attendance.STATUS_CHOICES):
                errors.append(f"Statut invalide: {att_status}")
                continue
            updated = Attendance.objects.filter(
                session=session, child_id=child_id
            ).update(status=att_status, note=note)
            if not updated:
                errors.append(f"Enfant {child_id} non trouve dans cette seance.")
            else:
                updates += 1

        log_action(request, "UPDATE", "AttendanceSession", session.id,
                   {"submitted": updates, "errors": len(errors)})

        # Verifier les eleves avec N absences consecutives
        self._check_absence_alerts(session)

        return Response({
            "updated": updates,
            "errors": errors,
            "detail": f"Appel enregistre : {updates} eleves mis a jour.",
        })

    def _check_absence_alerts(self, session):
        """
        Envoie une alerte email si un eleve depasse le seuil d'absences consecutives.
        (Seuil configurable dans MosqueSettings — defaut : 3)
        """
        try:
            from core.models import MosqueSettings
            settings_obj = MosqueSettings.objects.filter(mosque=session.mosque).first()
            threshold = getattr(settings_obj, "absence_alert_threshold", 3) if settings_obj else 3
        except Exception:
            threshold = 3

        absences = Attendance.objects.filter(
            session=session,
            status__in=[Attendance.STATUS_ABSENT, Attendance.STATUS_LATE],
        ).select_related("child__family")

        for att in absences:
            child = att.child
            # Compter les absences consecutives recentes
            recent = Attendance.objects.filter(
                child=child,
                session__school_class=session.school_class,
                status__in=[Attendance.STATUS_ABSENT],
            ).order_by("-session__date")[:threshold]

            if recent.count() >= threshold and all(
                a.status == Attendance.STATUS_ABSENT for a in recent
            ):
                logger.warning(
                    "ABSENCE ALERT: %s a %d absences consecutives (classe %s)",
                    child.first_name, threshold, session.school_class.name,
                )
                try:
                    _send_absence_alert(child, threshold, session.school_class, session.mosque)
                except Exception as exc:
                    logger.error("ABSENCE EMAIL ERROR: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Suivi Coran
# ─────────────────────────────────────────────────────────────────────────────

class QuranProgressView(APIView):
    """
    GET /api/school/children/{child_id}/quran/
        → progression complete (114 sourates ou seulement les enregistrees)
    PUT /api/school/children/{child_id}/quran/{surah}/
        body: {"status": "memorized", "notes": "...", "completed_at": "2026-04-14"}
    POST /api/school/children/{child_id}/quran/bulk/
        body: [{"surah_number": 114, "status": "memorized"}, ...]
    """
    permission_classes = [
        IsAuthenticated,
        HasMosquePermission,
        plan_module_permission("school_basic"),
    ]

    def get(self, request, child_id):
        mosque = _mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        progress = QuranProgress.objects.filter(child=child).order_by("surah_number")
        progress_map = {p.surah_number: p for p in progress}

        # Retourner les 114 sourates avec statut (not_started si absent)
        result = []
        for num, name in SURAH_CHOICES:
            p = progress_map.get(num)
            result.append({
                "surah_number": num,
                "surah_name": name,
                "status": p.status if p else QuranProgress.STATUS_NOT_STARTED,
                "started_at": p.started_at.isoformat() if p and p.started_at else None,
                "completed_at": p.completed_at.isoformat() if p and p.completed_at else None,
                "notes": p.notes if p else "",
            })

        memorized = sum(1 for r in result if r["status"] == QuranProgress.STATUS_MEMORIZED)
        return Response({
            "child_id": child.id,
            "child_name": child.first_name,
            "total_memorized": memorized,
            "total_in_progress": sum(1 for r in result if r["status"] == QuranProgress.STATUS_IN_PROGRESS),
            "surahs": result,
        })

    def put(self, request, child_id, surah_number):
        mosque = _mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        new_status = request.data.get("status")
        if not new_status or new_status not in dict(QuranProgress.STATUS_CHOICES):
            return Response({"error": f"Statut invalide. Valeurs: {list(dict(QuranProgress.STATUS_CHOICES).keys())}"}, status=400)

        today = date.today()
        defaults = {
            "status": new_status,
            "notes": request.data.get("notes", ""),
            "updated_by": request.user,
        }
        if new_status == QuranProgress.STATUS_IN_PROGRESS:
            defaults["started_at"] = request.data.get("started_at") or today
        if new_status == QuranProgress.STATUS_MEMORIZED:
            defaults["completed_at"] = request.data.get("completed_at") or today

        progress, created = QuranProgress.objects.update_or_create(
            child=child,
            surah_number=surah_number,
            defaults=defaults,
        )
        log_action(request, "UPDATE", "QuranProgress", progress.id,
                   {"child": child.first_name, "surah": surah_number, "status": new_status})
        return Response(QuranProgressSerializer(progress).data)

    def post(self, request, child_id):
        """Bulk update: POST /api/school/children/{id}/quran/bulk/"""
        mosque = _mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        items = request.data if isinstance(request.data, list) else request.data.get("surahs", [])
        updated = 0
        for item in items:
            surah = item.get("surah_number")
            new_status = item.get("status")
            if not surah or not new_status:
                continue
            QuranProgress.objects.update_or_create(
                child=child, surah_number=surah,
                defaults={"status": new_status, "updated_by": request.user,
                          "notes": item.get("notes", "")},
            )
            updated += 1
        log_action(request, "UPDATE", "QuranProgress", child.id,
                   {"child": child.first_name, "bulk_updated": updated})
        return Response({"updated": updated})


# ─────────────────────────────────────────────────────────────────────────────
# Stats absences d'un enfant
# ─────────────────────────────────────────────────────────────────────────────

class ChildAbsencesView(APIView):
    """
    GET /api/school/children/{child_id}/absences/
    Statistiques d'absences d'un enfant pour l'annee active.
    """
    permission_classes = [IsAuthenticated, HasMosquePermission, plan_module_permission("school_basic")]

    def get(self, request, child_id):
        mosque = _mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()

        qs = Attendance.objects.filter(child=child)
        if active_year:
            qs = qs.filter(session__school_class__school_year=active_year)

        total_sessions = qs.count()
        absent = qs.filter(status=Attendance.STATUS_ABSENT).count()
        late = qs.filter(status=Attendance.STATUS_LATE).count()
        excused = qs.filter(status=Attendance.STATUS_EXCUSED).count()
        present = qs.filter(status=Attendance.STATUS_PRESENT).count()

        rate = round(present / total_sessions * 100, 1) if total_sessions > 0 else None

        recent_absences = qs.filter(
            status__in=[Attendance.STATUS_ABSENT, Attendance.STATUS_LATE]
        ).select_related("session__school_class").order_by("-session__date")[:10]

        return Response({
            "child_id": child.id,
            "child_name": child.first_name,
            "school_year": active_year.label if active_year else None,
            "stats": {
                "total_sessions": total_sessions,
                "present": present,
                "absent": absent,
                "late": late,
                "excused": excused,
                "attendance_rate": rate,
            },
            "recent_absences": [
                {
                    "date": a.session.date.isoformat(),
                    "class": a.session.school_class.name,
                    "status": a.status,
                    "note": a.note,
                }
                for a in recent_absences
            ],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Periodes + Appreciations
# ─────────────────────────────────────────────────────────────────────────────

class GradePeriodViewSet(viewsets.ModelViewSet):
    """
    CRUD periodes d'appreciation.
    GET/POST /api/school/periods/
    POST     /api/school/periods/{id}/grades/   — saisir les appreciations
    POST     /api/school/periods/{id}/publish/  — publier les bulletins
    """
    serializer_class = GradePeriodSerializer
    permission_classes = [
        IsAuthenticated,
        HasMosquePermission,
        plan_module_permission("school_full"),
    ]

    def get_queryset(self):
        mosque = _mosque(self.request)
        if mosque is None:
            return GradePeriod.objects.none()
        return GradePeriod.objects.filter(mosque=mosque).select_related("school_year")

    def perform_create(self, serializer):
        obj = serializer.save(mosque=_mosque(self.request))
        log_action(self.request, "CREATE", "GradePeriod", obj.id, {"name": obj.name})

    @action(detail=True, methods=["post"], url_path="grades")
    def save_grades(self, request, pk=None):
        """
        POST /api/school/periods/{id}/grades/
        body: [{"child_id": 1, "mention": "TB", "appreciation": "...", ...}, ...]
        """
        period = self.get_object()
        items = request.data if isinstance(request.data, list) else request.data.get("grades", [])
        saved = 0
        errors = []
        mosque = _mosque(request)

        for item in items:
            child_id = item.get("child_id")
            mention = item.get("mention", "")
            if not child_id or mention not in dict(Grade.MENTION_CHOICES):
                errors.append(f"Donnee invalide: {item}")
                continue
            try:
                child = Child.objects.get(id=child_id, mosque=mosque)
            except Child.DoesNotExist:
                errors.append(f"Enfant {child_id} introuvable.")
                continue

            Grade.objects.update_or_create(
                child=child, period=period,
                defaults={
                    "mention": mention,
                    "appreciation": item.get("appreciation", ""),
                    "absences_count": item.get("absences_count", 0),
                    "surah_memorized_count": item.get("surah_memorized_count", 0),
                    "school_class_id": item.get("class_id"),
                    "created_by": request.user,
                },
            )
            saved += 1

        log_action(request, "UPDATE", "GradePeriod", period.id,
                   {"grades_saved": saved, "errors": len(errors)})
        return Response({"saved": saved, "errors": errors})

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        """POST /api/school/periods/{id}/publish/ — marque les bulletins comme publies."""
        period = self.get_object()
        period.is_published = True
        period.save()
        log_action(request, "UPDATE", "GradePeriod", period.id, {"published": True})
        return Response({"detail": f"Bulletins de '{period.name}' publies."})
