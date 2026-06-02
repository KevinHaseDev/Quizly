from rest_framework import serializers

from quiz_app.models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for quiz questions."""
    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuestionCreateResponseSerializer(serializers.ModelSerializer):
    """Serializer for quiz question creation response."""
    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer', 'created_at', 'updated_at']


class QuizSerializer(serializers.ModelSerializer):
    """Serializer for quizzes."""
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
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
    """Serializer for quiz creation response."""
    questions = QuestionCreateResponseSerializer(many=True, read_only=True)

    class Meta:
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
    """Serializer for quiz updates."""
    class Meta:
        model = Quiz
        fields = ['title', 'description']


class QuizCreateRequestSerializer(serializers.Serializer):
    """Serializer for quiz creation requests."""
    url = serializers.URLField(required=True)

    def validate(self, attrs):
        """Add source_url to the validated data."""
        attrs['source_url'] = attrs['url']
        return attrs
