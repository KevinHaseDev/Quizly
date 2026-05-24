from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Quiz

from .permissions import IsQuizOwner
from .serializers import QuizSerializer


class QuizListCreateView(generics.GenericAPIView):
    """Skeleton endpoint for quiz list/create."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(owner=self.request.user).prefetch_related('questions')

    def get(self, request, *args, **kwargs):
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def post(self, request, *args, **kwargs):
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class QuizDetailView(generics.GenericAPIView):
    """Skeleton endpoint for quiz retrieve/update/delete."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        return Quiz.objects.select_related('owner').prefetch_related('questions')

    def _get_object(self):
        quiz = get_object_or_404(self.get_queryset(), pk=self.kwargs.get(self.lookup_url_kwarg))
        self.check_object_permissions(self.request, quiz)
        return quiz

    def get(self, request, *args, **kwargs):
        self._get_object()
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def patch(self, request, *args, **kwargs):
        self._get_object()
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, *args, **kwargs):
        self._get_object()
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
