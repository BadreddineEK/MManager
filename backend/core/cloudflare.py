"""
Service Cloudflare DNS — Nidham SaaS
======================================
Crée/supprime automatiquement les CNAME DNS pour chaque tenant.

Architecture :
  - Tunnel Cloudflare configuré UNE FOIS : *.nidham.fr → nginx:80
  - À chaque création de mosquée : signal → create_tenant_dns(slug)
    → CNAME  slug.nidham.fr → <tunnel-id>.cfargotunnel.com

Variables d'environnement (.env) :
    CLOUDFLARE_API_TOKEN  token API (Zone:DNS:Edit sur nidham.fr)
    CLOUDFLARE_ZONE_ID    Zone ID nidham.fr
    CLOUDFLARE_TUNNEL_ID  UUID du tunnel Zero Trust
    NIDHAM_BASE_DOMAIN    nidham.fr
"""
import logging
import os

import requests

logger = logging.getLogger("core.cloudflare")
_API = "https://api.cloudflare.com/client/v4"


def _cfg() -> dict | None:
    t  = os.environ.get("CLOUDFLARE_API_TOKEN",  "").strip()
    z  = os.environ.get("CLOUDFLARE_ZONE_ID",    "").strip()
    ti = os.environ.get("CLOUDFLARE_TUNNEL_ID",  "").strip()
    b  = os.environ.get("NIDHAM_BASE_DOMAIN",    "").strip()
    if not all([t, z, ti, b]):
        return None
    return {"token": t, "zone_id": z, "tunnel_id": ti, "base": b}


def _hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _find(cfg: dict, fqdn: str) -> dict | None:
    try:
        r = requests.get(
            f"{_API}/zones/{cfg['zone_id']}/dns_records",
            params={"name": fqdn, "type": "CNAME"},
            headers=_hdrs(cfg["token"]), timeout=10,
        )
        res = r.json().get("result", [])
        return res[0] if res else None
    except Exception:
        return None


def create_tenant_dns(slug: str) -> tuple[bool, str]:
    """
    Crée le CNAME DNS pour un slug de tenant.
    Idempotent — ne fait rien si le record existe déjà.
    Retourne (True, message) ou (False, erreur).
    """
    cfg = _cfg()
    if not cfg:
        logger.warning(
            "CLOUDFLARE: non configuré — DNS skipped pour '%s'. "
            "Renseigner CLOUDFLARE_API_TOKEN / ZONE_ID / TUNNEL_ID / NIDHAM_BASE_DOMAIN.",
            slug,
        )
        return True, "Cloudflare non configuré (dev mode) — DNS skipped"

    fqdn    = f"{slug}.{cfg['base']}"
    content = f"{cfg['tunnel_id']}.cfargotunnel.com"

    if _find(cfg, fqdn):
        logger.info("CLOUDFLARE: '%s' existe déjà", fqdn)
        return True, f"Already exists: {fqdn}"

    try:
        r = requests.post(
            f"{_API}/zones/{cfg['zone_id']}/dns_records",
            json={"type": "CNAME", "name": fqdn, "content": content,
                  "ttl": 1, "proxied": True, "comment": f"Nidham tenant: {slug}"},
            headers=_hdrs(cfg["token"]), timeout=10,
        )
        d = r.json()
        if d.get("success"):
            logger.info("CLOUDFLARE: CNAME '%s' créé → %s", fqdn, content)
            return True, f"Created: {fqdn}"
        errors = d.get("errors", [])
        if any(e.get("code") == 81057 for e in errors):
            return True, f"Already exists: {fqdn}"
        msg = str(errors)
        logger.error("CLOUDFLARE: Erreur création '%s' — %s", fqdn, msg)
        return False, f"API error: {msg}"
    except requests.RequestException as exc:
        logger.error("CLOUDFLARE: Exception réseau '%s' — %s", fqdn, exc)
        return False, f"Network error: {exc}"


def delete_tenant_dns(slug: str) -> tuple[bool, str]:
    """Supprime le CNAME DNS d'un tenant (lors suppression mosquée)."""
    cfg = _cfg()
    if not cfg:
        return True, "Cloudflare non configuré — skipped"

    fqdn     = f"{slug}.{cfg['base']}"
    existing = _find(cfg, fqdn)
    if not existing:
        return True, f"Record '{fqdn}' introuvable"

    try:
        r = requests.delete(
            f"{_API}/zones/{cfg['zone_id']}/dns_records/{existing['id']}",
            headers=_hdrs(cfg["token"]), timeout=10,
        )
        if r.json().get("success"):
            logger.info("CLOUDFLARE: CNAME '%s' supprimé", fqdn)
            return True, f"Deleted: {fqdn}"
        msg = str(r.json().get("errors", []))
        logger.error("CLOUDFLARE: Erreur suppression '%s' — %s", fqdn, msg)
        return False, f"API error: {msg}"
    except requests.RequestException as exc:
        return False, f"Network error: {exc}"
