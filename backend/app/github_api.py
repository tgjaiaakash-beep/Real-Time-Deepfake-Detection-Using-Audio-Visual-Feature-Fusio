import httpx
from .config import settings

API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

async def exchange_code(code: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://github.com/login/oauth/access_token",
            headers={"Accept":"application/json"},
            json={"client_id":settings.GITHUB_CLIENT_ID, "client_secret":settings.GITHUB_CLIENT_SECRET,
                  "code":code, "redirect_uri":settings.GITHUB_CALLBACK_URL})
        r.raise_for_status()
        data = r.json()
    if "access_token" not in data:
        raise ValueError(data.get("error_description", "GitHub authorization failed"))
    return data["access_token"]

async def gh_request(token, method, path, **kwargs):
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.request(method, API + path,
            headers={**HEADERS, "Authorization":f"Bearer {token}"}, **kwargs)
    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        raise RuntimeError("GitHub API rate limit reached. Try again later.")
    if r.status_code >= 400:
        try: detail = r.json().get("message", r.text)
        except Exception: detail = r.text
        raise RuntimeError(f"GitHub API error ({r.status_code}): {detail}")
    return r.json() if r.content else {}

async def list_repositories(token):
    return await gh_request(token, "GET", "/user/repos", params={"per_page":100, "sort":"updated"})

async def publish_files(token, owner, repo, branch, files, message):
    repo_info = await gh_request(token, "GET", f"/repos/{owner}/{repo}")
    default_branch = repo_info.get("default_branch") or "main"
    try:
        await gh_request(token, "GET", f"/repos/{owner}/{repo}/branches/{branch}")
    except RuntimeError:
        if branch != default_branch:
            raise RuntimeError(f"Target branch '{branch}' does not exist. Create it on GitHub first.")
        branch = default_branch
    # Contents API creates or updates files and records a commit for each file.
    import base64
    published = []
    for path, content in files.items():
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        existing = None
        try:
            existing = await gh_request(token, "GET", endpoint, params={"ref":branch})
        except RuntimeError as exc:
            if "404" not in str(exc): raise
        body = {"message":message, "content":base64.b64encode(content.encode()).decode(), "branch":branch}
        if existing and existing.get("sha"): body["sha"] = existing["sha"]
        await gh_request(token, "PUT", endpoint, json=body)
        published.append(path)
    return {"url":repo_info["html_url"], "branch":branch, "published_files":published}
