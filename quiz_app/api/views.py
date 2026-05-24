from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Question, Quiz
from quiz_app.services.quiz_generator import create_quiz_from_youtube_url

from .permissions import IsQuizOwner
from .serializers import QuizCreateRequestSerializer, QuizSerializer


class QuizListCreateView(generics.GenericAPIView):
    """Endpoint for listing user quizzes and creating a new quiz."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(owner=self.request.user).prefetch_related('questions')

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        request_serializer = QuizCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        video_url = request_serializer.validated_data['url']
        generated_quiz = create_quiz_from_youtube_url(video_url)
        quiz = self._save_quiz_with_questions(request.user, video_url, generated_quiz)

        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _save_quiz_with_questions(self, user, video_url, generated_quiz):
        if isinstance(generated_quiz, Quiz):
            return generated_quiz

        with transaction.atomic():
            quiz = Quiz.objects.create(
                owner=user,
                video_url=video_url,
                title=generated_quiz.get('title', 'Generated Quiz'),
                description=generated_quiz.get('description', ''),
            )
            questions = generated_quiz.get('questions', [])
            Question.objects.bulk_create([
                Question(
                    quiz=quiz,
                    title=question.get('title', 'Generated Question'),
                    description=question.get('description', ''),
                )
                for question in questions
            ])
            return quiz


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
        quiz = self._get_object()
        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        self._get_object()
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def delete(self, request, *args, **kwargs):
        self._get_object()
        return Response({'detail': 'Not implemented yet.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
