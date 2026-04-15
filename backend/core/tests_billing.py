"""Tests du systeme de plans et monetisation — Nidham"""
import pytest
from unittest.mock import MagicMock, patch
from django.test import TestCase
from rest_framework.test import APIRequestFactory


def make_plan(**kwargs):
    from core.models import Plan
    d = dict(name="test_plan",display_name="Test",price_monthly="0.00",price_yearly="0.00",
             max_families=30,max_users=1,max_sms_month=0,modules=["core"],
             is_active=True,is_public=True,sort_order=0)
    d.update(kwargs)
    return Plan(**d)


def make_sub(plan, status="active", sms_used=0):
    from core.models import Subscription
    sub = Subscription.__new__(Subscription)
    sub.mosque = MagicMock(); sub.mosque.name = "Test"
    sub.plan = plan; sub.status = status; sub.billing_cycle = "monthly"
    sub.trial_end = None; sub.current_period_end = None
    sub.sms_used_this_month = sms_used; sub.sms_reset_date = None
    sub.stripe_customer_id = ""; sub.stripe_subscription_id = ""; sub.helloasso_subscription_id = ""
    return sub

class TestPlanAllowsModule(TestCase):
    def test_present(self):
        self.assertTrue(make_plan(modules=["core","school_basic"]).allows_module("school_basic"))
    def test_absent(self):
        self.assertFalse(make_plan(modules=["core"]).allows_module("school_full"))
    def test_empty(self):
        self.assertFalse(make_plan(modules=[]).allows_module("core"))

class TestPlanCheckLimit(TestCase):
    def test_under(self):
        self.assertTrue(make_plan(max_families=30).check_limit("families", 15))
    def test_at_limit(self):
        self.assertFalse(make_plan(max_families=30).check_limit("families", 30))
    def test_over(self):
        self.assertFalse(make_plan(max_families=30).check_limit("families", 50))
    def test_unlimited(self):
        self.assertTrue(make_plan(max_families=-1).check_limit("families", 99999))
    def test_display_unlimited(self):
        self.assertEqual(make_plan(max_families=-1).get_limit_display("families"), "Illimite")
    def test_display_value(self):
        self.assertEqual(make_plan(max_families=100).get_limit_display("families"), "100")

class TestSubscriptionIsActive(TestCase):
    def test_trial(self):
        self.assertTrue(make_sub(make_plan(), status="trial").is_active)
    def test_trialing(self):
        self.assertTrue(make_sub(make_plan(), status="trialing").is_active)
    def test_active(self):
        self.assertTrue(make_sub(make_plan(), status="active").is_active)
    def test_expired(self):
        self.assertFalse(make_sub(make_plan(), status="expired").is_active)
    def test_cancelled(self):
        self.assertFalse(make_sub(make_plan(), status="cancelled").is_active)

FREE = ["core","public_portal"]
STD  = ["core","treasury_full","school_basic","public_portal","email_groups"]
PRO  = ["core","treasury_full","treasury_fec","school_basic","school_full","public_portal","email_groups","sms","member_portal","analytics","mobile_app"]
FED  = PRO + ["federation"]

class TestModulesLogic(TestCase):
    def test_free_no_school(self):
        p = make_plan(modules=FREE)
        self.assertFalse(p.allows_module("school_basic"))
    def test_standard_school_basic_not_full(self):
        p = make_plan(modules=STD)
        self.assertTrue(p.allows_module("school_basic"))
        self.assertFalse(p.allows_module("school_full"))
    def test_standard_no_fec(self):
        self.assertFalse(make_plan(modules=STD).allows_module("treasury_fec"))
    def test_standard_no_sms(self):
        self.assertFalse(make_plan(modules=STD).allows_module("sms"))
    def test_pro_all_modules(self):
        p = make_plan(modules=PRO)
        for m in ["school_full","treasury_fec","sms","member_portal","analytics"]:
            self.assertTrue(p.allows_module(m), m)
    def test_pro_no_federation_module(self):
        self.assertFalse(make_plan(modules=PRO).allows_module("federation"))
    def test_federation_module(self):
        self.assertTrue(make_plan(modules=FED).allows_module("federation"))
    def test_std_limit_families(self):
        p = make_plan(max_families=100)
        self.assertTrue(p.check_limit("families",99))
        self.assertFalse(p.check_limit("families",100))
    def test_free_limit_families(self):
        p = make_plan(max_families=30)
        self.assertTrue(p.check_limit("families",29))
        self.assertFalse(p.check_limit("families",30))
    def test_std_limit_users(self):
        p = make_plan(max_users=5)
        self.assertTrue(p.check_limit("users",4))
        self.assertFalse(p.check_limit("users",5))
    def test_pro_unlimited(self):
        p = make_plan(max_families=-1,max_users=-1)
        self.assertTrue(p.check_limit("families",99999))
        self.assertTrue(p.check_limit("users",99999))

