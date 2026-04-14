"""
Teacher Views — Espace Professeur
====================================
Endpoints reserves au role TEACHER, scopes a SA classe uniquement.
Un prof ne voit que les eleves de ses classes, ne peut pas acceder
aux donnees financieres ni aux autres classes.

Endpoints:
  GET  /api/school/teacher/me/            — profil + classes assignees
  GET  /api/school/teacher/my-class/      — eleves de MA classe (annee active)
  POST /api/school/teacher/sessions/      — creer une seance d'appel
  GET  /api/school/teacher/sessions/      — mes seances d'appel
  POST /api/school/teacher/sessions/{id}/submit/  — soumettre l'appel
  GET  /api/school/teacher/sessions/{id}/ — detail seance
  GET  /api/school/teacher/children/{id}/quran/   — suivi Coran (lecture + ecriture)
  PUT  /api/school/teacher/children/{id}/quran/{surah}/
  GET  /api/school/teacher/children/{id}/absences/
  POST /api/school/teacher/periods/{id}/grades/   — saisir appreciations (school_full)
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission, IsTeacherOrAdmin
from core.plan_enforcement import plan_module_permission
from core.utils import get_mosque, log_action

from .models import (
    Attendance,
    AttendanceSession,
    Child,
    Class,
    ClassEnrollment,
    Grade,
    GradePeriod,
    QuranProgress,
    SchoolYear,
    SURAH_CHOICES,
)
from .serializers_v2 import (
    AttendanceSerializer,
    AttendanceSessionDetailSerializer,
    AttendanceSessionSerializer,
    ClassEnrollmentSerializer,
    ClassSerializer,
    GradeSerializer,
    QuranProgressSerializer,
)

logger = logging.getLogger("school.teacher")

TEACHER_PERMISSIONS = [
    IsAuthenticated,
    HasMosquePermission,
    IsTeacherOrAdmin,
    plan_module_permission("school_basic"),
]


def _get_teacher_classes(request):
    """
    Retourne les classes dont l'utilisateur est le prof assigne.
    Si ADMIN ou ECOLE_MANAGER : retourne toutes les classes de la mosquee.
    """
    user = request.user
    mosque = get_mosque(request)
    if mosque is None:
        return Class.objects.none()

    role = getattr(user, "role", "")
    if user.is_superuser or role in ("ADMIN", "ECOLE_MANAGER"):
        # Admin voit tout
        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        if active_year:
            return Class.objects.filter(mosque=mosque, school_year=active_year)
        return Class.objects.filter(mosque=mosque)
    else:
        # Prof voit seulement ses classes
        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        qs = Class.objects.filter(mosque=mosque, teacher=user)
        if active_year:
            qs = qs.filter(school_year=active_year)
        return qs


def _assert_class_access(request, school_class):
    """Leve une exception si le prof n'a pas acces a cette classe."""
    user = request.user
    role = getattr(user, "role", "")
    if user.is_superuser or role in ("ADMIN", "ECOLE_MANAGER"):
        return True
    if school_class.teacher != user:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Vous n'avez pas acces a cette classe.")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Profil professeur
# ─────────────────────────────────────────────────────────────────────────────

class TeacherMeView(APIView):
    """
    GET /api/school/teacher/me/
    Retourne le profil du prof connecte + ses classes assignees.
    """
    permission_classes = TEACHER_PERMISSIONS

    def get(self, request):
        user = request.user
        mosque = get_mosque(request)
        my_classes = _get_teacher_classes(request)
        classes_data = ClassSerializer(my_classes, many=True).data

        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": getattr(user, "role", ""),
                "email": user.email,
            },
            "mosque": mosque.name if mosque else None,
            "assigned_classes": classes_data,
            "classes_count": my_classes.count(),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Ma classe — liste des eleves
# ─────────────────────────────────────────────────────────────────────────────

class TeacherMyClassView(APIView):
    """
    GET /api/school/teacher/my-class/?class_id=X
    Liste des eleves inscrits dans la/les classes du prof.
    """
    permission_classes = TEACHER_PERMISSIONS

    def get(self, request):
        mosque = get_mosque(request)
        my_classes = _get_teacher_classes(request)

        # Filtre optionnel par classe
        class_id = request.query_params.get("class_id")
        if class_id:
            my_classes = my_classes.filter(id=class_id)
            if not my_classes.exists():
                return Response({"error": "Classe introuvable ou non assignee."}, status=404)

        result = []
        for school_class in my_classes:
            enrollments = ClassEnrollment.objects.filter(
                school_class=school_class, is_active=True
            ).select_related("child__family")

            students = []
            for e in enrollments:
                child = e.child
                memorized = QuranProgress.objects.filter(
                    child=child, status=QuranProgress.STATUS_MEMORIZED
                ).count()
                absences = Attendance.objects.filter(
                    child=child,
                    status__in=[Attendance.STATUS_ABSENT],
                    session__school_class=school_class,
                ).count()
                students.append({
                    "enrollment_id": e.id,
                    "child_id": child.id,
                    "child_name": child.first_name,
                    "family_name": child.family.primary_contact_name,
                    "family_phone": child.family.phone1,
                    "family_email": child.family.email,
                    "level": child.level,
                    "birth_date": child.birth_date.isoformat() if child.birth_date else None,
                    "quran_memorized": memorized,
                    "absences_count": absences,
                })

            result.append({
                "class_id": school_class.id,
                "class_name": school_class.name,
                "level_code": school_class.level_code,
                "room": school_class.room,
                "schedule_notes": school_class.schedule_notes,
                "student_count": len(students),
                "students": students,
            })

        return Response({"classes": result})


