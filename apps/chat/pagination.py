from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response

class ConversationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "size"
    max_page_size = 100

class MessageCursorPagination(CursorPagination):
    page_size = 50
    ordering = "created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data):
        return Response({
            "nextCursor": self.get_next_link(),
            "previousCursor": self.get_previous_link(),
            "results": data
        })
