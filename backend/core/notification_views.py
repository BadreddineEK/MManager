"""
Vues Notifications email — envoi de rappels
=============================================
POST /api/notifications/send-arrears/
    → Envoie un email de rappel à toutes les familles en impayé (année active)
POST /api/notifications/send-unpaid-members/
    → Envoie un email de rappel à tous les adhérents non cotisants (année active)
POST /api/notifications/test/
    → Envoie un email de test à l'adresse fournie (vérifie la config SMTP)

Les emails sont envoyés en direct (pas de queue). Sur un Pi, c'est suffisant.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import MosqueSettings
from core.permissions import IsAdminRole
from core.utils import get_mosque, log_action
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Family, SchoolPayment, SchoolYear

logger = logging.getLogger("core")


def _get_smtp_settings(mosque):
    """Retourne les paramètres SMTP depuis MosqueSettings."""
    try:
        s = mosque.settings
        return {
            "host": s.smtp_host,
            "port": s.smtp_port,
            "user": s.smtp_user,
            "password": s.smtp_password,
            "use_tls": s.smtp_use_tls,
            "from": s.email_from or s.smtp_user,
            "prefix": s.email_subject_prefix or "[Mosquée Manager]",
            "mosque_name": mosque.name,
        }
    except MosqueSettings.DoesNotExist:
        return None


def _send_email(smtp_cfg: dict, to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """
    Envoie un email via SMTP.
    Retourne (success: bool, error_message: str).
    """
    if not smtp_cfg.get("host"):
        return False, "SMTP non configuré (hôte manquant)"
    if not to_email or "@" not in to_email:
        return False, f"Adresse email invalide : {to_email!r}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{smtp_cfg['prefix']} {subject}"
    msg["From"] = smtp_cfg["from"]
    msg["To"] = to_email

    # Version texte plain (fallback)
    import re
    plain = re.sub(r"<[^>]+>", "", html_body).strip()
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if smtp_cfg["use_tls"]:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"], timeout=10)

        if smtp_cfg["user"] and smtp_cfg["password"]:
            server.login(smtp_cfg["user"], smtp_cfg["password"])

        server.sendmail(smtp_cfg["from"], [to_email], msg.as_string())
        server.quit()
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Erreur d'authentification SMTP"
    except smtplib.SMTPConnectError:
        return False, f"Impossible de se connecter à {smtp_cfg['host']}:{smtp_cfg['port']}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _arrears_email_html(mosque_name: str, family_name: str, school_year: str) -> str:
    return f"""
<html><body style="font-family:sans-serif;color:#1e1e2e;padding:20px;">
  <h2 style="color:#6d28d9;">🕌 {mosque_name}</h2>
  <p>Bonjour <strong>{family_name}</strong>,</p>
  <p>
    Nous vous informons que le paiement des frais de scolarité pour l'année
    <strong>{school_year}</strong> n'a pas encore été enregistré à notre niveau.
  </p>
  <p>
    Nous vous remercions de bien vouloir régulariser votre situation au plus tôt.<br/>
    N'hésitez pas à nous contacter pour tout renseignement.
  </p>
  <p style="margin-top:24px;">Cordialement,<br/><strong>{mosque_name}</strong></p>
</body></html>
"""


def _unpaid_member_email_html(mosque_name: str, member_name: str, year: int, amount: float) -> str:
    return f"""
<html><body style="font-family:sans-serif;color:#1e1e2e;padding:20px;">
  <h2 style="color:#6d28d9;">🕌 {mosque_name}</h2>
  <p>Bonjour <strong>{member_name}</strong>,</p>
  <p>
    Nous vous rappelons que votre cotisation annuelle pour <strong>{year}</strong>
    d'un montant de <strong>{amount:.2f} €</strong> n'a pas encore été réglée.
  </p>
  <p>
    Merci de bien vouloir régulariser votre situation.<br/>
    Pour toute question, n'hésitez pas à nous contacter.
  </p>
  <p style="margin-top:24px;">Cordialement,<br/><strong>{mosque_name}</strong></p>
