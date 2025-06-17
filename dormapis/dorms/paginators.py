from rest_framework.pagination import PageNumberPagination


class ItemPaginator(PageNumberPagination):
    page_size = 4