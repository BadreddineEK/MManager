from rest_framework.pagination import PageNumberPagination


class DynamicPageSizePagination(PageNumberPagination):
    """
    Pagination globale qui accepte ?page_size=N sur tous les endpoints.
    Par défaut : 50. Maximum autorisé : 1000.
    """
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000
