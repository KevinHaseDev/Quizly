from urllib.parse import parse_qs, urlparse

from rest_framework import serializers

from quiz_app.models import Question, Quiz


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'created_at', 'updated_at']


class QuizSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id',
            'owner',
            'video_url',
            'title',
            'description',
            'created_at',
            'updated_at',
            'questions',
        ]


class QuizCreateRequestSerializer(serializers.Serializer):
    url = serializers.URLField()

    def validate_url(self, value):
        parsed_url = urlparse(value)
        host = parsed_url.netloc.lower()
        if host in {'youtu.be', 'www.youtu.be'} and parsed_url.path.strip('/'):
            return value
        if host.endswith('youtube.com') and parse_qs(parsed_url.query).get('v'):
            return value
        raise serializers.ValidationError('Only YouTube URLs are supported.')
