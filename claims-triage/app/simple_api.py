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


@api.get("/")
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