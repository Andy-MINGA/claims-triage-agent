# agent.py — Insurance Claims Triage multi-agent workflow (ADK 2.0)
from __future__ import annotations
import sqlite3
from typing import Any, Literal

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events.event import Event
from google.adk.workflow import Edge, Workflow
from google.adk.workflow.agents.llm_agent import LlmAgent
from google.adk.workflow.node import node
from pydantic import BaseModel, Field


# ---------- Schemas ----------
class ClaimData(BaseModel):
    claimant_name: str = Field(description="Name of the person filing the claim")
    policy_number: str = Field(description="Policy number referenced in the claim, e.g. POL-1001")
    incident_description: str = Field(description="What happened, in the claimant's words")
    claim_amount: float = Field(description="Dollar amount being claimed")


class RiskAssessment(BaseModel):
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk level of this claim based on the description and amount"
    )
    risk_reasoning: str = Field(description="Short explanation for the assigned risk level")


# ---------- Node 1: Intake Agent ----------
intake_agent = LlmAgent(
    name="intake_agent",
    model="gemini-3.1-flash-lite",
    instruction=(
        "You are an insurance intake specialist. Extract structured claim details "
        "from the raw claim text provided. Be precise about the policy number format (e.g. POL-1001)."
    ),
    output_key="claim_data",
    output_schema=ClaimData,
)


# ---------- Node 2: Risk Assessment Agent ----------
risk_agent = LlmAgent(
    name="risk_assessment_agent",
    model="gemini-3.1-flash-lite",
    instruction=(
        "You are a risk assessment specialist for an insurance company. Given the extracted "
        "claim data, assess the risk level (low, medium, high) based on the claim amount and "
        "incident description. Flag anything unusual (e.g. very high amounts, vague descriptions, "
        "descriptions that mention excluded activities like racing or DUI)."
    ),
    output_key="risk_assessment",
    output_schema=RiskAssessment,
)


# ---------- Node 3: Coverage Checker (function node, queries policy DB) ----------
@node
def coverage_checker(ctx: Context, node_input: Any):
    """Checks the claim's policy_number against the policy knowledge base."""
    claim = ctx.state.get("claim_data", {})
    policy_number = claim.get("policy_number", "")

    db = sqlite3.connect("../mcp_server/policies.db")
    cursor = db.execute("SELECT * FROM policies WHERE policy_number = ?", (policy_number,))
    row = cursor.fetchone()

    if row is None:
        coverage_result = {
            "found": False,
            "decision": "cannot_verify",
            "reason": f"No policy found matching {policy_number}",
        }
    else:
        columns = [desc[0] for desc in cursor.description]
        policy = dict(zip(columns, row))
        exclusions = policy.get("exclusions", "").lower()
        description = claim.get("incident_description", "").lower()

        excluded_hit = any(
            term.strip() in description for term in exclusions.split(",") if term.strip()
        )

        if policy["status"] != "active":
            decision = "denied"
            reason = f"Policy status is '{policy['status']}', not active."
        elif excluded_hit:
            decision = "denied"
            reason = f"Incident matches an exclusion: {policy['exclusions']}"
        elif claim.get("claim_amount", 0) > policy["coverage_limit"]:
            decision = "partial"
            reason = f"Claim amount exceeds coverage limit of ${policy['coverage_limit']}"
        else:
            decision = "covered"
            reason = "Claim falls within policy coverage and no exclusions apply."

        coverage_result = {
            "found": True,
            "policy": policy,
            "decision": decision,
            "reason": reason,
        }

    yield Event(data=coverage_result, state={"coverage_result": coverage_result})


# ---------- Node 4: Report Generator Agent ----------
report_agent = LlmAgent(
    name="report_generator_agent",
    model="gemini-3.1-flash-lite",
    instruction=(
        "You are a claims report writer. Using the claim data, risk assessment, and coverage "
        "check result available in state, write a clear, structured triage report for a human "
        "adjuster. Include: claim summary, risk level with reasoning, coverage decision with "
        "reasoning, and a recommended next action."
    ),
)


# ---------- Workflow ----------
root_workflow = Workflow(
    name="claims_triage_workflow",
    edges=[*Edge.chain("START", intake_agent, risk_agent, coverage_checker, report_agent)],
)

app = App(
    name="claims_triage_agent",
    root_agent=root_workflow,
)