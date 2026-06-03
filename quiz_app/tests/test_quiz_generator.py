import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from quiz_app.services.quiz_generator import (
    QuizGenerationAcquisitionError,
    QuizGenerationAIError,
    QuizGenerationServiceError,
    QuizGenerationTranscriptionError,
    QuizGenerationValidationError,
    QuizGenerationService,
    create_quiz_from_youtube_url,
)


VALID_STANDARD_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
VALID_SHORT_URL = 'https://youtu.be/dQw4w9WgXcQ'
INVALID_URL = 'https://example.com/video'

VALID_PAYLOAD = {
    'title': 'Test Quiz',
    'description': 'A test quiz.',
    'questions': [
        {
            'question_title': f'Question {i}',
            'question_options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
        }
        for i in range(10)
    ],
}


class ValidateUrlTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()

    def test_accepts_standard_youtube_url(self):
        result = self.service.validate_url(VALID_STANDARD_URL)
        self.assertEqual(result, VALID_STANDARD_URL)

    def test_accepts_short_youtube_url(self):
        result = self.service.validate_url(VALID_SHORT_URL)
        self.assertEqual(result, VALID_SHORT_URL)

    def test_rejects_non_youtube_url(self):
        with self.assertRaises(QuizGenerationValidationError):
            self.service.validate_url(INVALID_URL)

    def test_rejects_youtube_url_without_video_id(self):
        with self.assertRaises(QuizGenerationValidationError):
            self.service.validate_url('https://www.youtube.com/watch')


class AcquireAudioTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()
        self.mock_info = {
            'title': 'Test Video',
            'duration': 60,
            'uploader': 'Tester',
            'thumbnail': 'https://img.example.com/thumb.jpg',
            'formats': [
                {'vcodec': 'none', 'url': 'https://audio.example.com/best.m4a', 'abr': 128},
                {'vcodec': 'none', 'url': 'https://audio.example.com/low.m4a', 'abr': 64},
            ],
        }

    @patch.object(QuizGenerationService, '_fetch_media_info')
    def test_returns_audio_reference_with_best_stream(self, mock_fetch):
        mock_fetch.return_value = self.mock_info
        result = self.service.acquire_audio(VALID_STANDARD_URL)
        self.assertEqual(result['audio_url'], 'https://audio.example.com/best.m4a')
        self.assertEqual(result['metadata']['title'], 'Test Video')

    @patch.object(QuizGenerationService, '_fetch_media_info')
    def test_raises_acquisition_error_on_yt_dlp_failure(self, mock_fetch):
        mock_fetch.side_effect = QuizGenerationAcquisitionError('yt-dlp failed')
        with self.assertRaises(QuizGenerationAcquisitionError):
            self.service.acquire_audio(VALID_STANDARD_URL)

    @patch.object(QuizGenerationService, '_fetch_media_info')
    def test_raises_if_no_audio_url_resolved(self, mock_fetch):
        mock_fetch.return_value = {'formats': [], 'url': None}
        with self.assertRaises(QuizGenerationAcquisitionError):
            self.service.acquire_audio(VALID_STANDARD_URL)

    def test_fetch_media_info_raises_on_yt_dlp_exception(self):
        with patch('yt_dlp.YoutubeDL') as mock_ydl_cls:
            mock_ydl_cls.return_value.__enter__.return_value.extract_info.side_effect = Exception('network error')
            with self.assertRaises(QuizGenerationAcquisitionError):
                self.service._fetch_media_info(VALID_STANDARD_URL)

    @patch.object(QuizGenerationService, '_fetch_media_info')
    def test_falls_back_to_generic_url_when_no_audio_only_formats(self, mock_fetch):
        mock_fetch.return_value = {'formats': [], 'url': 'https://fallback.example.com/stream'}
        result = self.service.acquire_audio(VALID_STANDARD_URL)
        self.assertEqual(result['audio_url'], 'https://fallback.example.com/stream')


class TranscribeAudioTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()
        self.audio_ref = {'audio_url': 'https://audio.example.com/stream.m4a'}

    @patch.object(QuizGenerationService, '_get_whisper_model')
    def test_returns_transcript_text(self, mock_get_model):
        mock_get_model.return_value.transcribe.return_value = {'text': '  Hello World  '}
        result = self.service.transcribe_audio(self.audio_ref)
        self.assertEqual(result, 'Hello World')

    def test_raises_if_no_audio_url(self):
        with self.assertRaises(QuizGenerationTranscriptionError):
            self.service.transcribe_audio({'audio_url': None})

    @patch.object(QuizGenerationService, '_get_whisper_model')
    def test_raises_on_whisper_exception(self, mock_get_model):
        mock_get_model.return_value.transcribe.side_effect = RuntimeError('whisper failed')
        with self.assertRaises(QuizGenerationTranscriptionError):
            self.service.transcribe_audio(self.audio_ref)

    @patch.object(QuizGenerationService, '_get_whisper_model')
    def test_raises_on_empty_transcript(self, mock_get_model):
        mock_get_model.return_value.transcribe.return_value = {'text': '   '}
        with self.assertRaises(QuizGenerationTranscriptionError):
            self.service.transcribe_audio(self.audio_ref)


