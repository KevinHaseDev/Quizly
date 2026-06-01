# Quizly Backend

Django REST backend for Quizly.

## Tech Stack

- Python 3.14+
- Django 6
- Django REST Framework
- SimpleJWT (HTTP-only cookie auth)
- yt-dlp (YouTube audio source extraction)
- openai-whisper (transcription)
- google-genai (Gemini Flash quiz generation)

## Features

- User registration and login
- JWT authentication with HTTP-only cookies (`access_token`, `refresh_token`)
- Refresh-token rotation endpoint
- Logout with refresh-token blacklist
- Quiz CRUD for authenticated owners
- Quiz creation from YouTube URLs

## Required External Dependencies

### FFMPEG (required)

Whisper processing requires a globally available `ffmpeg` binary.

Verify installation:

```bash
ffmpeg -version
```

## Environment Variables

Create a `.env` file in the project root.

```env
SECRET_KEY=your-django-secret-key
GOOGLE_API_KEY=your-gemini-api-key
```

Notes:
- `GOOGLE_API_KEY` is required for Gemini quiz generation.
- In local development, missing auth cookie settings are handled with safe defaults in code.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Database Setup

```bash
python manage.py migrate
python manage.py createsuperuser
```

## Run Development Server

```bash
python manage.py runserver
```

Backend base URL:

- `http://127.0.0.1:8000/`

## API Endpoints

### Authentication

- `POST /api/register/`
- `POST /api/login/`
- `POST /api/logout/`
- `POST /api/token/refresh/`

### Quiz Management

- `POST /api/quizzes/`
- `GET /api/quizzes/`
- `GET /api/quizzes/{id}/`
- `PATCH /api/quizzes/{id}/`
- `DELETE /api/quizzes/{id}/`

## Admin

Django admin is enabled and quiz entities are registered:

- `Quiz`
- `Question`

Login:

- `http://127.0.0.1:8000/admin/`

## Tests

Run all tests:

```bash
python manage.py test
```

## Coverage

Run coverage and enforce a minimum threshold:

```bash
coverage run manage.py test
coverage report --fail-under=95
```

Generate HTML report:

```bash
coverage html
```

## Important Submission Notes

- Submit backend as a dedicated repository.
- Do not commit SQLite database files.
- Keep `requirements.txt` complete and up to date.
