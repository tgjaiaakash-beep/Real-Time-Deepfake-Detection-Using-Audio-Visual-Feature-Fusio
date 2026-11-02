# AI Project Builder

A full-stack project-generation workspace: React/Vite frontend, FastAPI backend, configurable OpenAI-compatible AI provider, ZIP export, and GitHub OAuth publishing.

## Features
- Enter project requirements or upload PDF, DOCX, TXT, PNG, JPG, or WEBP specifications.
- Generate a project file map using a server-side AI provider.
- Browse and preview generated text files.
- Download a ZIP with a preserved folder structure.
- Connect GitHub using OAuth, create a repository or choose an existing one, and publish after explicit confirmation.
- SQLite project persistence and backend validation.

## Requirements
- Python 3.10+
- Node.js 18+
- An API key for an OpenAI-compatible `/chat/completions` endpoint for code generation.
- Optional GitHub OAuth App credentials for publishing.
- For image OCR, install the Tesseract OCR system package as well as the Python dependencies.

## Run locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `backend/.env`: set a long random `SECRET_KEY`, `AI_API_KEY`, and optionally `AI_BASE_URL` / `AI_MODEL`.

Start the API:
```bash
set -a; source .env; set +a
uvicorn app.main:app --reload --port 8000
```
On Windows PowerShell, load the variables from `.env` in your preferred environment manager before starting Uvicorn.

### 2. Frontend
In a second terminal:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open http://localhost:5173. Set `VITE_API_URL` if the API is hosted elsewhere.

## GitHub OAuth setup
1. In GitHub, create an OAuth App under Developer settings.
2. Set its authorization callback URL to `http://localhost:8000/api/github/callback`.
3. Put its Client ID and Client Secret in `backend/.env` as `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.
4. Restart the backend and use **Connect GitHub**.

The app requests the classic OAuth `repo` scope because publishing to private repositories requires it. GitHub OAuth Apps do not offer granular repository permissions. For a production deployment, prefer a GitHub App with narrowly scoped Contents: Read and write and Metadata: Read permissions, installed only on selected repositories.

## API
- `GET /api/health`
- `POST /api/projects/analyze`
- `POST /api/projects/generate`
- `POST /api/projects/upload-spec`
- `GET /api/projects/{project_id}/files`
- `GET /api/projects/{project_id}/download`
- `GET /api/github/login`
- `GET /api/github/callback`
- `GET /api/github/repositories`
- `POST /api/github/publish`

Interactive API docs: http://localhost:8000/docs

## Tests / smoke checks
```bash
curl http://localhost:8000/api/health
```
Then use the UI to upload a specification, analyze, generate, preview, and download. GitHub publishing can only be tested after OAuth credentials and an authorized GitHub account are configured. Test against a disposable repository before using a production repository.

## Security and deployment notes
- Never commit `.env`; secrets are backend-only. Set `SESSION_HTTPS_ONLY=true` behind HTTPS.
- Use a strong `SECRET_KEY`, HTTPS, restrictive CORS, rate limiting, CSRF protection for state-changing browser requests, and a production session/token store before public deployment.
- GitHub OAuth access tokens are kept in the backend SQLite session table; the browser receives only a signed, HTTP-only session identifier. Encrypt token storage at rest, add disconnect/revocation, and use a managed database/secret store for production.
- GitHub publishing uses the Contents API; each file write is a separate commit. Large repositories should use the Git Data API to create a single atomic commit.
- Existing branch must already exist. The UI asks for confirmation, but users should inspect the target repository and branch before publishing.
- Upload limits are enforced by the API. PDF/DOCX parsing is text extraction; scanned PDFs may need OCR preprocessing. Image OCR requires Tesseract installed on the host.
- The AI provider must return JSON in the documented `{"files": {...}}` format. Generated code is untrusted: review and test it before running.
- Add authentication/ownership checks, per-user project isolation, abuse prevention, request quotas, audit logs, and a managed secret store before multi-user production deployment.
