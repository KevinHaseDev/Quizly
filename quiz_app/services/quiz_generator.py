import json
import os
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp


class QuizGenerationValidationError(ValueError):
    """Raised when quiz generation input data is invalid."""


class QuizGenerationAcquisitionError(RuntimeError):
    """Raised when video metadata/audio data cannot be fetched."""


class QuizGenerationTranscriptionError(RuntimeError):
    """Raised when audio cannot be transcribed with Whisper."""


class QuizGenerationAIError(RuntimeError):
    """Raised when quiz generation with Gemini cannot be completed."""


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

    def __init__(self, whisper_model_name='turbo', gemini_model_name='gemini-3.5-flash'):
        self.whisper_model_name = whisper_model_name
        self.gemini_model_name = gemini_model_name
        self._whisper_model = None
        self._gemini_client = None

    def validate_url(self, video_url):
        parsed_url = urlparse(video_url)
        host = parsed_url.netloc.lower()

        is_short_url = host in {'youtu.be', 'www.youtu.be'} and bool(parsed_url.path.strip('/'))
        is_standard_url = host.endswith('youtube.com') and bool(parse_qs(parsed_url.query).get('v'))

        if not (is_short_url or is_standard_url):
            raise QuizGenerationValidationError('Only YouTube URLs are supported.')
        return video_url

    def acquire_audio(self, video_url):
        """Fetch audio source information and metadata with yt_dlp."""

        info = self._fetch_media_info(video_url)
        video_id = info.get('id') or self._extract_video_id(video_url)
        audio_url = self._resolve_audio_url(info)

        return {
            'video_url': video_url,
            'video_id': video_id,
            'audio_url': audio_url,
            'audio_path': audio_url or f'mock://audio/{video_id}.mp3',
            'metadata': {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
            },
        }

    def transcribe_audio(self, audio_reference):
        """Transcribe an audio source with Whisper."""

        transcription_source = self._get_transcription_source(audio_reference)
        if not transcription_source:
            raise QuizGenerationTranscriptionError('No audio source available for transcription.')

        try:
            model = self._get_whisper_model()
            result = model.transcribe(transcription_source)
        except Exception as exc:
            raise QuizGenerationTranscriptionError('Could not transcribe audio with Whisper.') from exc

        transcript_text = (result.get('text') or '').strip()
        if not transcript_text:
            raise QuizGenerationTranscriptionError('Whisper returned an empty transcript.')
        return transcript_text

    def generate_quiz_with_ai(self, transcript, video_url):
        """Generate quiz content from transcript with Gemini Flash."""

        try:
            response_text = self._request_quiz_from_gemini(transcript, video_url)
            payload = self._parse_gemini_quiz_payload(response_text)
            return self._normalize_quiz_payload(payload, video_url, transcript)
        except QuizGenerationAIError:
            return self._build_fallback_quiz_payload(video_url, transcript)

    def _request_quiz_from_gemini(self, transcript, video_url):
        client = self._get_gemini_client()
        prompt = self._build_quiz_prompt(transcript, video_url)
        try:
            response = client.models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
            )
        except Exception as exc:
            raise QuizGenerationAIError('Gemini request failed.') from exc

        response_text = (getattr(response, 'text', None) or '').strip()
        if not response_text:
            raise QuizGenerationAIError('Gemini response did not include text output.')
        return response_text

    def _get_gemini_client(self):
        if self._gemini_client is not None:
            return self._gemini_client

        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise QuizGenerationAIError('GOOGLE_API_KEY is missing for Gemini requests.')

        try:
            from google import genai
        except Exception as exc:
            raise QuizGenerationAIError('google-genai package is not available.') from exc

        self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    def _build_quiz_prompt(self, transcript, video_url):
        clipped = transcript[:12000]
        return (
            'Create a quiz as strict JSON (no markdown). '\
            'Use keys: title, description, questions. '\
            'questions must be a list of 10 objects with keys: title, description. '\
            f'Video URL: {video_url}\n\n'
            f'Transcript:\n{clipped}'
        )

    def _parse_gemini_quiz_payload(self, response_text):
        cleaned = response_text.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.strip('`')
            cleaned = cleaned.replace('json\n', '', 1)
            cleaned = cleaned.replace('JSON\n', '', 1)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise QuizGenerationAIError('Gemini did not return valid JSON.') from exc

    def _normalize_quiz_payload(self, payload, video_url, transcript):
        title = payload.get('title') if isinstance(payload, dict) else None
        description = payload.get('description') if isinstance(payload, dict) else None
        questions = payload.get('questions') if isinstance(payload, dict) else None

        normalized_questions = []
        if isinstance(questions, list):
            for item in questions:
                if not isinstance(item, dict):
                    continue
                question_title = item.get('title') or item.get('question') or item.get('question_title')
                question_description = item.get('description') or item.get('explanation') or ''
                if question_title:
                    normalized_questions.append(
                        {
                            'title': str(question_title).strip(),
                            'description': str(question_description).strip(),
                        }
                    )

        if not normalized_questions:
            return self._build_fallback_quiz_payload(video_url, transcript)

        return {
            'title': str(title or 'Generated Quiz').strip(),
            'description': str(description or f'Generated from {video_url}').strip(),
            'questions': normalized_questions,
        }

    def _build_fallback_quiz_payload(self, video_url, transcript):
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

    def _get_transcription_source(self, audio_reference):
        return audio_reference.get('audio_path') or audio_reference.get('audio_url')

    def _get_whisper_model(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(self.whisper_model_name)
        return self._whisper_model

    def _fetch_media_info(self, video_url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'format': 'bestaudio/best',
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(video_url, download=False)
        except Exception as exc:
            raise QuizGenerationAcquisitionError('Could not fetch YouTube audio metadata.') from exc

    def _resolve_audio_url(self, info):
        requested_formats = info.get('requested_formats') or []
        for item in requested_formats:
            if item.get('vcodec') == 'none' and item.get('url'):
                return item['url']

        formats = info.get('formats') or []
        audio_only = [item for item in formats if item.get('vcodec') == 'none' and item.get('url')]
        if audio_only:
            best = max(audio_only, key=lambda item: item.get('abr') or 0)
            return best.get('url')

        return info.get('url')


def create_quiz_from_youtube_url(video_url):
    """Backward-compatible entrypoint used by API views."""

    service = QuizGenerationService()
    return service.generate_from_url(video_url)
