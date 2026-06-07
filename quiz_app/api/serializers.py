"""Serializers for the quiz_app API."""

from urllib.parse import parse_qs, urlparse

from rest_framework import serializers

from quiz_app.models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    """Read serializer for Question, exposing core fields."""

    class Meta:
        """Serializer meta options."""

        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuestionCreateResponseSerializer(serializers.ModelSerializer):
    """Response serializer for Question after creation, including timestamps."""

    class Meta:
        """Serializer meta options."""

        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer', 'created_at', 'updated_at']


class QuizSerializer(serializers.ModelSerializer):
    """Read serializer for Quiz, including nested questions."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        """Serializer meta options."""

        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]


class QuizCreateResponseSerializer(serializers.ModelSerializer):
    """Response serializer for Quiz after creation, with full question timestamps."""

    questions = QuestionCreateResponseSerializer(many=True, read_only=True)

    class Meta:
        """Serializer meta options."""

        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'video_url',
            'questions',
        ]


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Write serializer for partial quiz updates (title and description only)."""

    class Meta:
        """Serializer meta options."""

        model = Quiz
        fields = ['title', 'description']


class QuizCreateRequestSerializer(serializers.Serializer):
    """Input serializer for quiz creation, accepting a YouTube URL."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Reject URLs that are not valid YouTube video links."""
        parsed_url = urlparse(value)
        host = parsed_url.netloc.lower()
        if host in {'youtu.be', 'www.youtu.be'} and parsed_url.path.strip('/'):
            return value
        if host.endswith('youtube.com') and parse_qs(parsed_url.query).get('v'):
            return value
        raise serializers.ValidationError('Only YouTube URLs are supported.')
