from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginationMessage:
    """
        Reincarnate to String format function
    """
    message = [{
        'code': 'invalid_page',
        'message': 'Invalid page.',
        'fields': ['page'],
        'status_code': 404
    }]

    def format(self, **kwargs):
        return self.message


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 20

    invalid_page_message = PaginationMessage()

    def get_paginated_response(self, data):
        return Response({
            'next': self.page.next_page_number() if self.page.has_next() else None,
            'previous': self.page.previous_page_number() if self.page.has_previous() else None,
            'results': data
        })
