from __future__ import annotations
import re
from typing import Any, Literal

import firebase_admin
from firebase_admin import credentials, firestore

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.workflow import Edge, Workflow, node, START
from pydantic import BaseModel, Field


# ---------- Schemas ----------
class ClaimData(BaseModel):
    claimant_name: str = Field(description="Name of the person filing the claim")
    policy_number: str = Field(description="Policy number referenced in the claim, e.g. POL-1001")
    incident_description: str = Field(description="What happened, in the claimant's words")
    claim_amount: float = Field(description="Dollar amount being claimed")


class RiskAssessment(BaseModel):
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk level of this claim"
    )
    risk_reasoning: str = Field(description="Short explanation for the assigned risk level")

# ---------- Firestore Setup ----------
import json
import os

if not firebase_admin._apps:
    firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if firebase_creds_json:
        # Production/deployed: credentials injected as an environment variable
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        # Local development: credentials read from file
        cred = credentials.Certificate("../mcp_server/firebase-service-account.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()



# ---------- Node 1: Security Screen (function node, runs BEFORE any LLM) ----------
@node
def security_screen(ctx: Context, node_input: Any):
    """Screens raw claim text for PII and prompt-injection attempts before any LLM sees it."""
    raw_text = str(node_input)
    text = raw_text

    text = re.sub(r"\b\d{3}-?\d{2}-?\d{4}\b", "[REDACTED-SSN]", text)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED-CARD]", text)

    injection_markers = [
        "ignore all rules", "ignore previous instructions", "bypass", "disregard the rules",
        "auto-approve", "you must approve", "override the policy", "act as", "system prompt",
    ]
    lowered = text.lower()
    flagged = any(marker in lowered for marker in injection_markers)

    if flagged:
        text = "[SECURITY FLAG: possible prompt-injection attempt] " + text

    yield Event(data=text, state={"screened_text": text, "security_flagged": flagged})

@node
def security_gate(ctx: Context, node_input: Any):
    """Hard-enforced routing gate: deterministically halts processing for flagged claims,
    instead of relying on the LLM to notice and respect the security flag on its own."""
    flagged = ctx.state.get("security_flagged", False)
    if flagged:
        halt_report = (
            "**Triage Report**\n\n"
            "**SECURITY ALERT: This claim was automatically halted before processing.**\n\n"
            "Reason: The submitted claim text contained a possible prompt-injection attempt "
            "(e.g., instructions trying to force auto-approval or bypass review rules).\n\n"
            "**Recommended Next Action:** Route to a human security reviewer immediately. "
            "Do not process this claim automatically."
        )
        yield Event(data=halt_report, state={"final_report": halt_report}, route="halted")
    else:
        yield Event(data=node_input, route="continue")


@node
def halted_output(ctx: Context, node_input: Any):
    """Terminal node for halted claims — final_report is already set by security_gate."""
    yield Event(data=ctx.state.get("final_report", "Claim halted for security review."))

# ---------- Node 2: Intake Agent ----------
intake_agent = LlmAgent(
    name="intake_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are an insurance intake specialist. Extract structured claim details from the "
        "provided claim text. Be precise about the policy number format (e.g. POL-1001). If the "
        "text contains a '[SECURITY FLAG...]' marker, note that this claim requires human review "
        "and extract fields as best as possible anyway."
    ),
    output_key="claim_data",
    output_schema=ClaimData,
)


# ---------- Node 3: Risk Assessment Agent ----------
risk_agent = LlmAgent(
    name="risk_assessment_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a risk assessment specialist. Given the extracted claim data, assess risk level "
        "(low, medium, high) based on claim amount and incident description. Flag unusual amounts, "
        "vague descriptions, or mentions of excluded activities like racing or DUI."
    ),
    output_key="risk_assessment",
    output_schema=RiskAssessment,
)


# ---------- Node 4: Coverage Checker (function node, queries policy DB) ----------
@node
def coverage_checker(ctx: Context, node_input: Any):
    """Checks the claim's policy_number against the policy knowledge base (Firestore)."""
    claim = ctx.state.get("claim_data", {})
    policy_number = claim.get("policy_number", "")

    if not policy_number:
        coverage_result = {
            "found": False,
            "decision": "cannot_verify",
            "reason": "No policy number was extracted from the claim. Route to human review.",
        }
        yield Event(data=coverage_result, state={"coverage_result": coverage_result})
        return

    try:
        doc = db.collection("policies").document(policy_number).get()
    except Exception as e:
        coverage_result = {
            "found": False,
            "decision": "cannot_verify",
            "reason": f"Policy database error: {str(e)}. Route to human review.",
        }
        yield Event(data=coverage_result, state={"coverage_result": coverage_result})
        return

    if not doc.exists:
        coverage_result = {
            "found": False,
            "decision": "cannot_verify",
            "reason": f"No policy found matching {policy_number}",
        }
    else:
        try:
            policy = doc.to_dict()
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

            coverage_result = {"found": True, "policy": policy, "decision": decision, "reason": reason}
        except (KeyError, TypeError) as e:
            coverage_result = {
                "found": True,
                "decision": "cannot_verify",
                "reason": f"Policy record was malformed ({str(e)}). Route to human review.",
            }

    yield Event(data=coverage_result, state={"coverage_result": coverage_result})


# ---------- Node 5: Report Generator Agent ----------
report_agent = LlmAgent(
    name="report_generator_agent",
    model="gemini-2.5-flash",
    output_key="final_report",
    instruction=(
        "You are a claims report writer. Write a clear structured triage report using ONLY "
        "the exact data provided below. Do NOT invent, guess, or fabricate any claim ID, date, "
        "name, or number not present in this data. If a value is missing, write 'Not available' "
        "for that field.\n\n"
        "CLAIM DATA:\n{claim_data}\n\n"
        "RISK ASSESSMENT:\n{risk_assessment}\n\n"
        "COVERAGE CHECK RESULT:\n{coverage_result}\n\n"
        "Using ONLY the data above, write the report with these sections: claim summary "
        "(claimant name, policy number, incident description, claim amount), risk level with "
        "reasoning, coverage decision with reasoning, and a recommended next action.\n"
        "The policyholder name (from COVERAGE CHECK RESULT) and the claimant name (from CLAIM "
        "DATA) may differ — do not merge or confuse them."
    ),
)
# ---------- Workflow ----------
root_agent = Workflow(
    name="claims_triage_workflow",
    edges=[
        Edge(from_node=START, to_node=security_screen),
        Edge(from_node=security_screen, to_node=security_gate),
        Edge(from_node=security_gate, to_node=intake_agent, route="continue"),
        Edge(from_node=security_gate, to_node=halted_output, route="halted"),
        Edge(from_node=intake_agent, to_node=risk_agent),
        Edge(from_node=risk_agent, to_node=coverage_checker),
        Edge(from_node=coverage_checker, to_node=report_agent),
    ],
)
app = App(name="claims_triage_agent", root_agent=root_agent)