# ─────────────────────────────────────────────────────────────────────────────
# Seances d'appel — scope prof
# ─────────────────────────────────────────────────────────────────────────────

class TeacherSessionListView(APIView):
    """
    GET  /api/school/teacher/sessions/?class_id=X
    POST /api/school/teacher/sessions/
    """
    permission_classes = TEACHER_PERMISSIONS

    def get(self, request):
        mosque = get_mosque(request)
        my_classes = _get_teacher_classes(request)
        class_id = request.query_params.get("class_id")
        if class_id:
            my_classes = my_classes.filter(id=class_id)

        sessions = AttendanceSession.objects.filter(
            school_class__in=my_classes
        ).select_related("school_class").order_by("-date")[:50]

        return Response(AttendanceSessionSerializer(sessions, many=True).data)

    def post(self, request):
        """Creer une seance pour une classe du prof."""
        mosque = get_mosque(request)
        class_id = request.data.get("school_class")
        if not class_id:
            return Response({"error": "school_class requis."}, status=400)

        try:
            school_class = Class.objects.get(id=class_id, mosque=mosque)
        except Class.DoesNotExist:
            return Response({"error": "Classe introuvable."}, status=404)

        _assert_class_access(request, school_class)

        session_date = request.data.get("date")
        if not session_date:
            from django.utils import timezone
            session_date = timezone.now().date().isoformat()

        # Verifier doublon
        existing = AttendanceSession.objects.filter(
            school_class=school_class, date=session_date
        ).first()
        if existing:
            return Response(
                {"error": f"Une seance existe deja pour cette classe le {session_date}.", "session_id": existing.id},
                status=409
            )

        session = AttendanceSession.objects.create(
            mosque=mosque,
            school_class=school_class,
            date=session_date,
            notes=request.data.get("notes", ""),
            created_by=request.user,
        )

        # Auto-creer lignes de presence
        enrollments = ClassEnrollment.objects.filter(
            school_class=school_class, is_active=True
        )
        Attendance.objects.bulk_create([
            Attendance(session=session, child=e.child, status=Attendance.STATUS_PRESENT)
            for e in enrollments
        ], ignore_conflicts=True)

        log_action(request, "CREATE", "AttendanceSession", session.id,
                   {"class": school_class.name, "date": str(session_date), "nb_eleves": enrollments.count()})

        return Response(AttendanceSessionSerializer(session).data, status=201)


class TeacherSessionDetailView(APIView):
    """
    GET  /api/school/teacher/sessions/{id}/
    POST /api/school/teacher/sessions/{id}/submit/
    """
    permission_classes = TEACHER_PERMISSIONS

    def _get_session(self, request, session_id):
        mosque = get_mosque(request)
        try:
            session = AttendanceSession.objects.select_related("school_class").get(
                id=session_id, mosque=mosque
            )
        except AttendanceSession.DoesNotExist:
            return None
        _assert_class_access(request, session.school_class)
        return session

    def get(self, request, session_id):
        session = self._get_session(request, session_id)
        if not session:
            return Response({"error": "Seance introuvable."}, status=404)
        return Response(AttendanceSessionDetailSerializer(session).data)

    def post(self, request, session_id):
        """Soumettre l'appel."""
        session = self._get_session(request, session_id)
        if not session:
            return Response({"error": "Seance introuvable."}, status=404)

        data = request.data.get("attendances", [])
        if not data:
            return Response({"error": "attendances[] requis."}, status=400)

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
                   {"prof": request.user.username, "updates": updates})
        return Response({
            "updated": updates,
            "errors": errors,
            "detail": f"Appel enregistre : {updates} eleve(s) mis a jour.",
        })


# ─────────────────────────────────────────────────────────────────────────────
# Coran + Absences — acces direct depuis espace prof
# ─────────────────────────────────────────────────────────────────────────────

