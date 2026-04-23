from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Max 5 tentatives de login par minute par IP.
    (Nginx fournit une 2e couche : 5r/m avec burst=3)
    """
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
