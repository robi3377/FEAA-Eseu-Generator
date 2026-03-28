import os
import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import secrets

from semantic_scholar import search_papers
from claude_client import generate_project, generate_explanation
from document_generator import generate_docx, generate_pdf_from_text

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="FEAA Eseu Generator")

security = HTTPBasic()

AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "password")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, AUTH_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, AUTH_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


class GenerateRequest(BaseModel):
    topic: str


INDEX_HTML = """<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FEAA Generator Eseu</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0a0a; --card: #141414; --border: #2a2a2a;
    --text: #ededed; --muted: #888; --accent: #6366f1; --accent-h: #818cf8;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Open Sans', sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 3rem 1rem; }
  h1 { font-size: 2rem; font-weight: 700; letter-spacing: 0; margin-bottom: 1.5rem; }
  .container { width: 100%; max-width: 640px; }

  .prompt-label { font-size: .85rem; color: var(--muted); margin-bottom: .5rem; }
  .prompt-box {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.2rem 1.4rem; font-style: italic; cursor: pointer;
    transition: border-color .2s; user-select: all; line-height: 1.5;
  }
  .prompt-box:hover { border-color: var(--accent); }
  .prompt-hint { font-size: .75rem; color: var(--muted); margin-top: .3rem; margin-bottom: 1.5rem; }

  .notes {
    margin-top: 0; margin-bottom: 1.5rem; padding: .9rem 1.1rem .9rem 1.1rem;
    list-style: none; background: rgba(120,80,0,.15); border: 1px solid #a16207;
    border-radius: 10px;
  }
  .notes li {
    font-size: .82rem; color: #fbbf24; padding-left: 1.2rem; position: relative;
    margin-bottom: .35rem; line-height: 1.45;
  }
  .notes li:last-child { margin-bottom: 0; }
  .notes li::before { content: "\\2022"; position: absolute; left: 0; color: #fbbf24; }

  label { font-size: .9rem; font-weight: 500; display: block; margin-bottom: .5rem; }
  textarea {
    width: 100%; height: 110px; background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem; color: var(--text); font-size: .95rem;
    resize: none; outline: none; transition: border-color .2s; font-family: inherit;
  }
  textarea::placeholder { color: var(--muted); }
  textarea:focus { border-color: var(--accent); }

  .gen-btn {
    margin-top: 1rem; width: 100%; padding: .85rem; border: none; border-radius: 12px;
    background: var(--accent); color: #fff; font-size: 1rem; font-weight: 600;
    cursor: pointer; transition: background .2s;
  }
  .gen-btn:hover:not(:disabled) { background: var(--accent-h); }
  .gen-btn:disabled { opacity: .4; cursor: not-allowed; }

  .progress {
    margin-top: 2rem; background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem;
  }
  .progress-title { font-size: .85rem; color: var(--muted); margin-bottom: 1rem; }
  .step { display: flex; align-items: center; gap: .75rem; margin-bottom: .7rem; font-size: .95rem; }
  .step .icon { width: 18px; height: 18px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  .step.done .icon { color: #4ade80; }
  .step.active .icon { animation: spin .8s linear infinite; }
  .step.pending { color: var(--muted); }
  .step.pending .icon { border: 1.5px solid var(--border); border-radius: 50%; }
  .spinner { width: 16px; height: 16px; border: 2px solid var(--accent); border-top-color: transparent; border-radius: 50%; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .progress-hint { font-size: .75rem; color: var(--muted); margin-top: .8rem; }

  .download-area {
    margin-top: 2rem; background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem; text-align: center;
  }
  .download-area p { margin-bottom: 1rem; color: #4ade80; font-weight: 600; }
  .dl-btn {
    display: inline-block; padding: .7rem 2rem; border: none; border-radius: 10px;
    background: #22c55e; color: #fff; font-size: .95rem; font-weight: 600;
    cursor: pointer; transition: background .2s; text-decoration: none;
  }
  .dl-btn:hover { background: #16a34a; }

  .error {
    margin-top: 1.5rem; background: rgba(127,29,29,.3); border: 1px solid #b91c1c;
    border-radius: 12px; padding: 1rem; color: #fca5a5;
  }
  .hidden { display: none; }
</style>
</head>
<body>

<h1>FEAA Generator Eseu</h1>

<div class="container">
  <p class="prompt-label">Prompt recomandat pentru generarea de topicuri (foloseste-l in ChatGPT/Claude):</p>
  <div class="prompt-box" id="promptBox" title="Click pentru a copia">
    &ldquo;Generate 10 academic essay topics in English, field: [X], university level. Keep them short and suitable as search queries.&rdquo;
  </div>
  <p class="prompt-hint">Click pe text pentru a copia</p>

  <ul class="notes">
    <li>NU pune prompt-ul de mai sus in caseta de generare! Foloseste-l separat in ChatGPT/Claude pentru a obtine topicuri, apoi copiaza un topic mai jos.</li>
    <li>Topicul trebuie sa fie in limba engleza pentru cautarea articolelor. Proiectul va fi generat in romana.</li>
  </ul>

  <label for="topic">Introdu topicul proiectului (in engleza):</label>
  <textarea id="topic" placeholder="Ex: The impact of artificial intelligence on university education"></textarea>
  <button class="gen-btn" id="btn" onclick="generate()">Genereaza proiect</button>

  <div class="progress hidden" id="progress">
    <p class="progress-title">Progres:</p>
    <div id="steps"></div>
    <p class="progress-hint">Procesul poate dura 1-2 minute...</p>
  </div>

  <div class="download-area hidden" id="downloadArea">
    <p>Proiectul a fost generat cu succes!</p>
    <a class="dl-btn" id="dlBtn" href="#" download>Descarca fisierele (.zip)</a>
  </div>

  <div class="error hidden" id="error"></div>
</div>

<script>
const STEPS = [
  "Cautare articole pe OpenAlex...",
  "Generare proiect academic cu Claude...",
  "Generare document explicativ...",
  "Creare fisiere .docx si .pdf..."
];
const promptText = 'Generate 10 academic essay topics in English, field: [X], university level. Keep them short and suitable as search queries.';

document.getElementById('promptBox').addEventListener('click', () => {
  navigator.clipboard.writeText(promptText);
});

function renderSteps(current) {
  const el = document.getElementById('steps');
  el.innerHTML = STEPS.map((s, i) => {
    if (i < current) return `<div class="step done"><span class="icon">&#10003;</span>${s}</div>`;
    if (i === current) return `<div class="step active"><span class="icon"><div class="spinner"></div></span>${s}</div>`;
    return `<div class="step pending"><span class="icon"></span>${s}</div>`;
  }).join('');
}

async function generate() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) return;

  const btn = document.getElementById('btn');
  const progress = document.getElementById('progress');
  const errorEl = document.getElementById('error');
  const dlArea = document.getElementById('downloadArea');

  btn.disabled = true;
  btn.textContent = 'Se genereaza...';
  progress.classList.remove('hidden');
  dlArea.classList.add('hidden');
  errorEl.classList.add('hidden');

  let step = 0;
  renderSteps(step);
  const iv = setInterval(() => { step = Math.min(step + 1, STEPS.length - 1); renderSteps(step); }, 8000);

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    clearInterval(iv);

    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: 'Server error' }));
      throw new Error(data.detail || 'Error ' + res.status);
    }

    renderSteps(STEPS.length);

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const dlBtn = document.getElementById('dlBtn');
    dlBtn.href = url;
    dlBtn.download = 'proiect_' + topic.slice(0, 30).replace(/\\s+/g, '_') + '.zip';

    setTimeout(() => {
      progress.classList.add('hidden');
      dlArea.classList.remove('hidden');
    }, 800);
  } catch (e) {
    clearInterval(iv);
    progress.classList.add('hidden');
    errorEl.textContent = e.message;
    errorEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Genereaza proiect';
  }
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index(_=Depends(verify_credentials)):
    return INDEX_HTML


@app.post("/generate")
async def generate(req: GenerateRequest, _=Depends(verify_credentials)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    # Step 1: Search OpenAlex
    try:
        papers = await search_papers(topic, limit=8)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAlex error: {e}")

    if len(papers) < 4:
        raise HTTPException(
            status_code=404,
            detail=f"Only {len(papers)} papers found. Need at least 4. Try a broader topic.",
        )

    # Step 2: Generate project text via Claude
    try:
        project_text = await generate_project(topic, papers, ANTHROPIC_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error (project): {e}")

    # Step 3: Generate explanation text via Claude
    try:
        explanation_text = await generate_explanation(topic, project_text, ANTHROPIC_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error (explanation): {e}")

    # Step 4: Generate documents
    docx_bytes = generate_docx(project_text, apply_a_replacement=True)
    project_pdf_bytes = generate_pdf_from_text(project_text, title="Proiect", apply_a_replacement=True)
    explanation_pdf_bytes = generate_pdf_from_text(explanation_text, title="Explicatie")

    # Step 5: Bundle into ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("proiect.docx", docx_bytes)
        zf.writestr("proiect.pdf", project_pdf_bytes)
        zf.writestr(f"explicatie_{topic[:50].replace(' ', '_')}.pdf", explanation_pdf_bytes)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="proiect_{topic[:30].replace(" ", "_")}.zip"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
