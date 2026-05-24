from urllib.parse import parse_qs, urlparse


class QuizGenerationValidationError(ValueError):
    """Raised when quiz generation input data is invalid."""


class QuizGenerationService:
    """Mock-friendly pipeline for quiz generation.

    This service keeps integrations as placeholders for now. Real external
    implementations (yt-dlp/ffmpeg, Whisper, Gemini) can be plugged in later.
    """

    def generate_from_url(self, video_url):
        normalized_url = self.validate_url(video_url)
        audio_reference = self.acquire_audio(normalized_url)
        transcript = self.transcribe_audio(audio_reference)
        return self.generate_quiz_with_ai(transcript, normalized_url)

    def validate_url(self, video_url):
        parsed_url = urlparse(video_url)
        host = parsed_url.netloc.lower()

        is_short_url = host in {'youtu.be', 'www.youtu.be'} and bool(parsed_url.path.strip('/'))
        is_standard_url = host.endswith('youtube.com') and bool(parse_qs(parsed_url.query).get('v'))

        if not (is_short_url or is_standard_url):
            raise QuizGenerationValidationError('Only YouTube URLs are supported.')
        return video_url

    def acquire_audio(self, video_url):
        """Placeholder for audio retrieval from YouTube."""

        video_id = self._extract_video_id(video_url)
        return {
            'video_url': video_url,
            'video_id': video_id,
            'audio_path': f'mock://audio/{video_id}.mp3',
        }

    def transcribe_audio(self, audio_reference):
        """Placeholder for speech-to-text transcription."""

        return (
            'This is a placeholder transcript generated from '
            f"{audio_reference['audio_path']} for development and tests."
        )

    def generate_quiz_with_ai(self, transcript, video_url):
        """Placeholder for AI quiz generation from transcript text."""

        excerpt = transcript[:80].strip() or 'the video content'
        return {
            'title': 'Generated Quiz',
            'description': f'Generated from {video_url}',
            'questions': [
                {
                    'title': 'What is the main topic of this video?',
                    'description': f'Use transcript excerpt: {excerpt}',
                },
                {
                    'title': 'Which key detail is highlighted in the transcript?',
                    'description': 'Answer based on the generated transcript text.',
                },
                {
                    'title': 'What practical takeaway can be inferred?',
                    'description': 'Explain one actionable insight from the content.',
                },
            ],
        }

    def _extract_video_id(self, video_url):
        parsed_url = urlparse(video_url)
        host = parsed_url.netloc.lower()
        if host.endswith('youtube.com'):
            return parse_qs(parsed_url.query).get('v', ['video'])[0]
        return parsed_url.path.strip('/') or 'video'


def create_quiz_from_youtube_url(video_url):
    """Backward-compatible entrypoint used by API views."""

    service = QuizGenerationService()
    return service.generate_from_url(video_url)
