# Quizly Backend

Django REST API that generates quizzes from YouTube videos. The backend
transcribes a video's audio with Whisper AI and uses Google Gemini Flash to
produce a ten-question multiple-choice quiz, which is then stored and served
through a JWT-authenticated REST API.

## Tech Stack

| Component | Library |
|---|---|
| Framework | Django 6 + Django REST Framework |
| Authentication | `djangorestframework-simplejwt` (HTTP-only cookies) |
| Video download | `yt-dlp` |
| Transcription | OpenAI Whisper (local) |
| Quiz generation | Google Gemini Flash (`google-genai`) |
| Database | SQLite (development) |

## Prerequisites

- **Python 3.11+**
- **FFmpeg** — required by Whisper for audio processing.  
  Install via your package manager or download from https://ffmpeg.org/download.html  
  and make sure `ffmpeg` is available on your system `PATH`.
- A **Google Gemini API key** (free tier is sufficient).  
  Obtain one at https://aistudio.google.com/app/apikey

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd quizly_test
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
GOOGLE_API_KEY=your-gemini-api-key
```

Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional, for Admin panel)

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/`.  
The admin panel is available at `http://127.0.0.1:8000/admin/`.

## API Endpoints

### Authentication

| Method | URL | Description | Auth required |
|---|---|---|---|
| `POST` | `/api/register/` | Register a new user | No |
| `POST` | `/api/login/` | Login and receive JWT cookies | No |
| `POST` | `/api/logout/` | Logout and blacklist tokens | Yes |
| `POST` | `/api/token/refresh/` | Refresh access token from cookie | No |

Authentication uses HTTP-only cookies (`access_token`, `refresh_token`).

### Quizzes

| Method | URL | Description | Auth required |
|---|---|---|---|
| `GET` | `/api/quizzes/` | List all quizzes of the authenticated user | Yes |
| `POST` | `/api/quizzes/` | Generate a new quiz from a YouTube URL | Yes |
| `GET` | `/api/quizzes/{id}/` | Retrieve a specific quiz | Yes |
| `PATCH` | `/api/quizzes/{id}/` | Update title and/or description | Yes |
| `DELETE` | `/api/quizzes/{id}/` | Delete a quiz permanently | Yes |

#### Quiz creation request body

```json
{ "url": "https://www.youtube.com/watch?v=example" }
```

Only YouTube URLs are accepted (standard `watch?v=` and short `youtu.be/` formats).

## Running Tests

```bash
python manage.py test
```

With coverage:

```bash
pip install coverage
coverage run manage.py test
coverage report
```

## Notes

- The Whisper `turbo` model (~1.5 GB) is downloaded automatically on first use and
  cached in `~/.cache/whisper/`.
- Quiz generation runs synchronously during the HTTP request. For production use a
  task queue (e.g. Celery) is recommended.
- The database file `db.sqlite3` is excluded from version control.
