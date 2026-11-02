import json, re
import httpx
from .config import settings

SYSTEM_PROMPT = """You are a senior software engineer generating secure, runnable educational projects.
Return ONLY valid JSON with this exact shape: {"files":{"relative/path":"complete file contents"}}.
Create a complete, coherent project matching the user's topic and selected stack. Include useful
README, tests where practical, dependency manifests, .gitignore and .env.example containing placeholders
only. Do not include real secrets, .env files, binaries, node_modules, virtual environments, or build output.
Keep paths relative and use text files. Include a sensible, functional implementation rather than TODO-only
stubs. The root should contain the frontend/backend or equivalent needed by the chosen stack."""

async def ask_ai(topic: str, stack: str):
    if not settings.AI_API_KEY:
        raise RuntimeError("AI_API_KEY is not configured on the backend. Add it to backend/.env.")
    payload = {
        "model": settings.AI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Project topic and requirements:\n{topic}\n\nPreferred stack: {stack}\nGenerate the complete project files."}
        ]
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            settings.AI_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
            json=payload
        )
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    result = json.loads(content)
    if "files" not in result:
        raise ValueError("AI response is missing the 'files' object")
    return result["files"]

async def analyze_topic(topic: str, stack: str):
    if not settings.AI_API_KEY:
        return {"summary": topic[:500], "stack": stack,
                "note": "Configure AI_API_KEY to enable AI-assisted analysis."}
    payload = {"model": settings.AI_MODEL, "temperature": 0.1,
        "messages": [{"role":"system","content":"Summarize a software project topic into concise goals, core modules, data flow, and suggested tests. Return plain text."},
                     {"role":"user","content":f"Stack: {stack}\nTopic: {topic}"}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(settings.AI_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization":f"Bearer {settings.AI_API_KEY}"}, json=payload)
        r.raise_for_status()
        return {"summary": r.json()["choices"][0]["message"]["content"], "stack": stack}
