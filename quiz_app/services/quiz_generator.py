import json
import os
from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp


class QuizGenerationValidationError(ValueError):
    """Raised when the input URL is not a supported YouTube URL."""


class QuizGenerationServiceError(RuntimeError):
    """Base class for errors that occur during quiz generation."""


class QuizGenerationAcquisitionError(QuizGenerationServiceError):
    """Raised when video metadata or audio data cannot be fetched."""


class QuizGenerationTranscriptionError(QuizGenerationServiceError):
    """Raised when audio cannot be transcribed with Whisper."""


class QuizGenerationAIError(QuizGenerationServiceError):
    """Raised when quiz generation with Gemini cannot be completed."""


class QuizGenerationService:
    """Pipeline that turns a YouTube URL into a quiz.

    Steps: validate URL → resolve audio stream (yt-dlp) →
    transcribe (Whisper) → generate quiz (Gemini).
    """

    def __init__(self, whisper_model_name='turbo', gemini_model_name='gemini-3.5-flash'):
        self.whisper_model_name = whisper_model_name
        self.gemini_model_name = gemini_model_name
        self._whisper_model = None
        self._gemini_client = None

    def generate_from_url(self, video_url):
        """Run the full pipeline and return a quiz payload dict."""
        normalized_url = self.validate_url(video_url)
        audio_reference = self.acquire_audio(normalized_url)
        transcript = self.transcribe_audio(audio_reference)
        return self.generate_quiz_with_ai(transcript, normalized_url)

    def validate_url(self, video_url):
        """Return the URL unchanged if it is a valid YouTube URL."""
        parsed = urlparse(video_url)
        host = parsed.netloc.lower()
        is_short = host in {'youtu.be', 'www.youtu.be'} and bool(parsed.path.strip('/'))
        is_standard = host.endswith('youtube.com') and bool(parse_qs(parsed.query).get('v'))
        if not (is_short or is_standard):
            raise QuizGenerationValidationError('Only YouTube URLs are supported.')
        return video_url

    def acquire_audio(self, video_url):
        """Resolve the best audio stream URL and metadata with yt-dlp."""
        info = self._fetch_media_info(video_url)
        audio_url = self._resolve_audio_url(info)
        if not audio_url:
            raise QuizGenerationAcquisitionError('No audio stream available for this video.')
        return {
            'video_url': video_url,
            'audio_url': audio_url,
            'metadata': {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
            },
        }

    def transcribe_audio(self, audio_reference):
        """Transcribe the resolved audio source with Whisper."""
        audio_url = audio_reference.get('audio_url')
        if not audio_url:
            raise QuizGenerationTranscriptionError('No audio source available for transcription.')
        try:
            result = self._get_whisper_model().transcribe(audio_url)
        except (Exception, SystemExit) as exc:
            raise QuizGenerationTranscriptionError(
                'Could not transcribe audio with Whisper.') from exc
        transcript = (result.get('text') or '').strip()
        if not transcript:
            raise QuizGenerationTranscriptionError('Whisper returned an empty transcript.')
        return transcript

    def generate_quiz_with_ai(self, transcript, video_url):
        """Generate and return a quiz payload dict from the transcript."""
        response_text = self._request_quiz_from_gemini(transcript, video_url)
        payload = self._parse_gemini_quiz_payload(response_text)
        return self._normalize_quiz_payload(payload, video_url)

    def _request_quiz_from_gemini(self, transcript, video_url):
        """Send the transcript to Gemini and return the raw response text."""
        prompt = self._build_quiz_prompt(transcript, video_url)
        try:
            response = self._get_gemini_client().models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
            )
        except (Exception, SystemExit) as exc:
            raise QuizGenerationAIError('Gemini request failed.') from exc
        response_text = (getattr(response, 'text', None) or '').strip()
        if not response_text:
            raise QuizGenerationAIError('Gemini response did not include text output.')
        return response_text

    def _get_gemini_client(self):
        """Return a cached Gemini client, initialised on first call."""
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
        """Return the prompt string sent to Gemini."""
        clipped = transcript[:12000]
        return (
            'Create a quiz as strict JSON (no markdown).\n'
            'Use keys: title, description, questions.\n'
            'questions must be a list of 10 objects with keys: '
            'question_title, question_options, answer.\n'
            'question_options must contain exactly 4 answer options.\n'
            'answer must match one value from question_options.\n'
            f'Video URL: {video_url}\n\nTranscript:\n{clipped}'
        )

    def _parse_gemini_quiz_payload(self, response_text):
        """Parse the Gemini response text into a dict."""
        cleaned = response_text.strip().strip('`')
        cleaned = cleaned.replace('json\n', '', 1).replace('JSON\n', '', 1)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise QuizGenerationAIError('Gemini did not return valid JSON.') from exc

    def _normalize_quiz_payload(self, payload, video_url):
        """Validate and normalise the Gemini quiz payload into a clean dict."""
        if not isinstance(payload, dict):
            raise QuizGenerationAIError('Gemini returned an unexpected payload.')
        questions = self._normalize_questions(payload.get('questions', []))
        if not questions:
            raise QuizGenerationAIError('Gemini did not return any usable questions.')
        return {
            'title': str(payload.get('title') or 'Generated Quiz').strip(),
            'description': str(
                payload.get('description') or f'Generated from {video_url}').strip(),
            'questions': questions,
        }

    def _normalize_questions(self, raw_questions):
        """Return a list of normalised question dicts, skipping invalid items."""
        if not isinstance(raw_questions, list):
            return []
        return [q for q in (self._normalize_question(item) for item in raw_questions) if q]

    def _normalize_question(self, item):
        """Return a normalised question dict or None if the item is unusable."""
        if not isinstance(item, dict):
            return None
        question_title = item.get('question_title')
        raw_options = item.get('question_options')
        if not question_title or not isinstance(raw_options, list):
            return None
        options = [str(o).strip() for o in raw_options if str(o).strip()]
        if len(options) != 4:
            return None
        answer = str(item.get('answer', '')).strip()
        return {
            'question_title': str(question_title).strip(),
            'question_options': options,
            'answer': answer if answer in options else options[0],
        }

    def _get_whisper_model(self):
        """Return a cached Whisper model, loaded on first call."""
        if self._whisper_model is None:
            try:
                self._whisper_model = whisper.load_model(self.whisper_model_name).to('cuda')
            except Exception:  # pragma: no cover - no GPU available
                self._whisper_model = whisper.load_model(self.whisper_model_name)
        return self._whisper_model

    def _fetch_media_info(self, video_url):
        """Fetch video metadata and format info from YouTube via yt-dlp."""
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
        except (Exception, SystemExit) as exc:
            raise QuizGenerationAcquisitionError(
                'Could not fetch YouTube audio metadata.') from exc

    def _resolve_audio_url(self, info):
        """Return the best audio-only stream URL from yt-dlp info."""
        formats = info.get('formats') or []
        audio_only = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
        if not audio_only:
            return info.get('url')
        return max(audio_only, key=lambda f: f.get('abr') or 0)['url']


def create_quiz_from_youtube_url(video_url):
    """Entrypoint used by API views."""
    return QuizGenerationService().generate_from_url(video_url)