class GenerateQuizWithAITests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()

    @patch.object(QuizGenerationService, '_request_quiz_from_gemini')
    def test_returns_normalised_quiz_payload(self, mock_request):
        mock_request.return_value = json.dumps(VALID_PAYLOAD)
        result = self.service.generate_quiz_with_ai('transcript', VALID_STANDARD_URL)
        self.assertEqual(result['title'], 'Test Quiz')
        self.assertEqual(len(result['questions']), 10)

    @patch.object(QuizGenerationService, '_request_quiz_from_gemini')
    def test_raises_ai_error_on_invalid_json(self, mock_request):
        mock_request.return_value = 'not json'
        with self.assertRaises(QuizGenerationAIError):
            self.service.generate_quiz_with_ai('transcript', VALID_STANDARD_URL)

    @patch.object(QuizGenerationService, '_request_quiz_from_gemini')
    def test_raises_if_gemini_request_fails(self, mock_request):
        mock_request.side_effect = QuizGenerationAIError('Gemini failed')
        with self.assertRaises(QuizGenerationAIError):
            self.service.generate_quiz_with_ai('transcript', VALID_STANDARD_URL)


class GeminiClientTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()

    def test_raises_without_api_key(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(QuizGenerationAIError):
                self.service._get_gemini_client()

    def test_raises_without_google_genai_package(self):
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            with patch('builtins.__import__', side_effect=ImportError('no module')):
                self.service._gemini_client = None
                with self.assertRaises(QuizGenerationAIError):
                    self.service._get_gemini_client()

    def test_returns_cached_client(self):
        mock_client = MagicMock()
        self.service._gemini_client = mock_client
        result = self.service._get_gemini_client()
        self.assertIs(result, mock_client)

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_request_quiz_raises_on_empty_response(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value.text = ''
        self.service._gemini_client = mock_client
        with self.assertRaises(QuizGenerationAIError):
            self.service._request_quiz_from_gemini('transcript', VALID_STANDARD_URL)

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_request_quiz_raises_on_gemini_exception(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception('API error')
        self.service._gemini_client = mock_client
        with self.assertRaises(QuizGenerationAIError):
            self.service._request_quiz_from_gemini('transcript', VALID_STANDARD_URL)


class ParseGeminiPayloadTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()

    def test_parses_plain_json(self):
        result = self.service._parse_gemini_quiz_payload(json.dumps(VALID_PAYLOAD))
        self.assertEqual(result['title'], 'Test Quiz')

    def test_strips_markdown_fences(self):
        wrapped = f'```json\n{json.dumps(VALID_PAYLOAD)}\n```'
        result = self.service._parse_gemini_quiz_payload(wrapped)
        self.assertEqual(result['title'], 'Test Quiz')

    def test_raises_on_invalid_json(self):
        with self.assertRaises(QuizGenerationAIError):
            self.service._parse_gemini_quiz_payload('not valid json')


class NormalizeQuizPayloadTests(TestCase):
    def setUp(self):
        self.service = QuizGenerationService()

    def test_returns_clean_payload(self):
        result = self.service._normalize_quiz_payload(VALID_PAYLOAD, VALID_STANDARD_URL)
        self.assertEqual(result['title'], 'Test Quiz')
        self.assertEqual(len(result['questions']), 10)

    def test_raises_on_non_dict_payload(self):
        with self.assertRaises(QuizGenerationAIError):
            self.service._normalize_quiz_payload('not a dict', VALID_STANDARD_URL)

    def test_raises_when_no_valid_questions(self):
        payload = {'title': 'T', 'description': 'D', 'questions': []}
        with self.assertRaises(QuizGenerationAIError):
            self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)

    def test_uses_fallback_title_when_missing(self):
        payload = {**VALID_PAYLOAD, 'title': None}
        result = self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)
        self.assertEqual(result['title'], 'Generated Quiz')

    def test_uses_fallback_description_when_missing(self):
        payload = {**VALID_PAYLOAD, 'description': None}
        result = self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)
        self.assertIn(VALID_STANDARD_URL, result['description'])

    def test_skips_question_with_wrong_option_count(self):
        bad_question = {
            'question_title': 'Bad Q',
            'question_options': ['A', 'B'],
            'answer': 'A',
        }
        payload = {**VALID_PAYLOAD, 'questions': [bad_question]}
        with self.assertRaises(QuizGenerationAIError):
            self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)

    def test_skips_non_dict_question_items(self):
        payload = {**VALID_PAYLOAD, 'questions': ['not a dict']}
        with self.assertRaises(QuizGenerationAIError):
            self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)

    def test_falls_back_to_first_option_when_answer_not_in_options(self):
        question = {
            'question_title': 'Q1',
            'question_options': ['A', 'B', 'C', 'D'],
            'answer': 'X',
        }
        payload = {**VALID_PAYLOAD, 'questions': [question] * 10}
        result = self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)
        self.assertEqual(result['questions'][0]['answer'], 'A')

    def test_skips_question_without_title(self):
        question = {'question_options': ['A', 'B', 'C', 'D'], 'answer': 'A'}
        payload = {**VALID_PAYLOAD, 'questions': [question]}
        with self.assertRaises(QuizGenerationAIError):
            self.service._normalize_quiz_payload(payload, VALID_STANDARD_URL)


class ErrorHierarchyTests(TestCase):
    def test_acquisition_error_is_service_error(self):
        self.assertTrue(issubclass(QuizGenerationAcquisitionError, QuizGenerationServiceError))

    def test_transcription_error_is_service_error(self):
        self.assertTrue(issubclass(QuizGenerationTranscriptionError, QuizGenerationServiceError))

    def test_ai_error_is_service_error(self):
        self.assertTrue(issubclass(QuizGenerationAIError, QuizGenerationServiceError))


class CreateQuizFromYoutubeUrlTests(TestCase):
    @patch.object(QuizGenerationService, 'generate_from_url')
    def test_delegates_to_service(self, mock_generate):
        mock_generate.return_value = VALID_PAYLOAD
        result = create_quiz_from_youtube_url(VALID_STANDARD_URL)
        self.assertEqual(result, VALID_PAYLOAD)
        mock_generate.assert_called_once_with(VALID_STANDARD_URL)
