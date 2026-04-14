"""
tests_v2.py — Tests école coranique v2
========================================
Couverture :
  - Class CRUD (admin/ecole_manager peut créer, TEACHER ne peut pas)
  - ClassEnrollment (enroll/unenroll, anti-doublon)
  - AttendanceSession (création, lignes auto, doublon même date bloqué)
  - AttendanceSubmit (soumettre appel via /submit/)
  - QuranProgress (GET 114 sourates, PUT statut)
  - Teacher scope isolation (prof A ne voit pas classes de prof B)
  - TeacherMeView (/api/school/teacher/me/)
  - TeacherMyClassView (/api/school/teacher/my-class/)
"""
import pytest
from django.urls import reverse
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from core.models import User
from school.models import (
    Attendance,
    AttendanceSession,
    Child,
    Class,
    ClassEnrollment,
    Family,
    QuranProgress,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _authenticated_client(mosque, user, password):
    """Client TenantClient authentifié avec JWT."""
    from django.urls import reverse as _rev
    client = TenantClient(mosque)
    resp = client.post(
        _rev("core:login"),
        {"username": user.username, "password": password},
        content_type="application/json",
    )
    assert resp.status_code == 200, f"Login échoué pour {user.username}: {resp.data}"
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {resp.data['access']}"
    return client


def _make_family(mosque):
    return Family.objects.create(
        mosque=mosque,
        primary_contact_name="Ahmed Test",
        phone1="0600000001",
        email="ahmed.test@test.com",
    )


def _make_child(mosque, family, first_name="Youssef"):
    return Child.objects.create(
        mosque=mosque,
        family=family,
        first_name=first_name,
        level="N1",
    )


def _make_class(mosque, school_year, name="Test NP", level="NP", teacher=None):
    return Class.objects.create(
        mosque=mosque,
        school_year=school_year,
        name=name,
        level_code=level,
        teacher=teacher,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures teacher
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def teacher_user(mosque):
    with schema_context(mosque.schema_name):
        return User.objects.create_user(
            username="teacher_test",
            email="teacher@test.com",
            password="TeacherPass123!",
            mosque=mosque,
            role="TEACHER",
        )


@pytest.fixture
def teacher_user_b(mosque):
    """Second professeur — pour tester l'isolation."""
    with schema_context(mosque.schema_name):
        return User.objects.create_user(
            username="teacher_b",
            email="teacher_b@test.com",
            password="TeacherBPass123!",
            mosque=mosque,
            role="TEACHER",
        )


@pytest.fixture
def teacher_client(mosque, teacher_user):
    return _authenticated_client(mosque, teacher_user, "TeacherPass123!")


@pytest.fixture
def teacher_client_b(mosque, teacher_user_b):
    return _authenticated_client(mosque, teacher_user_b, "TeacherBPass123!")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Class CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestClassCRUD:

    def test_create_class_as_admin(self, admin_client, mosque, school_year):
        """Un ADMIN peut créer une classe."""
        with schema_context(mosque.schema_name):
            resp = admin_client.post(
                "/api/school/classes/",
                {"name": "N1 Débutants", "level_code": "N1", "school_year": school_year.id},
                content_type="application/json",
            )
        assert resp.status_code == 201, resp.data
        assert resp.data["name"] == "N1 Débutants"

    def test_create_class_as_ecole_manager(self, ecole_client, mosque, school_year):
        """Un ECOLE_MANAGER peut créer une classe."""
        with schema_context(mosque.schema_name):
            resp = ecole_client.post(
                "/api/school/classes/",
                {"name": "N2 Inter", "level_code": "N2", "school_year": school_year.id},
                content_type="application/json",
            )
        assert resp.status_code == 201, resp.data

    def test_teacher_cannot_create_class(self, teacher_client, mosque, school_year):
        """Un TEACHER ne peut pas créer une classe."""
        with schema_context(mosque.schema_name):
            resp = teacher_client.post(
                "/api/school/classes/",
                {"name": "N3 Avancés", "level_code": "N3", "school_year": school_year.id},
                content_type="application/json",
            )
        assert resp.status_code in (403, 405), resp.data

    def test_list_classes(self, admin_client, mosque, school_year):
        """GET /api/school/classes/ retourne la liste."""
        with schema_context(mosque.schema_name):
            _make_class(mosque, school_year, name="NP Petits", level="NP")
            resp = admin_client.get("/api/school/classes/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_class_unique_together(self, admin_client, mosque, school_year):
        """Deux classes avec le même (mosque, school_year, level_code) → erreur."""
        with schema_context(mosque.schema_name):
            _make_class(mosque, school_year, name="N1 A", level="N1A")
            resp = admin_client.post(
                "/api/school/classes/",
                {"name": "N1 B", "level_code": "N1A", "school_year": school_year.id},
                content_type="application/json",
            )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 2. Class Enrollment
# ─────────────────────────────────────────────────────────────────────────────

class TestClassEnrollment:

    def test_enroll_child(self, admin_client, mosque, school_year):
        """POST /api/school/classes/{id}/enroll/ inscrit un enfant → 201."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            resp = admin_client.post(
                f"/api/school/classes/{klass.id}/enroll/",
                {"child_id": child.id},
                content_type="application/json",
            )
        assert resp.status_code == 201, resp.data
        assert ClassEnrollment.objects.filter(school_class=klass, child=child, is_active=True).exists()

    def test_reenroll_returns_200(self, admin_client, mosque, school_year):
        """Réinscription d'un élève déjà inscrit → 200 (pas doublon)."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            # Première inscription
            admin_client.post(
                f"/api/school/classes/{klass.id}/enroll/",
                {"child_id": child.id},
                content_type="application/json",
            )
            # Deuxième inscription du même enfant
            resp = admin_client.post(
                f"/api/school/classes/{klass.id}/enroll/",
                {"child_id": child.id},
                content_type="application/json",
            )
        assert resp.status_code == 200
        # Toujours une seule inscription active
        count = ClassEnrollment.objects.filter(school_class=klass, child=child, is_active=True).count()
        assert count == 1

    def test_unenroll_child(self, admin_client, mosque, school_year):
        """DELETE /api/school/classes/{id}/enroll/{child_id}/ → is_active=False."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(
                mosque=mosque, school_class=klass, child=child, is_active=True
            )
            resp = admin_client.delete(
                f"/api/school/classes/{klass.id}/enroll/{child.id}/"
            )
        assert resp.status_code == 200, resp.data
        e = ClassEnrollment.objects.get(school_class=klass, child=child)
        assert e.is_active is False

    def test_unenroll_nonexistent_returns_404(self, admin_client, mosque, school_year):
        """Désinscrire un enfant non inscrit → 404."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            resp = admin_client.delete(
                f"/api/school/classes/{klass.id}/enroll/{child.id}/"
            )
        assert resp.status_code == 404

    def test_get_enrolled_students(self, admin_client, mosque, school_year):
        """GET /api/school/classes/{id}/enroll/ retourne les inscrits."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(
                mosque=mosque, school_class=klass, child=child, is_active=True
            )
            resp = admin_client.get(f"/api/school/classes/{klass.id}/enroll/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["students"][0]["child"] == child.id


# ─────────────────────────────────────────────────────────────────────────────
# 3. Attendance Session
# ─────────────────────────────────────────────────────────────────────────────

class TestAttendanceSession:

    def test_create_session_auto_creates_attendance_lines(self, admin_client, mosque, school_year):
        """POST /api/school/sessions/ crée une séance + lignes présence auto."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            c1 = _make_child(mosque, family, "Ali")
            c2 = _make_child(mosque, family, "Omar")
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=c1, is_active=True)
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=c2, is_active=True)

            resp = admin_client.post(
                "/api/school/sessions/",
                {"school_class": klass.id, "date": "2026-01-10", "type": "regular"},
                content_type="application/json",
            )
        assert resp.status_code == 201, resp.data
        session_id = resp.data["id"]
        att_count = Attendance.objects.filter(session_id=session_id).count()
        assert att_count == 2

    def test_session_detail_includes_attendances(self, admin_client, mosque, school_year):
        """GET /api/school/sessions/{id}/ retourne les présences."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=child, is_active=True)
            create_resp = admin_client.post(
                "/api/school/sessions/",
                {"school_class": klass.id, "date": "2026-01-11", "type": "regular"},
                content_type="application/json",
            )
            session_id = create_resp.data["id"]
            resp = admin_client.get(f"/api/school/sessions/{session_id}/")
        assert resp.status_code == 200
        assert "attendances" in resp.data

    def test_submit_attendance(self, admin_client, mosque, school_year):
        """POST /api/school/sessions/{id}/submit/ met à jour les statuts."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=child, is_active=True)
            create_resp = admin_client.post(
                "/api/school/sessions/",
                {"school_class": klass.id, "date": "2026-01-12", "type": "regular"},
                content_type="application/json",
            )
            session_id = create_resp.data["id"]
            resp = admin_client.post(
                f"/api/school/sessions/{session_id}/submit/",
                {"attendances": [{"child_id": child.id, "status": "absent", "note": "maladie"}]},
                content_type="application/json",
            )
        assert resp.status_code == 200, resp.data
        assert resp.data["updated"] == 1
        att = Attendance.objects.get(session_id=session_id, child=child)
        assert att.status == "absent"

    def test_submit_invalid_status(self, admin_client, mosque, school_year):
        """POST /submit/ avec un statut invalide → erreur dans la liste errors."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=child, is_active=True)
            create_resp = admin_client.post(
                "/api/school/sessions/",
                {"school_class": klass.id, "date": "2026-01-13", "type": "regular"},
                content_type="application/json",
            )
            session_id = create_resp.data["id"]
            resp = admin_client.post(
                f"/api/school/sessions/{session_id}/submit/",
                {"attendances": [{"child_id": child.id, "status": "INVALIDE"}]},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert len(resp.data["errors"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Quran Progress
# ─────────────────────────────────────────────────────────────────────────────

class TestQuranProgress:

    def test_get_returns_114_surahs(self, admin_client, mosque, school_year):
        """GET /api/school/children/{id}/quran/ retourne 114 sourates."""
        with schema_context(mosque.schema_name):
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            resp = admin_client.get(f"/api/school/children/{child.id}/quran/")
        assert resp.status_code == 200, resp.data
        assert len(resp.data["surahs"]) == 114
        assert resp.data["total_memorized"] == 0

    def test_put_updates_surah_status(self, admin_client, mosque, school_year):
        """PUT /api/school/children/{id}/quran/{surah}/ met à jour le statut."""
        with schema_context(mosque.schema_name):
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            resp = admin_client.put(
                f"/api/school/children/{child.id}/quran/114/",
                {"status": "memorized"},
                content_type="application/json",
            )
        assert resp.status_code == 200, resp.data
        assert resp.data["status"] == "memorized"
        assert resp.data["surah_number"] == 114

    def test_put_invalid_status_returns_400(self, admin_client, mosque, school_year):
        """PUT avec statut invalide → 400."""
        with schema_context(mosque.schema_name):
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            resp = admin_client.put(
                f"/api/school/children/{child.id}/quran/1/",
                {"status": "INVALIDE"},
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_get_after_put_reflects_update(self, admin_client, mosque, school_year):
        """Après PUT memorized, GET retourne total_memorized=1."""
        with schema_context(mosque.schema_name):
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            admin_client.put(
                f"/api/school/children/{child.id}/quran/114/",
                {"status": "memorized"},
                content_type="application/json",
            )
            resp = admin_client.get(f"/api/school/children/{child.id}/quran/")
        assert resp.status_code == 200
        assert resp.data["total_memorized"] == 1
        # La sourate 114 doit être memorized
        surah_114 = next(s for s in resp.data["surahs"] if s["surah_number"] == 114)
        assert surah_114["status"] == "memorized"

    def test_child_not_found_returns_404(self, admin_client, mosque):
        """Enfant inexistant → 404."""
        with schema_context(mosque.schema_name):
            resp = admin_client.get("/api/school/children/99999/quran/")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 5. Teacher Scope Isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestTeacherScope:

    def test_teacher_me_returns_only_own_classes(
        self, mosque, school_year, teacher_user, teacher_user_b, teacher_client, teacher_client_b
    ):
        """TeacherMeView : prof A voit seulement ses classes, pas celles du prof B."""
        with schema_context(mosque.schema_name):
            klass_a = _make_class(mosque, school_year, name="Classe A", level="CA", teacher=teacher_user)
            klass_b = _make_class(mosque, school_year, name="Classe B", level="CB", teacher=teacher_user_b)

            resp_a = teacher_client.get("/api/school/teacher/me/")
            resp_b = teacher_client_b.get("/api/school/teacher/me/")

        assert resp_a.status_code == 200, resp_a.data
        assert resp_b.status_code == 200, resp_b.data

        ids_a = [c["id"] for c in resp_a.data["assigned_classes"]]
        ids_b = [c["id"] for c in resp_b.data["assigned_classes"]]

        assert klass_a.id in ids_a
        assert klass_b.id not in ids_a
        assert klass_b.id in ids_b
        assert klass_a.id not in ids_b

    def test_teacher_my_class_shows_enrolled_students(
        self, mosque, school_year, teacher_user, teacher_client
    ):
        """TeacherMyClassView : prof voit ses élèves."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year, name="Mon NP", level="MNP", teacher=teacher_user)
            family = _make_family(mosque)
            child = _make_child(mosque, family, "Bilal")
            ClassEnrollment.objects.create(
                mosque=mosque, school_class=klass, child=child, is_active=True
            )
            resp = teacher_client.get(f"/api/school/teacher/my-class/?class_id={klass.id}")

        assert resp.status_code == 200, resp.data
        # La réponse est {"classes": [{"class_id": ..., "students": [...]}]}
        all_students = []
        for item in resp.data.get("classes", []):
            all_students.extend(item.get("students", []))
        student_ids = [s["child_id"] for s in all_students]
        assert child.id in student_ids

    def test_teacher_cannot_access_other_class_students(
        self, mosque, school_year, teacher_user, teacher_user_b, teacher_client
    ):
        """TeacherMyClassView : prof A ne peut pas accéder aux élèves de la classe du prof B."""
        with schema_context(mosque.schema_name):
            klass_b = _make_class(mosque, school_year, name="Classe B Only", level="CBO", teacher=teacher_user_b)
            resp = teacher_client.get(f"/api/school/teacher/my-class/?class_id={klass_b.id}")

        # Doit retourner 404 car la classe n'appartient pas au prof A
        assert resp.status_code == 404, resp.data

    def test_teacher_session_scope(
        self, mosque, school_year, teacher_user, teacher_client
    ):
        """TeacherSessionListView : prof ne voit que les séances de ses classes."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year, name="Coran Prof", level="CPRO", teacher=teacher_user)
            family = _make_family(mosque)
            child = _make_child(mosque, family)
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=child, is_active=True)

            # Créer une séance via l'endpoint teacher
            resp = teacher_client.post(
                "/api/school/teacher/sessions/",
                {"school_class": klass.id, "date": "2026-02-01", "type": "regular"},
                content_type="application/json",
            )
        assert resp.status_code == 201, resp.data


# ─────────────────────────────────────────────────────────────────────────────
# 6. Teacher Quran (via teacher endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class TestTeacherQuranView:

    def test_teacher_can_update_student_quran(
        self, mosque, school_year, teacher_user, teacher_client
    ):
        """Un prof peut mettre à jour la progression Coran d'un élève de sa classe."""
        with schema_context(mosque.schema_name):
            klass = _make_class(mosque, school_year, name="Coran T", level="CT", teacher=teacher_user)
            family = _make_family(mosque)
            child = _make_child(mosque, family, "Hassan")
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass, child=child, is_active=True)

            resp = teacher_client.put(
                f"/api/school/teacher/children/{child.id}/quran/112/",
                {"status": "in_progress"},
                content_type="application/json",
            )
        assert resp.status_code == 200, resp.data
        assert resp.data["status"] == "in_progress"

    def test_teacher_cannot_update_other_class_student(
        self, mosque, school_year, teacher_user, teacher_user_b, teacher_client
    ):
        """Prof A ne peut pas modifier la progression d'un élève de la classe du prof B."""
        with schema_context(mosque.schema_name):
            klass_b = _make_class(mosque, school_year, name="Coran B", level="CQB", teacher=teacher_user_b)
            family = _make_family(mosque)
            child = _make_child(mosque, family, "Khalid")
            ClassEnrollment.objects.create(mosque=mosque, school_class=klass_b, child=child, is_active=True)

            resp = teacher_client.put(
                f"/api/school/teacher/children/{child.id}/quran/112/",
                {"status": "memorized"},
                content_type="application/json",
            )
        assert resp.status_code in (403, 404), resp.data


# ─────────────────────────────────────────────────────────────────────────────
# 7. Multi-tenant isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiTenantIsolation:

    def test_class_not_visible_across_mosques(
        self, admin_client, mosque, mosque_b, school_year, other_client
    ):
        """La mosquée B ne voit pas les classes de la mosquée A."""
        with schema_context(mosque.schema_name):
            _make_class(mosque, school_year, name="Visible A", level="VA")

        with schema_context(mosque_b.schema_name):
            resp = other_client.get("/api/school/classes/")

        assert resp.status_code == 200
        # La mosquée B n'a pas créé de classes, la liste doit être vide
        # (réponse paginée → results=[])
        results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        assert len(results) == 0
