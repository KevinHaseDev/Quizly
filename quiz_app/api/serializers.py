from rest_framework import serializers

from quiz_app.models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuestionCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer', 'created_at', 'updated_at']


class QuizSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Quiz
        fields = ['title', 'description']


class QuizCreateRequestSerializer(serializers.Serializer):
    url = serializers.URLField(required=True)

    def validate(self, attrs):
        attrs['source_url'] = attrs['url']
        return attrs
