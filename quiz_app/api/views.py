from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.models import Question, Quiz
from quiz_app.services.quiz_generator import (
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
        """Get the queryset of quizzes for the authenticated user."""
        return Quiz.objects.filter(owner=self.request.user).prefetch_related('questions')

    def get(self, request, *args, **kwargs):
        """Handle GET requests to list quizzes."""
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Handle POST requests to create a new quiz."""
        request_serializer = QuizCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        video_url = request_serializer.validated_data['source_url']
        try:
            generated_quiz = create_quiz_from_youtube_url(video_url)
        except QuizGenerationValidationError as exc:
            return Response({'url': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        quiz = self._save_quiz_with_questions(request.user, video_url, generated_quiz)

        serializer = QuizCreateResponseSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _save_quiz_with_questions(self, user, video_url, generated_quiz):
        """Save a quiz along with its questions."""
        if isinstance(generated_quiz, Quiz):
            return generated_quiz

        quiz_payload = generated_quiz if isinstance(generated_quiz, dict) else {}

        with transaction.atomic():
            quiz = Quiz.objects.create(
                owner=user,
                video_url=video_url,
                title=str(quiz_payload.get('title') or 'Generated Quiz').strip(),
                description=str(quiz_payload.get('description') or '').strip(),
            )

            questions = self._normalize_generated_questions(quiz_payload)
            Question.objects.bulk_create([
                Question(
                    quiz=quiz,
                    question_title=question['question_title'],
                    question_options=question['question_options'],
                    answer=question['answer'],
                )
                for question in questions
            ])
            return quiz

    def _normalize_generated_questions(self, quiz_payload):
        """Normalize the generated quiz questions to ensure they meet the required format."""
        raw_questions = quiz_payload.get('questions', []) if isinstance(quiz_payload, dict) else []
        normalized_questions = []

        if isinstance(raw_questions, list):
            for index, raw_question in enumerate(raw_questions, start=1):
                if len(normalized_questions) == 10:
                    break
                if not isinstance(raw_question, dict):
                    continue
                normalized_questions.append(self._normalize_question(raw_question, index))

        while len(normalized_questions) < 10:
            normalized_questions.append(self._build_fallback_question(len(normalized_questions) + 1))

        return normalized_questions

    def _normalize_question(self, raw_question, index):
        """Normalize a single quiz question to ensure it meets the required format."""
        question_title = str(
            raw_question.get('question_title')
            or raw_question.get('question')
            or f'Generated Question {index}'
        ).strip()

        raw_options = raw_question.get('question_options') or raw_question.get('options') or []
        if not isinstance(raw_options, list):
            raw_options = []

        options = []
        for option in raw_options:
            option_text = str(option).strip()
            if option_text and option_text not in options:
                options.append(option_text)
            if len(options) == 4:
                break

        while len(options) < 4:
            options.append(f'Option {chr(65 + len(options))}')

        answer = str(raw_question.get('answer') or options[0]).strip()
        if answer not in options:
            answer = options[0]

        return {
            'question_title': question_title,
            'question_options': options,
            'answer': answer,
        }

    def _build_fallback_question(self, index):
        """Build a fallback question when there are not enough generated questions."""
        options = ['Option A', 'Option B', 'Option C', 'Option D']
        return {
            'question_title': f'Question {index}: Generated fallback question',
            'question_options': options,
            'answer': options[0],
        }


class QuizDetailView(generics.GenericAPIView):
    """Endpoint for retrieving, updating and deleting a quiz."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        """Get the queryset of quizzes for the authenticated user."""
        return Quiz.objects.select_related('owner').prefetch_related('questions')

    def _get_object(self):
        """Retrieve a quiz object and check permissions."""
        quiz = get_object_or_404(self.get_queryset(), pk=self.kwargs.get(self.lookup_url_kwarg))
        self.check_object_permissions(self.request, quiz)
        return quiz

    def get(self, request, *args, **kwargs):
        """Handle GET requests to retrieve quiz details."""
        quiz = self._get_object()
        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        """Handle PATCH requests to update quiz title and description."""
        quiz = self._get_object()
        allowed_fields = {'title', 'description'}
        unsupported_fields = set(request.data.keys()) - allowed_fields
        if unsupported_fields:
            return Response(
                {'detail': 'Only title and description can be updated.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_serializer = QuizUpdateSerializer(quiz, data=request.data, partial=True)
        update_serializer.is_valid(raise_exception=True)
        update_serializer.save()

        serializer = self.get_serializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """Handle DELETE requests to delete a quiz."""
        quiz = self._get_object()
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
