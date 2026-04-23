from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Max 5 tentatives de login par fenetre de 5 minutes par IP.
    """
    scope = "login"
    THROTTLE_RATES = {"login": "5/min"}

    # Fenetre de 5 minutes au lieu de 1 minute
    def parse_rate(self, rate):
        num, period = super().parse_rate(rate)
        # num=5, period=60s -> on veut 5 sur 300s
        return (num, 300)

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
