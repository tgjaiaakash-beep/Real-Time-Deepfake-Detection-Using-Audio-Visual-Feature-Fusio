import secrets, io, zipfile, re
from pathlib import Path
from urllib.parse import urlencode
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from .config import settings
from .db import init_db, save_project, get_project, save_github_token, get_github_token
from .ai import ask_ai, analyze_topic
from .security import clean_generated_files
from . import github_api

app = FastAPI(title=settings.APP_NAME, version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                   session_cookie=settings.COOKIE_NAME, https_only=settings.SESSION_HTTPS_ONLY,
                   same_site="lax", max_age=3600)
app.add_middleware(CORSMiddleware, allow_origins=[settings.FRONTEND_ORIGIN],
                   allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["Content-Type"])

@app.on_event("startup")
def startup(): init_db()

class ProjectRequest(BaseModel):
    topic: str = Field(min_length=10, max_length=20000)
    stack: str = Field(default="React + Vite, Python + FastAPI", max_length=200)

class PublishRequest(BaseModel):
    project_id: str
    owner: str = Field(min_length=1, max_length=100)
    repo: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=350)
    visibility: str = "private"
    branch: str = Field(default="main", min_length=1, max_length=100)
    message: str = Field(default="Publish generated project", max_length=200)
    create_new: bool = False
    confirm: bool = False

def require_github(request):
    token = get_github_token(request.session.get("github_session_id"))
    if not token: raise HTTPException(401, "Connect your GitHub account first.")
    return token

@app.get("/api/health")
def health(): return {"status":"ok", "ai_configured":bool(settings.AI_API_KEY),
                      "github_configured":bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)}

@app.post("/api/projects/analyze")
async def analyze(req: ProjectRequest):
    try: return await analyze_topic(req.topic, req.stack)
    except Exception as e: raise HTTPException(502, str(e))

@app.post("/api/projects/generate")
async def generate(req: ProjectRequest):
    try:
        raw = await ask_ai(req.topic, req.stack)
        files = clean_generated_files(raw)
        pid = save_project(req.topic, req.stack, files)
        return {"project_id":pid, "file_count":len(files), "files":list(files.keys())}
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/projects/{project_id}/files")
def project_files(project_id: str):
    project = get_project(project_id)
    if not project: raise HTTPException(404, "Project not found")
    return {"project_id":project_id, "files":project["files"]}

@app.get("/api/projects/{project_id}/download")
def download(project_id: str):
    project = get_project(project_id)
    if not project: raise HTTPException(404, "Project not found")
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in project["files"].items():
            # Re-check paths at packaging time; never include credentials or generated folders.
            from .security import safe_project_path
            try: safe = safe_project_path(name)
            except ValueError: continue
            archive.writestr(f"generated-project/{safe}", content)
    memory.seek(0)
    return StreamingResponse(memory, media_type="application/zip",
        headers={"Content-Disposition":f'attachment; filename="project-{project_id[:8]}.zip"'})

@app.get("/api/github/login")
def github_login(request: Request):
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(503, "GitHub OAuth is not configured on the backend.")
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    params = {"client_id":settings.GITHUB_CLIENT_ID, "redirect_uri":settings.GITHUB_CALLBACK_URL,
              "scope":"repo", "state":state}
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode(params))

@app.get("/api/github/callback")
async def github_callback(request: Request, code: str = "", state: str = ""):
    expected = request.session.pop("oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(400, "Invalid OAuth state. Restart GitHub connection.")
    try:
        token = await github_api.exchange_code(code)
        user = await github_api.gh_request(token, "GET", "/user")
        session_id = secrets.token_urlsafe(32)
        save_github_token(session_id, token, user.get("login", ""))
        request.session["github_session_id"] = session_id
        request.session["github_user"] = user.get("login")
        return RedirectResponse(settings.FRONTEND_ORIGIN + "/?github=connected")
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/github/repositories")
async def repositories(request: Request):
    try:
        repos = await github_api.list_repositories(require_github(request))
        return [{"name":r["name"], "full_name":r["full_name"], "private":r["private"],
                 "default_branch":r["default_branch"], "html_url":r["html_url"]} for r in repos]
    except HTTPException: raise
    except Exception as e: raise HTTPException(502, str(e))

@app.post("/api/github/publish")
async def publish(req: PublishRequest, request: Request):
    if not req.confirm: raise HTTPException(400, "Explicit confirmation is required before publishing.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", req.owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", req.repo):
        raise HTTPException(400, "Invalid GitHub owner or repository name.")
    project = get_project(req.project_id)
    if not project: raise HTTPException(404, "Project not found")
    token = require_github(request)
    try:
        if req.create_new:
            created = await github_api.gh_request(token, "POST", "/user/repos",
                json={"name":req.repo, "description":req.description,
                      "private":req.visibility != "public", "auto_init":True})
            owner = created["owner"]["login"]
        else: owner = req.owner
        result = await github_api.publish_files(token, owner, req.repo, req.branch,
                                                  clean_generated_files(project["files"]), req.message)
        return {"status":"published", **result}
    except Exception as e: raise HTTPException(502, str(e))

@app.post("/api/projects/upload-spec")
async def upload_spec(file: UploadFile = File(...)):
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit: raise HTTPException(413, "Upload exceeds the configured size limit.")
    name = (file.filename or "").lower()
    try:
        if name.endswith(".txt"): text = data.decode("utf-8-sig")
        elif name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        elif name.endswith((".png",".jpg",".jpeg",".webp")):
            from PIL import Image
            import pytesseract
            text = pytesseract.image_to_string(Image.open(io.BytesIO(data)))
        else: raise HTTPException(415, "Supported formats: PDF, DOCX, TXT, PNG, JPG, WEBP.")
        if not text.strip(): raise HTTPException(422, "No readable text found in the uploaded file.")
        return {"filename":file.filename, "text":text[:20000]}
    except HTTPException: raise
    except Exception as e: raise HTTPException(422, f"Could not extract text: {e}")