class TestSmsRemaining(TestCase):
    def test_full_remaining(self):
        p=make_plan(max_sms_month=150); s=make_sub(p,sms_used=0)
        self.assertEqual(max(0,p.max_sms_month-s.sms_used_this_month),150)
    def test_partial(self):
        p=make_plan(max_sms_month=150); s=make_sub(p,sms_used=50)
        self.assertEqual(max(0,p.max_sms_month-s.sms_used_this_month),100)
    def test_exhausted(self):
        p=make_plan(max_sms_month=150); s=make_sub(p,sms_used=150)
        self.assertEqual(max(0,p.max_sms_month-s.sms_used_this_month),0)
    def test_free_zero(self):
        p=make_plan(max_sms_month=0)
        remaining=max(0,p.max_sms_month-0) if p.max_sms_month>0 else 0
        self.assertEqual(remaining,0)

class TestPlanModulePermission(TestCase):
    def _req(self, mosque, su=False):
        f=APIRequestFactory(); r=f.get("/")
        u=MagicMock(); u.is_superuser=su
        r.user=u; r.mosque=mosque; return r
    def test_blocks_missing(self):
        from core.plan_enforcement import plan_module_permission
        p=make_plan(modules=["core"]); m=MagicMock(); m.name="T"
        with patch("core.plan_enforcement._get_plan",return_value=p):
            self.assertFalse(plan_module_permission("school_full")().has_permission(self._req(m),None))
    def test_allows_present(self):
        from core.plan_enforcement import plan_module_permission
        p=make_plan(modules=["core","school_full"]); m=MagicMock(); m.name="T"
        with patch("core.plan_enforcement._get_plan",return_value=p):
            self.assertTrue(plan_module_permission("school_full")().has_permission(self._req(m),None))
    def test_superuser_bypass(self):
        from core.plan_enforcement import plan_module_permission
        p=make_plan(modules=["core"]); m=MagicMock()
        with patch("core.plan_enforcement._get_plan",return_value=p):
            self.assertTrue(plan_module_permission("school_full")().has_permission(self._req(m,su=True),None))
    def test_no_mosque_blocks(self):
        from core.plan_enforcement import plan_module_permission
        f=APIRequestFactory(); r=f.get("/"); u=MagicMock(); u.is_superuser=False
        r.user=u; r.mosque=None
        self.assertFalse(plan_module_permission("school_basic")().has_permission(r,None))
    def test_no_plan_fail_open(self):
        from core.plan_enforcement import plan_module_permission
        m=MagicMock(); m.name="Orphan"
        with patch("core.plan_enforcement._get_plan",return_value=None):
            self.assertTrue(plan_module_permission("school_basic")().has_permission(self._req(m),None))

@pytest.mark.django_db
def test_plan_fixtures_count():
    from core.models import Plan
    assert Plan.objects.count() >= 4

@pytest.mark.django_db
def test_plan_names_exist():
    from core.models import Plan
    names = set(Plan.objects.values_list("name",flat=True))
    for n in ["free_cloud","standard","pro","federation"]:
        assert n in names, f"Plan manquant: {n}"

@pytest.mark.django_db
def test_free_cloud_fixtures():
    from core.models import Plan
    p=Plan.objects.get(name="free_cloud")
    assert float(p.price_monthly)==0.0; assert p.max_families==30
    assert p.max_users==1; assert p.max_sms_month==0
    assert "core" in p.modules; assert "school_basic" not in p.modules

@pytest.mark.django_db
def test_standard_fixtures():
    from core.models import Plan
    p=Plan.objects.get(name="standard")
    assert float(p.price_monthly)==39.0; assert p.max_families==100
    assert p.max_users==5; assert "school_basic" in p.modules
    assert "school_full" not in p.modules; assert "treasury_fec" not in p.modules

@pytest.mark.django_db
def test_pro_fixtures():
    from core.models import Plan
    p=Plan.objects.get(name="pro")
    assert float(p.price_monthly)==79.0; assert p.max_families==-1
    assert p.max_users==-1; assert p.max_sms_month==150
    for m in ["school_full","treasury_fec","analytics","sms","member_portal"]:
        assert m in p.modules, f"Manquant dans pro: {m}"

@pytest.mark.django_db
def test_federation_not_public():
    from core.models import Plan
    p=Plan.objects.get(name="federation")
    assert p.is_public is False; assert "federation" in p.modules
    assert p.max_sms_month==500; assert float(p.price_monthly)==199.0
