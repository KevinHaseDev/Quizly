from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Question, Quiz
from quiz_app.services.quiz_generator import (
    QuizGenerationServiceError,
    QuizGenerationValidationError,
    create_quiz_from_youtube_url,
)

from .permissions import IsQuizOwner
from .serializers import (
    QuizCreateRequestSerializer,
    QuizCreateResponseSerializer,
    QuizSerializer,
    QuizUpdateSerializer,
)


class QuizListCreateView(generics.GenericAPIView):
    """Endpoint for listing user quizzes and creating a new quiz."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(owner=self.request.user).prefetch_related(
            "questions"
        )

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        request_serializer = QuizCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        video_url = request_serializer.validated_data["url"]
        try:
            generated_quiz = create_quiz_from_youtube_url(video_url)
        except QuizGenerationValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except QuizGenerationServiceError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            quiz = self._save_quiz_with_questions(
                request.user, video_url, generated_quiz
            )
        except Exception as exc:
            return Response(
                {"detail": "Failed to save quiz."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = QuizCreateResponseSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _save_quiz_with_questions(self, user, video_url, generated_quiz):
        """Persist the generated quiz dict to the database atomically."""
        with transaction.atomic():
            quiz = Quiz.objects.create(
                owner=user,
                video_url=video_url,
                title=generated_quiz.get("title", "Generated Quiz"),
                description=generated_quiz.get("description", ""),
            )
            Question.objects.bulk_create(
                [
                    Question(
                        quiz=quiz,
                        question_title=q.get("question_title", ""),
                        question_options=q.get("question_options", []),
                        answer=q.get("answer", ""),
                    )
                    for q in generated_quiz.get("questions", [])
                ]
            )
            return quiz


class QuizDetailView(generics.GenericAPIView):
    """Endpoint for retrieving, updating and deleting a quiz."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    lookup_url_kwarg = "id"

    def get_queryset(self):
        return Quiz.objects.select_related("owner").prefetch_related("questions")

    def _get_object(self):
        quiz = get_object_or_404(
            self.get_queryset(), pk=self.kwargs.get(self.lookup_url_kwarg)
        )
        self.check_object_permissions(self.request, quiz)
        return quiz

    def get(self, request, *args, **kwargs):
        quiz = self._get_object()
        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        quiz = self._get_object()
        allowed_fields = {"title", "description"}
        unsupported_fields = set(request.data.keys()) - allowed_fields
        if unsupported_fields:
            return Response(
                {"detail": "Only title and description can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_serializer = QuizUpdateSerializer(quiz, data=request.data, partial=True)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()

        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        quiz = self._get_object()
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
