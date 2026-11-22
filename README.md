# Email Spam Filtering Engine

A Django REST Framework backend for a website contact form. Every submission is scored by a
machine-learning spam classifier. Clean messages are forwarded to the site owner by email through
[Resend](https://resend.com). Spam is stored but not forwarded. All submissions can be reviewed
in the Django admin.

> **About this release.** This repository is the public edition of a private project that ran in
> production as the spam-filtering backend for my website's contact form. In production it screened
> every incoming message with a machine-learning classifier, so real enquiries reached my inbox and
> spam was quietly filtered out. For this release, all credentials, personal data and
> deployment-specific infrastructure have been removed and replaced with documented placeholders.
> The engine, trained model, API and test suite are the same ones that ran in production, now set up
> to run locally in a few minutes.

The project is set up to run locally with SQLite. Clone it, create a `.env` and run the dev server.

## Features

- **Contact submission API** (`POST /api/contact/submit/`) with input validation and normalisation
- **ML spam scoring** with a pre-trained scikit-learn pipeline (TF-IDF + Logistic Regression)
- **Configurable spam threshold** (`SPAM_THRESHOLD`, default `0.70`)
- **Honeypot field**: requests that fill the hidden `website` field are silently accepted and discarded
- **Email notifications** for clean messages via Resend, using an HTML template with a reply-to set to the sender
- **Stored audit trail**: every scored submission is saved with its score, status, client IP and user agent
- **Django admin** with colour-coded spam scores and bulk "mark as ham / mark as spam" actions
- **Health check endpoint** (`GET /api/health/`)
- **Interactive API docs**: Swagger UI and ReDoc, generated from the code by drf-spectacular (OpenAPI 3)
- **CI** with GitHub Actions (system checks, migration check, tests, flake8), run manually on demand

## How classification works

1. **Validation** (`contact/serializers.py`). `name` is stripped and must be at least 2 characters.
   `email` must be a valid address and is stripped and lower-cased. `message` is stripped and must be
   10–5000 characters. Invalid input returns `400` with the field errors.
2. **Honeypot** (`contact/views.py`). If the request contains a non-empty `website` field, the API
   returns `200 {"success": true}` and saves nothing.
3. **Scoring** (`contact/ml_engine.py`). The message text goes to the model's `predict_proba`, and the
   probability of the spam class (index 1) is rounded to 4 decimals. The model is loaded from
   `MODEL_PATH` with `joblib` on first use and cached in memory for later requests.
   - If the model file doesn't exist, or scoring raises an error, the score falls back to `0.0`,
     so every message is treated as clean.
4. **Decision**. A message is spam when `score >= SPAM_THRESHOLD`.
5. **Persistence**. A `ContactSubmission` row is created with status `spam` or `accepted`.
6. **Notification** (`contact/email_service.py`). For clean messages only, the notification email is
   sent through Resend and `email_sent` is recorded on the submission. If `RESEND_API_KEY` is not
   set, sending is skipped with a logged warning and `email_sent` stays `False`.
7. **Response**. Both clean and spam submissions return `201 {"success": true}`, so senders can't
   tell whether they were flagged.

The bundled model is `models/spam_classifier_v1.joblib`, a pickled scikit-learn `Pipeline`. It is
stored with **Git LFS**. This repository doesn't include training code. The `TrainingDataset` and
`ModelVersion` models (visible in the admin) are there to record labelled data and model versions.

> ⚠️ `.joblib` files are pickles. Loading one runs code from it, so only load model files you trust.

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.12+ (developed and tested on 3.14) |
| Web framework | Django 6.0.2, Django REST Framework 3.16.1 |
| ML | scikit-learn 1.8.0, joblib, NumPy, SciPy |
| Email | Resend (Python SDK 2.22.0) |
| Database | SQLite |
| Config | python-dotenv |
| CORS | django-cors-headers |
| API docs | drf-spectacular (OpenAPI 3, Swagger UI, ReDoc) |
| CI | GitHub Actions |

## Project structure

```
.
├── contact/                      # The contact/spam-filtering app
│   ├── admin.py                  # Admin for submissions, training data, model versions
│   ├── email_service.py          # Resend notification email
│   ├── ml_engine.py              # Model loading, caching and scoring
│   ├── models.py                 # ContactSubmission, TrainingDataset, ModelVersion
│   ├── serializers.py            # Input validation
│   ├── tests.py                  # Test suite
│   ├── urls.py                   # /api/contact/submit/, /api/health/
│   ├── views.py                  # ContactSubmitView, HealthCheckView
│   └── migrations/
├── core/                         # Django project (settings, root URLs, WSGI/ASGI)
├── models/
│   └── spam_classifier_v1.joblib # Pre-trained classifier (Git LFS)
├── templates/emails/
│   └── contact_notification.html # Notification email template
├── .github/workflows/django-ci.yml # Optional CI (manual trigger only)
├── .env.example                  # Template for your .env
├── manage.py
└── requirements.txt
```

## Setup

### 1. Clone (with Git LFS)

The model file is stored in Git LFS. Install [Git LFS](https://git-lfs.com) before cloning, or the
model will be a small pointer file and every message will score `0.0`.

```bash
git lfs install
git clone <repo-url>
cd email-spam-filtering-engine
git lfs pull
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create your `.env`

The `.env` file is **not** in the repository and must never be committed (it's in `.gitignore`).
Create it from the template:

```bash
cp .env.example .env
```

Then edit `.env` and supply real values:

- `SECRET_KEY`: **required**. The app won't start without it. Generate one with:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DEBUG=True` and `ALLOWED_HOSTS=localhost,127.0.0.1` are already set for local use. Host names
  go in `ALLOWED_HOSTS` **without a port** (`127.0.0.1`, not `127.0.0.1:8000`).
- *Optional:* `RESEND_API_KEY`, `OWNER_EMAIL`, `FROM_EMAIL` if you want notification emails to be
  sent. `FROM_EMAIL` must use a domain you have verified in Resend. If `RESEND_API_KEY` is left
  empty, messages are still scored and saved, and emails are skipped.
- *Optional:* `CORS_ALLOWED_ORIGIN`: the origin of a local frontend that will call the API
  (default `http://localhost:3000`).

`.env` can be placed in the project root or in `core/`. `python-dotenv` searches upward from
`core/settings.py`. See [Environment variables](#environment-variables) for the full list.

#### Placeholders you need to replace

This repository contains **no real keys, email addresses or domains**. Every sensitive value is a
dummy placeholder that you replace with your own:

| Placeholder | Where | Replace with | Needed for |
|---|---|---|---|
| `replace-with-a-long-random-secret-key` | `.env`: `SECRET_KEY` | Your own random key (generate it with the command above) | Always. The placeholder works for local testing, but use your own key. |
| *(empty)* | `.env`: `RESEND_API_KEY` | Your API key from the [Resend dashboard](https://resend.com) | Sending notification emails |
| `user@example.com` | `.env`: `OWNER_EMAIL` (also the default in `core/settings.py` and `contact/email_service.py`) | The inbox that should receive contact messages | Sending notification emails |
| `Jane Doe <noreply@example.org>` | `.env`: `FROM_EMAIL` (also the default in `contact/email_service.py`) | `Your Name <noreply@your-domain>` on a domain verified in Resend | Sending notification emails |
| `http://localhost:3000` | `.env`: `CORS_ALLOWED_ORIGIN` (also the default in `core/settings.py`) | The URL of the frontend that calls the API | Calling the API from a browser app |
| `example.org` | `templates/emails/contact_notification.html`, footer text | Your site name or domain | Cosmetic: footer of the notification email |

Never commit your filled-in `.env`. It's listed in `.gitignore`.

### 4. Create the database

The SQLite database (`db.sqlite3`) is not in the repository. Running migrations creates it:

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
```

### 5. Run

Run commands from the project root, because `MODEL_PATH` is resolved relative to the current
directory.

```bash
python manage.py runserver
```

Then open:
- http://127.0.0.1:8000/ redirects to the Swagger UI at `/api/docs/`
- http://127.0.0.1:8000/api/ is the API (see [API endpoints](#api-endpoints))
- http://127.0.0.1:8000/admin/ is the Django admin (log in with the superuser from step 4)

> Python bytecode (`__pycache__/`, `*.pyc`) is generated automatically when the app runs. It is
> ignored by Git and shouldn't be committed.

### Troubleshooting

| Problem | Fix |
|---|---|
| `KeyError: 'SECRET_KEY'` on startup | `.env` is missing or has no `SECRET_KEY`. Repeat step 3. |
| `DisallowedHost ... add '127.0.0.1' to ALLOWED_HOSTS` | Set `ALLOWED_HOSTS=localhost,127.0.0.1` in `.env`, with host names only and no `:8000` |
| `no such table: contact_contactsubmission` | Run `python manage.py migrate` (step 4) |
| Every message scores `0.0` | The model file is missing or is only a Git LFS pointer. Run `git lfs pull` and start the server from the project root. |
| Admin pages have no styling | Set `DEBUG=True`. The dev server only serves static files in debug mode. |

## Environment variables

| Variable | Required | Default in code | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | none (startup fails if missing) | Django secret key |
| `DEBUG` | No | `True` | `True` enables debug mode. Any other value disables it. |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated host names, without ports |
| `CORS_ALLOWED_ORIGIN` | No | `http://localhost:3000` | Frontend origin allowed by CORS (`http://127.0.0.1:8000` is always allowed) |
| `RESEND_API_KEY` | For email | unset/empty → emails skipped | Resend API key |
| `OWNER_EMAIL` | For email | `user@example.com` | Address that receives notification emails |
| `FROM_EMAIL` | For email | `Jane Doe <noreply@example.org>` | Sender, in `Name <address>` format, on a Resend-verified domain |
| `SPAM_THRESHOLD` | No | `0.70` | Score at or above which a message is spam |
| `MODEL_PATH` | No | `models/spam_classifier_v1.joblib` | Path to the joblib model file |

## API documentation (Swagger)

With the server running (`python manage.py runserver`), interactive docs are available at:

| URL | What it is |
|---|---|
| http://127.0.0.1:8000/api/docs/ | **Swagger UI**: browse the endpoints and send requests with **Try it out** |
| http://127.0.0.1:8000/api/redoc/ | **ReDoc**: read-only reference view |
| http://127.0.0.1:8000/api/schema/ | Raw OpenAPI 3 schema (YAML; add `?format=json` for JSON) |

The schema is generated from the code: the request body comes from `ContactSubmissionSerializer`,
and the descriptions, responses and examples come from the `@extend_schema` decorators in
`contact/views.py`. To export it to a file:

```bash
python manage.py spectacular --validate --file schema.yaml
```

The Swagger UI and ReDoc pages load their JavaScript/CSS from a CDN, so the browser needs internet access.

## API endpoints

All responses are JSON.

### `POST /api/contact/submit/`

Submit a contact form message.

**Request**

```bash
curl -X POST http://127.0.0.1:8000/api/contact/submit/ \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Jane Doe",
        "email": "user@example.com",
        "message": "Hello, I would like to discuss a project with you."
      }'
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | required, ≥ 2 characters after trimming, max 100 |
| `email` | string | required, valid email, lower-cased |
| `message` | string | required, 10–5000 characters after trimming |
| `website` | string | honeypot. Leave empty or omit it (hide it from humans in your form). |

**Responses**

`201 Created` for an accepted or spam-flagged submission:

```json
{ "success": true }
```

`200 OK` when the honeypot is triggered (nothing is saved):

```json
{ "success": true }
```

`400 Bad Request` for validation errors:

```json
{
  "success": false,
  "errors": {
    "name": ["Name must be at least 2 characters."],
    "email": ["Enter a valid email address."],
    "message": ["Message must be at least 10 characters."]
  }
}
```

### `GET /api/health/`

```bash
curl http://127.0.0.1:8000/api/health/
```

```json
{
  "status": "ok",
  "ml_model": { "status": "loaded", "ready": true }
}
```

Note: the `ml_model` block is a fixed response. It doesn't check whether the model file actually
loaded.

### `/admin/`

The Django admin (requires a superuser) for:
- **Contact submissions**: search, filter by status, email-sent flag and date, colour-coded spam score
  (≥ 0.70 red, ≥ 0.40 amber, otherwise green), and bulk actions *Mark selected as HAM* / *Mark selected as SPAM*
  (which also record the reviewing admin's username).
- **Training datasets** and **Model versions**.

## Running tests

The suite (24 tests in `contact/tests.py`) covers models, serializer validation, the ML engine,
the email service, the API views and end-to-end flows. The ML model and the Resend API are mocked,
so no API key or network access is needed. A `SECRET_KEY` must still be set (for example via your `.env`).

```bash
python manage.py test
```

An optional GitHub Actions workflow (`.github/workflows/django-ci.yml`) runs `manage.py check`,
`makemigrations --check`, `migrate`, the tests and flake8. It does **not** run automatically on
pushes or pull requests. Start it manually from the repository's **Actions** tab → *Django CI* →
**Run workflow** (`workflow_dispatch`). It reads `SECRET_KEY` from the repository secret
`DJANGO_SECRET_KEY`, so add that secret before running it.