</body></html>
"""


class SendArrearsNotificationsView(APIView):
    """
    POST /api/notifications/send-arrears/
    Envoie un email à chaque famille ayant un impayé pour l'année scolaire active.
    Réponse : { sent: [...], failed: [...], skipped: [...] }
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquée trouvée."}, status=status.HTTP_404_NOT_FOUND)

        smtp_cfg = _get_smtp_settings(mosque)
        if not smtp_cfg or not smtp_cfg.get("host"):
            return Response(
                {"detail": "Configuration SMTP manquante. Renseignez-la dans Paramètres → Notifications."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response({"detail": "Aucune année scolaire active."}, status=status.HTTP_404_NOT_FOUND)

        paid_family_ids = set(
            SchoolPayment.objects.filter(mosque=mosque, school_year=active_year)
            .values_list("family_id", flat=True)
        )
        families_in_arrears = Family.objects.filter(mosque=mosque).exclude(id__in=paid_family_ids)

        sent, failed, skipped = [], [], []

        for family in families_in_arrears:
            if not family.email:
                skipped.append({"id": family.id, "name": family.primary_contact_name, "reason": "Pas d'email"})
                continue

            html = _arrears_email_html(mosque.name, family.primary_contact_name, active_year.label)
            ok, err = _send_email(
                smtp_cfg,
                family.email,
                f"Rappel paiement — {active_year.label}",
                html,
            )
            if ok:
                sent.append({"id": family.id, "name": family.primary_contact_name, "email": family.email})
                logger.info("NOTIF: rappel envoyé → %s <%s>", family.primary_contact_name, family.email)
            else:
                failed.append({"id": family.id, "name": family.primary_contact_name, "email": family.email, "error": err})
                logger.warning("NOTIF: échec envoi → %s <%s> : %s", family.primary_contact_name, family.email, err)

        log_action(request, "SEND_NOTIF", "SchoolArrears", payload={
            "year": active_year.label,
            "sent": len(sent),
            "failed": len(failed),
            "skipped": len(skipped),
        })

        return Response({
            "year": active_year.label,
            "total": len(sent) + len(failed) + len(skipped),
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
        })


class SendUnpaidMembersNotificationsView(APIView):
    """
    POST /api/notifications/send-unpaid-members/
    Envoie un email à chaque adhérent sans cotisation pour l'année active.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquée trouvée."}, status=status.HTTP_404_NOT_FOUND)

        smtp_cfg = _get_smtp_settings(mosque)
        if not smtp_cfg or not smtp_cfg.get("host"):
            return Response(
                {"detail": "Configuration SMTP manquante. Renseignez-la dans Paramètres → Notifications."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_year = MembershipYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response({"detail": "Aucune année de cotisation active."}, status=status.HTTP_404_NOT_FOUND)

        paid_ids = set(
            MembershipPayment.objects.filter(mosque=mosque, membership_year=active_year)
            .values_list("member_id", flat=True)
        )
        unpaid_members = Member.objects.filter(mosque=mosque).exclude(id__in=paid_ids)

        sent, failed, skipped = [], [], []

        for member in unpaid_members:
            if not member.email:
                skipped.append({"id": member.id, "name": member.full_name, "reason": "Pas d'email"})
                continue

            html = _unpaid_member_email_html(
                mosque.name, member.full_name, active_year.year, float(active_year.amount_expected)
            )
            ok, err = _send_email(
                smtp_cfg,
                member.email,
                f"Rappel cotisation {active_year.year}",
                html,
            )
            if ok:
                sent.append({"id": member.id, "name": member.full_name, "email": member.email})
                logger.info("NOTIF: rappel cotisation → %s <%s>", member.full_name, member.email)
            else:
                failed.append({"id": member.id, "name": member.full_name, "email": member.email, "error": err})
                logger.warning("NOTIF: échec cotisation → %s <%s> : %s", member.full_name, member.email, err)

        log_action(request, "SEND_NOTIF", "MembershipUnpaid", payload={
            "year": active_year.year,
            "sent": len(sent),
            "failed": len(failed),
            "skipped": len(skipped),
        })

        return Response({
            "year": active_year.year,
            "total": len(sent) + len(failed) + len(skipped),
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
        })


class TestEmailView(APIView):
    """
    POST /api/notifications/test/
    Body: { "to": "test@email.com" }
    Envoie un email de test pour vérifier la config SMTP.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquée trouvée."}, status=status.HTTP_404_NOT_FOUND)

        smtp_cfg = _get_smtp_settings(mosque)
        if not smtp_cfg or not smtp_cfg.get("host"):
            return Response(
                {"detail": "Configuration SMTP manquante."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        to_email = request.data.get("to", "").strip()
        if not to_email or "@" not in to_email:
            return Response({"detail": "Adresse email invalide."}, status=status.HTTP_400_BAD_REQUEST)

        html = f"""
<html><body style="font-family:sans-serif;padding:20px;">
  <h2 style="color:#6d28d9;">✅ Test email — {mosque.name}</h2>
  <p>La configuration SMTP de <strong>{mosque.name}</strong> fonctionne correctement.</p>
  <p style="color:#888;font-size:12px;">Envoyé depuis Mosquée Manager</p>
</body></html>
"""
        ok, err = _send_email(smtp_cfg, to_email, "Test de configuration email", html)
        if ok:
            return Response({"detail": f"Email de test envoyé à {to_email}."})
        else:
            return Response({"detail": f"Échec : {err}"}, status=status.HTTP_502_BAD_GATEWAY)
