import logging

from django.db import connection
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterMosqueSerializer

logger = logging.getLogger(__name__)


class CheckSlugView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        with schema_context('public'):
            from core.models import Mosque
            slug = request.query_params.get('slug', '').lower().strip()
            if not slug:
                return Response({'error': 'Parametre slug requis.'}, status=400)
            available = not Mosque.objects.filter(slug=slug).exists()
            return Response({'available': available, 'slug': slug})


class RegisterMosqueView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        with schema_context('public'):
            from core.models import Mosque as _Mosque
            serializer = RegisterMosqueSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data            = serializer.validated_data
        slug            = data['slug']
        schema_name     = slug.replace('-', '_')
        mosque_name     = data['mosque_name']
        timezone        = data['timezone']
        admin_username  = data['admin_username']
        admin_email     = data['admin_email']
        admin_password  = data['admin_password']
        base_domain     = data['base_domain']
        # Username interne = slug__username pour éviter les collisions inter-mosquées
        internal_username = f"{schema_name}__{admin_username}" 

        try:
            with schema_context('public'):
                from core.models import Domain, Mosque
                mosque = Mosque(
                    schema_name=schema_name,
                    name=mosque_name,
                    slug=slug,
                    timezone=timezone,
                )
                mosque.save()
                logger.info('Tenant cree: %s (schema=%s)', mosque_name, schema_name)

                full_domain = slug + "." + base_domain
                Domain.objects.create(domain=full_domain, tenant=mosque, is_primary=True)
                logger.info('Domaine cree: %s', full_domain)

            with schema_context(schema_name):
                from django.contrib.auth import get_user_model
                User = get_user_model()
                User.objects.create_user(
                    username=internal_username,
                    email=admin_email,
                    password=admin_password,
                    mosque=mosque,
                    role='ADMIN',
                )
                logger.info('Admin cree: %s (login=%s) dans %s', admin_username, internal_username, schema_name)

            # 4. Assigner plan free + trial 30 jours
            import datetime
            from django_tenants.utils import schema_context as sc
            with sc('public'):
                from core.models import Plan, Subscription
                # Trial = plan pro (accès complet pendant l'essai)
                trial_plan = Plan.objects.filter(name='pro').first() \
                    or Plan.objects.filter(name='free_cloud').first() \
                    or Plan.objects.first()
                today = datetime.date.today()
                trial_end = today + datetime.timedelta(days=14)  # 14j comme affiche sur le portail
                Subscription.objects.create(
                    mosque=mosque,
                    plan=trial_plan,
                    status='trial',
                    billing_cycle='monthly',
                    trial_end=trial_end,
                    current_period_start=today,
                    current_period_end=trial_end,
                )
                logger.info('Subscription trial (plan=%s) creee pour %s', trial_plan.name, mosque.name)

            return Response(
                {
                    'success': True,
                    'mosque': {
                        'id':          mosque.pk,
                        'name':        mosque.name,
                        'slug':        mosque.slug,
                        'schema_name': mosque.schema_name,
                    },
                    'domain':         full_domain,
                    'admin_username':    admin_username,
                    'login_username':    internal_username,
                    'message': f'Mosquée créée. Connectez-vous avec : {internal_username}',
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            logger.exception('Erreur onboarding slug=%s', slug)
            try:
                with schema_context('public'):
                    from core.models import Domain, Mosque as M
                    Domain.objects.filter(tenant__schema_name=schema_name).delete()
                    M.objects.filter(schema_name=schema_name).delete()
            except Exception:
                pass
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
