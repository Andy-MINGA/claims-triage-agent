# simple_api.py — A lean FastAPI wrapper for the claims triage agent,
# avoiding the scaffolded fast_api_app.py's Google Cloud Logging / ADC
# dependencies, which require a full GCP project we don't have (Issue #13).
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.runners import InMemoryRunner
from google.genai import types
from app.agent import app as claims_app

api = FastAPI(title="Claims Triage API")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    claim_text: str


class ClaimResponse(BaseModel):
    final_report: str
    security_flagged: bool


from fastapi.responses import HTMLResponse

FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Claims Triage Agent</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; background: #f5f5f7; }
  h1 { color: #1a1a1a; }
  textarea { width: 100%; height: 100px; padding: 10px; font-size: 14px; border-radius: 8px; border: 1px solid #ccc; }
  button { margin-top: 10px; padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; font-size: 15px; cursor: pointer; }
  button:disabled { background: #93c5fd; cursor: not-allowed; }
  #report { white-space: pre-wrap; background: white; border-radius: 8px; padding: 20px; margin-top: 20px; border: 1px solid #ddd; min-height: 50px; }
  .flagged { border-left: 5px solid #dc2626; }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #fff; border-top: 2px solid transparent; border-radius: 50%; animation: spin 0.7s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
  <h1>Claims Triage Agent</h1>
  <p>Enter a claim description below and submit for automated triage.</p>
  <textarea id="claimText" placeholder="e.g. Claimant Jane Doe filed a claim under policy POL-1001 for a fender bender, claiming 2000 dollars in damages."></textarea>
  <br>
  <button id="submitBtn" onclick="submitClaim()">Submit Claim</button>
  <div id="report"></div>

<script>
async function submitClaim() {
  const text = document.getElementById('claimText').value;
  const btn = document.getElementById('submitBtn');
  const reportDiv = document.getElementById('report');
  if (!text.trim()) { alert('Please enter a claim description.'); return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Processing...';
  reportDiv.textContent = '';
  reportDiv.className = '';

  try {
    const res = await fetch('/triage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim_text: text })
    });
    const data = await res.json();
    reportDiv.textContent = data.final_report;
    reportDiv.className = data.security_flagged ? 'flagged' : '';
  } catch (err) {
    reportDiv.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit Claim';
  }
}
</script>
</body>
</html>
"""


@api.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML


@api.get("/health")
def health_check():
    return {"status": "ok", "service": "claims-triage-api"}


@api.post("/triage", response_model=ClaimResponse)
async def triage_claim(request: ClaimRequest):
    runner = InMemoryRunner(agent=claims_app.root_agent, app_name="claims_triage_api")
    session = await runner.session_service.create_session(
        app_name="claims_triage_api", user_id="api_user"
    )
    msg = types.Content(role="user", parts=[types.Part(text=request.claim_text)])

    accumulated_state = {}
    async for event in runner.run_async(user_id="api_user", session_id=session.id, new_message=msg):
        if event.actions and event.actions.state_delta:
            accumulated_state.update(event.actions.state_delta)

    final_report = accumulated_state.get("final_report", "No report was generated.")
    security_flagged = accumulated_state.get("security_flagged", False)

    return ClaimResponse(final_report=final_report, security_flagged=security_flagged)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000)