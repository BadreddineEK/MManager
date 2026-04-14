"""Serializers school v2 — Classes, Appel, Coran, Appreciations."""
from rest_framework import serializers

from .models import (
    Attendance,
    AttendanceSession,
    Child,
    Class,
    ClassEnrollment,
    Grade,
    GradePeriod,
    QuranProgress,
    SURAH_CHOICES,
)


class ClassSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    school_year_label = serializers.CharField(source="school_year.label", read_only=True)

    class Meta:
        model = Class
        fields = [
            "id", "name", "level_code", "teacher", "teacher_name",
            "school_year", "school_year_label",
            "room", "schedule_notes", "max_students",
            "order", "student_count", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None

    def get_student_count(self, obj):
        return obj.enrollments.filter(is_active=True).count()

    def validate(self, data):
        # Verifier unicite (mosque, school_year, level_code) a la creation
        request = self.context.get("request")
        mosque = getattr(request, "mosque", None) if request else None
        school_year = data.get("school_year")
        level_code = data.get("level_code")
        if mosque and school_year and level_code:
            qs = Class.objects.filter(mosque=mosque, school_year=school_year, level_code=level_code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "level_code": "Une classe avec ce code niveau existe deja pour cette annee scolaire."
                })
        return data


class ClassEnrollmentSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.first_name", read_only=True)
    family_name = serializers.CharField(source="child.family.primary_contact_name", read_only=True)
    child_level = serializers.CharField(source="child.level", read_only=True)

    class Meta:
        model = ClassEnrollment
        fields = [
            "id", "child", "child_name", "family_name", "child_level",
            "school_class", "enrolled_at", "is_active", "notes",
        ]
        read_only_fields = ["enrolled_at"]


class AttendanceSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.first_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "child", "child_name", "status", "status_display", "note"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id", "school_class", "class_name", "date", "notes",
            "present_count", "absent_count", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_present_count(self, obj):
        return obj.attendances.filter(status=Attendance.STATUS_PRESENT).count()

    def get_absent_count(self, obj):
        return obj.attendances.filter(
            status__in=[Attendance.STATUS_ABSENT, Attendance.STATUS_LATE]
        ).count()


class AttendanceSessionDetailSerializer(AttendanceSessionSerializer):
    """Version detaillee avec la liste complete des presences."""
    attendances = AttendanceSerializer(many=True, read_only=True)

    class Meta(AttendanceSessionSerializer.Meta):
        fields = AttendanceSessionSerializer.Meta.fields + ["attendances"]


class QuranProgressSerializer(serializers.ModelSerializer):
    surah_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = QuranProgress
        fields = [
            "id", "child", "surah_number", "surah_name",
            "status", "status_display",
            "started_at", "completed_at", "notes", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_surah_name(self, obj):
        return dict(SURAH_CHOICES).get(obj.surah_number, f"Sourate {obj.surah_number}")


class GradePeriodSerializer(serializers.ModelSerializer):
    school_year_label = serializers.CharField(source="school_year.label", read_only=True)
    grades_count = serializers.SerializerMethodField()

    class Meta:
        model = GradePeriod
        fields = [
            "id", "name", "school_year", "school_year_label",
            "start_date", "end_date", "is_published", "order", "grades_count",
        ]

    def get_grades_count(self, obj):
        return obj.grades.count()


class GradeSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.first_name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    mention_display = serializers.CharField(source="get_mention_display", read_only=True)

    class Meta:
        model = Grade
        fields = [
            "id", "child", "child_name", "period", "period_name",
            "school_class", "mention", "mention_display",
            "appreciation", "absences_count", "surah_memorized_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
