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

The project runs locally with SQLite. No API keys are needed to try it: the spam classifier, the API,
the interactive docs and the admin all work with the placeholder configuration. Add your own
[Resend](https://resend.com) key only if you also want notification emails to be sent.

## Contents

- [Features](#features)
- [How classification works](#how-classification-works)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Setup, step by step](#setup-step-by-step)
- [Try it out](#try-it-out)
- [Sending real emails (optional)](#sending-real-emails-optional)
- [Troubleshooting](#troubleshooting)
- [Environment variables](#environment-variables)
- [API documentation (Swagger)](#api-documentation-swagger)
- [API endpoints](#api-endpoints)
- [Running tests](#running-tests)

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

> **Security note:** `.joblib` files are pickles. Loading one runs code from it, so only load model
> files you trust.

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

## Quick start

For readers who already have Python 3.12+, Git and Git LFS installed (macOS/Linux shown; see the
step-by-step guide below for Windows):

```bash
git lfs install
git clone https://github.com/pridem755/email-spam-filtering-backend.git
cd email-spam-filtering-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/. It redirects to the interactive API docs.

## Setup, step by step

### Prerequisites

| Tool | Version | Check with | Get it |
|---|---|---|---|
| Python | **3.12 or newer** (Django 6 requires it) | `python --version` (macOS/Linux: `python3 --version`) | https://www.python.org/downloads/ |
| Git | any recent version | `git --version` | https://git-scm.com/downloads |
| Git LFS | any recent version | `git lfs version` | https://git-lfs.com (included with Git for Windows) |

An internet connection is needed to install the packages and to load the Swagger/ReDoc pages.

### 1. Get the code (with the model file)

The trained model (`models/spam_classifier_v1.joblib`, about 470 KB) is stored with **Git LFS**.
Without Git LFS you only get a small text pointer instead of the model. The app still starts, but
every message then scores `0.0` and is treated as clean.

```bash
git lfs install
git clone https://github.com/pridem755/email-spam-filtering-backend.git
cd email-spam-filtering-backend
git lfs pull
```

Check that the real model was downloaded:

```bash
git lfs ls-files
```

The line for `models/spam_classifier_v1.joblib` should contain an asterisk (`*`). A dash (`-`)
means only the pointer was downloaded. In that case, run `git lfs pull` again.

> **Downloaded the ZIP instead of cloning?** GitHub's "Download ZIP" button may contain only the
> LFS pointer. If `models/spam_classifier_v1.joblib` is only a few hundred bytes, download the model
> on its own from the repository page (open the file on GitHub and click **Download raw file**) and
> put it in the `models/` folder. Alternatively, clone with Git as shown above.

All remaining commands are run **from this project folder** (the one containing `manage.py`).

### 2. Create a virtual environment and install dependencies

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
py -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (Command Prompt)**

```bat
py -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

When the environment is active, your prompt starts with `(venv)`. Activate it again in every new
terminal before running the project.

### 3. Create your `.env` file

Settings are read from a `.env` file that you create from the template. It's listed in
`.gitignore`, so it is never committed.

| Shell | Command |
|---|---|
| macOS / Linux / Git Bash | `cp .env.example .env` |
| Windows PowerShell | `Copy-Item .env.example .env` |
| Windows Command Prompt | `copy .env.example .env` |

The template works as is for local testing. To use your own secret key (recommended), generate
one and paste it into `SECRET_KEY=` in `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Notes:
- `DEBUG=True` and `ALLOWED_HOSTS=localhost,127.0.0.1` are already set for local use. Host names
  go in `ALLOWED_HOSTS` **without a port** (`127.0.0.1`, not `127.0.0.1:8000`).
- `RESEND_API_KEY` is empty on purpose. Messages are still scored and saved, and emails are skipped.
  See [Sending real emails](#sending-real-emails-optional).
- `CORS_ALLOWED_ORIGIN` only matters if a browser frontend calls the API (default
  `http://localhost:3000`).
- `.env` can be placed in the project root or in `core/`. See
  [Environment variables](#environment-variables) for the full list.

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

Never commit your filled-in `.env`.

### 4. Create the database

The SQLite database (`db.sqlite3`) is not in the repository. Running migrations creates it:

```bash
python manage.py migrate
```

To use the Django admin, also create an admin account (you'll be asked for a username, email and
password; the email can be left blank):

```bash
python manage.py createsuperuser
```

### 5. Run the server

```bash
python manage.py runserver
```

Leave this terminal running and open:

| URL | What you'll see |
|---|---|
| http://127.0.0.1:8000/ | Redirects to the Swagger UI |
| http://127.0.0.1:8000/api/docs/ | Swagger UI: interactive API docs |
| http://127.0.0.1:8000/api/redoc/ | ReDoc: read-only API reference |
| http://127.0.0.1:8000/admin/ | Django admin (log in with the account from step 4) |

Stop the server with `Ctrl+C`. If port 8000 is already in use, run it on another port, e.g.
`python manage.py runserver 8001`.

> Python bytecode (`__pycache__/`, `*.pyc`) is generated automatically when the app runs. It is
> ignored by Git and shouldn't be committed.

## Try it out

The easiest way is the Swagger UI:

1. Open http://127.0.0.1:8000/api/docs/.
2. Expand **POST /api/contact/submit/** and click **Try it out**.
3. Edit the example body and click **Execute**.
4. Open http://127.0.0.1:8000/admin/ → **Contact submissions** to see the stored message, its spam
   score and its status (`accepted` or `spam`).

Try a normal message and a spammy one (for example *"URGENT!!! You WON a FREE cash prize, click
here now!!!"*) and compare their scores in the admin.

From a terminal:

**macOS / Linux / Git Bash**

```bash
curl -X POST http://127.0.0.1:8000/api/contact/submit/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "user@example.com", "message": "Hello, I would like to discuss a project with you."}'
```

**Windows PowerShell**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/contact/submit/ `
  -ContentType "application/json" `
  -Body '{"name": "Jane Doe", "email": "user@example.com", "message": "Hello, I would like to discuss a project with you."}'
```

The response is `{"success": true}` for both clean and spam messages. The classification is only
visible in the admin and the server log.

## Sending real emails (optional)

Clean messages are emailed to you through [Resend](https://resend.com). To enable it:

1. Create a free Resend account.
2. Add and verify a domain you own under **Domains** (Resend shows the DNS records to add).
3. Create an API key under **API Keys** (*Sending access* is enough).
4. Fill in `.env`:
   ```
   RESEND_API_KEY=re_...your key...
   OWNER_EMAIL=you@your-inbox.com
   FROM_EMAIL=Your Name <noreply@your-verified-domain.com>
   ```
5. Restart `python manage.py runserver` and submit a clean message.

Whether sending succeeded is recorded in the submission's **Email sent** field in the admin. If it
failed, the server log shows the reason.

## Troubleshooting

| Problem | Fix |
|---|---|
| `KeyError: 'SECRET_KEY'` on startup | `.env` is missing or has no `SECRET_KEY`. Repeat step 3 and run commands from the project folder. |
| `ModuleNotFoundError: No module named 'django'` | The virtual environment isn't active. Activate it (step 2) and try again. |
| PowerShell: `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt with `venv\Scripts\activate.bat`. |
| `python` is not recognised (Windows) | Use `py` instead of `python`, or reinstall Python with **Add python.exe to PATH** ticked. |
| `pip install` fails with `No matching distribution found for Django==6.0.2` (or numpy/scipy build errors) | Your Python is too old. Check `python --version`, install Python 3.12 or newer, and recreate the virtual environment. |
| `git: 'lfs' is not a git command` | Install Git LFS (https://git-lfs.com), then run `git lfs install` and `git lfs pull`. |
| Every message scores `0.0`, log shows `Machine Learning scoring error` | The model file is only a Git LFS pointer. See step 1, and start the server from the project folder. |
| `DisallowedHost ... add '127.0.0.1' to ALLOWED_HOSTS` | Set `ALLOWED_HOSTS=localhost,127.0.0.1` in `.env`, with host names only and no `:8000`. |
| `no such table: contact_contactsubmission` | Run `python manage.py migrate` (step 4). |
| `Error: That port is already in use` | Stop the other server, or run `python manage.py runserver 8001`. |
| Admin pages have no styling | Set `DEBUG=True`. The dev server only serves static files in debug mode. |
| Swagger/ReDoc page is blank | These pages load their files from a CDN; check your internet connection. |
| Browser frontend gets a CORS error | Set `CORS_ALLOWED_ORIGIN` in `.env` to your frontend's exact origin (e.g. `http://localhost:5173`) and restart. |
| `email_sent` stays false | `RESEND_API_KEY` is empty, or Resend rejected the request (check the server log, the API key and that `FROM_EMAIL` uses a verified domain). |

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
| `MODEL_PATH` | No | `models/spam_classifier_v1.joblib` | Path to the joblib model file, relative to the folder you start the server from |

## API documentation (Swagger)

With the server running (`python manage.py runserver`), interactive docs are available at:

| URL | What it is |
|---|---|
| http://127.0.0.1:8000/api/docs/ | **Swagger UI**: browse the endpoints and send requests with **Try it out** |
| http://127.0.0.1:8000/api/redoc/ | **ReDoc**: read-only reference view |
| http://127.0.0.1:8000/api/schema/ | Raw OpenAPI 3 schema (YAML; add `?format=json` for JSON) |

The schema is generated from the code: the request body comes from `ContactSubmissionSerializer`,
and the descriptions, responses and examples come from the `@extend_schema` decorators in
`contact/views.py`. To export it to a file (for example to import into Postman):

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
so no API key or network access is needed. A `SECRET_KEY` must still be set (the placeholder in
`.env` is enough).

```bash
python manage.py test
```

Expected result: `Ran 24 tests ... OK`.

An optional GitHub Actions workflow (`.github/workflows/django-ci.yml`) runs `manage.py check`,
`makemigrations --check`, `migrate`, the tests and flake8. It does **not** run automatically on
pushes or pull requests. Start it manually from the repository's **Actions** tab → *Django CI* →
**Run workflow** (`workflow_dispatch`). It reads `SECRET_KEY` from the repository secret
`DJANGO_SECRET_KEY`, so add that secret before running it.