class TeacherQuranView(APIView):
    """
    GET /api/school/teacher/children/{child_id}/quran/
    PUT /api/school/teacher/children/{child_id}/quran/{surah}/
    Identique a QuranProgressView mais avec verification scope prof.
    """
    permission_classes = TEACHER_PERMISSIONS

    def _get_child(self, request, child_id):
        mosque = get_mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return None
        # Verifier que l'enfant est dans une des classes du prof
        my_classes = _get_teacher_classes(request)
        if not ClassEnrollment.objects.filter(
            child=child, school_class__in=my_classes, is_active=True
        ).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cet enfant n'est pas dans vos classes.")
        return child

    def get(self, request, child_id):
        child = self._get_child(request, child_id)
        if not child:
            return Response({"error": "Enfant introuvable."}, status=404)

        progress = QuranProgress.objects.filter(child=child).order_by("surah_number")
        progress_map = {p.surah_number: p for p in progress}

        result = []
        for num, name in SURAH_CHOICES:
            p = progress_map.get(num)
            result.append({
                "surah_number": num,
                "surah_name": name,
                "status": p.status if p else QuranProgress.STATUS_NOT_STARTED,
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
        from datetime import date
        child = self._get_child(request, child_id)
        if not child:
            return Response({"error": "Enfant introuvable."}, status=404)

        new_status = request.data.get("status")
        if not new_status or new_status not in dict(QuranProgress.STATUS_CHOICES):
            return Response({"error": "Statut invalide."}, status=400)

        defaults = {"status": new_status, "notes": request.data.get("notes", ""), "updated_by": request.user}
        if new_status == QuranProgress.STATUS_IN_PROGRESS:
            defaults["started_at"] = request.data.get("started_at") or date.today()
        if new_status == QuranProgress.STATUS_MEMORIZED:
            defaults["completed_at"] = request.data.get("completed_at") or date.today()

        progress, _ = QuranProgress.objects.update_or_create(
            child=child, surah_number=surah_number, defaults=defaults
        )
        log_action(request, "UPDATE", "QuranProgress", progress.id,
                   {"prof": request.user.username, "child": child.first_name, "surah": surah_number})
        return Response(QuranProgressSerializer(progress).data)


class TeacherChildAbsencesView(APIView):
    """GET /api/school/teacher/children/{child_id}/absences/"""
    permission_classes = TEACHER_PERMISSIONS

    def get(self, request, child_id):
        mosque = get_mosque(request)
        try:
            child = Child.objects.get(id=child_id, mosque=mosque)
        except Child.DoesNotExist:
            return Response({"error": "Enfant introuvable."}, status=404)

        my_classes = _get_teacher_classes(request)
        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()

        qs = Attendance.objects.filter(
            child=child, session__school_class__in=my_classes
        )
        if active_year:
            qs = qs.filter(session__school_class__school_year=active_year)

        total = qs.count()
        absent = qs.filter(status=Attendance.STATUS_ABSENT).count()
        late = qs.filter(status=Attendance.STATUS_LATE).count()
        present = qs.filter(status=Attendance.STATUS_PRESENT).count()
        rate = round(present / total * 100, 1) if total > 0 else None

        recent = qs.filter(
            status__in=[Attendance.STATUS_ABSENT, Attendance.STATUS_LATE]
        ).select_related("session__school_class").order_by("-session__date")[:10]

        return Response({
            "child_id": child.id,
            "child_name": child.first_name,
            "stats": {
                "total_sessions": total, "present": present,
                "absent": absent, "late": late,
                "attendance_rate": rate,
            },
            "recent_absences": [
                {"date": a.session.date.isoformat(), "class": a.session.school_class.name,
                 "status": a.status, "note": a.note}
                for a in recent
            ],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Appreciations — scope prof (school_full)
# ─────────────────────────────────────────────────────────────────────────────

class TeacherGradeView(APIView):
    """
    POST /api/school/teacher/periods/{period_id}/grades/
    Saisir les appreciations pour les eleves des classes du prof.
    Requiert le module school_full.
    """
    permission_classes = [
        IsAuthenticated,
        HasMosquePermission,
        IsTeacherOrAdmin,
        plan_module_permission("school_full"),
    ]

    def post(self, request, period_id):
        mosque = get_mosque(request)
        try:
            period = GradePeriod.objects.get(id=period_id, mosque=mosque)
        except GradePeriod.DoesNotExist:
            return Response({"error": "Periode introuvable."}, status=404)

        my_classes = _get_teacher_classes(request)
        items = request.data if isinstance(request.data, list) else request.data.get("grades", [])
        saved, errors = 0, []

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
            # Verifier que l'enfant est dans les classes du prof
            if not ClassEnrollment.objects.filter(
                child=child, school_class__in=my_classes, is_active=True
            ).exists():
                errors.append(f"Enfant {child_id} hors de vos classes.")
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
                   {"prof": request.user.username, "saved": saved, "errors": len(errors)})
        return Response({"saved": saved, "errors": errors})
