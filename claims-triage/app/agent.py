import sqlite3
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types


def check_policy_coverage(policy_number: str, incident_description: str, claim_amount: float) -> str:
    """Checks a claim against the policy knowledge base to determine coverage.

    Args:
        policy_number: The policy number referenced in the claim, e.g. POL-1001.
        incident_description: What happened, in the claimant's own words.
        claim_amount: The dollar amount being claimed.

    Returns:
        A string describing the coverage decision (covered, denied, partial, or cannot_verify) and reasoning.
    """
    db = sqlite3.connect("../mcp_server/policies.db")
    cursor = db.execute("SELECT * FROM policies WHERE policy_number = ?", (policy_number,))
    row = cursor.fetchone()

    if row is None:
        return f"cannot_verify: No policy found matching {policy_number}"

    columns = [desc[0] for desc in cursor.description]
    policy = dict(zip(columns, row))
    exclusions = policy.get("exclusions", "").lower()
    description = incident_description.lower()
    excluded_hit = any(term.strip() in description for term in exclusions.split(",") if term.strip())

    if policy["status"] != "active":
        return f"denied: Policy status is '{policy['status']}', not active."
    elif excluded_hit:
        return f"denied: Incident matches an exclusion: {policy['exclusions']}"
    elif claim_amount > policy["coverage_limit"]:
        return f"partial: Claim amount (${claim_amount}) exceeds coverage limit of ${policy['coverage_limit']}"
    else:
        return f"covered: Claim falls within policy coverage limit of ${policy['coverage_limit']} and no exclusions apply."


model = Gemini(model="gemini-flash-latest", retry_options=types.HttpRetryOptions(attempts=3))

intake_agent = Agent(
    name="intake_agent",
    model=model,
    instruction=(
        "You are an insurance intake specialist. Extract structured claim details from the raw "
        "claim text: claimant name, policy number (format POL-XXXX), incident description, and "
        "claim amount in dollars. Present these clearly labeled."
    ),
)

risk_agent = Agent(
    name="risk_assessment_agent",
    model=model,
    instruction=(
        "You are a risk assessment specialist for an insurance company. Given extracted claim "
        "details, assess a risk level (low, medium, or high) based on the claim amount and incident "
        "description. Flag anything unusual: very high amounts, vague descriptions, or mentions of "
        "excluded activities."
    ),
)

coverage_agent = Agent(
    name="coverage_checker_agent",
    model=model,
    instruction=(
        "You are a coverage verification specialist. Use the check_policy_coverage tool with the "
        "policy number, incident description, and claim amount to determine if the claim is covered, "
        "denied, partial, or cannot be verified. Always call the tool — never guess."
    ),
    tools=[check_policy_coverage],
)

report_agent = Agent(
    name="report_generator_agent",
    model=model,
    instruction=(
        "You are a claims report writer. Combine the claim details, risk assessment, and coverage "
        "decision from this conversation into a clear, structured triage report for a human adjuster: "
        "claim summary, risk level with reasoning, coverage decision with reasoning, and a recommended "
        "next action."
    ),
)

root_agent = Agent(
    name="claims_triage_orchestrator",
    model=model,
    instruction=(
        "You orchestrate an insurance claims triage pipeline. For each claim submitted, delegate "
        "in this exact order: first to intake_agent to extract structured claim data, then to "
        "risk_assessment_agent to assess risk, then to coverage_checker_agent to check policy "
        "coverage, and finally to report_generator_agent to produce the final triage report. "
        "Always complete all four steps in order before giving your final answer."
    ),
    sub_agents=[intake_agent, risk_agent, coverage_agent, report_agent],
)

app = App(
    root_agent=root_agent,
    name="app",
)