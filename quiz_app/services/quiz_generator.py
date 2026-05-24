from urllib.parse import parse_qs, urlparse

import whisper
import yt_dlp


class QuizGenerationValidationError(ValueError):
    """Raised when quiz generation input data is invalid."""


class QuizGenerationAcquisitionError(RuntimeError):
    """Raised when video metadata/audio data cannot be fetched."""


class QuizGenerationTranscriptionError(RuntimeError):
    """Raised when audio cannot be transcribed with Whisper."""


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

    def __init__(self, whisper_model_name='turbo'):
        self.whisper_model_name = whisper_model_name
        self._whisper_model = None

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
