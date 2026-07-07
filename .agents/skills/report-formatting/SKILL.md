\---

name: report-formatting

description: Use this skill when generating the final triage report for a human adjuster, combining claim data, risk assessment, and coverage decision into a clear structured summary.

\---



\# Report Formatting Skill



\## Goal

To produce a consistent, clear, human-readable triage report for a claims adjuster, combining outputs from the intake, risk assessment, and coverage checking steps into one structured document.



\## Instructions

1\. Gather the three required inputs from prior steps: extracted claim data, risk assessment (level + reasoning), and coverage decision (decision + reasoning).

2\. Structure the report in this exact order, using these exact section headers:

&#x20;  - \*\*Claim Summary\*\* — claimant name, policy number, incident description, claim amount

&#x20;  - \*\*Risk Assessment\*\* — risk level (low/medium/high) and the reasoning behind it

&#x20;  - \*\*Coverage Decision\*\* — decision (covered/denied/partial/cannot\_verify) and the reasoning behind it

&#x20;  - \*\*Recommended Next Action\*\* — one clear, actionable sentence for the adjuster (e.g., "Approve for payout," "Escalate for manual review," "Request additional documentation")

3\. Keep each section to 2-4 sentences maximum. Adjusters need a fast read, not an essay.

4\. Use plain, direct language — avoid hedging phrases like "it seems" or "possibly" unless genuine uncertainty exists in the underlying data.



\## Examples

\*\*Input (from prior steps):\*\*

\- Claim: Jane Doe, POL-1001, fender bender, $2000

\- Risk: low — minor incident, amount consistent with typical fender bender claims

\- Coverage: covered — policy active, no exclusions triggered, within coverage limit



\*\*Output:\*\*



Claim Summary

Claimant Jane Doe filed a claim under policy POL-1001 for a fender bender, claiming $2000 in damages.

Risk Assessment

Risk level: Low. The incident and amount are consistent with a typical minor collision claim, with no red flags.

Coverage Decision

Decision: Covered. Policy POL-1001 is active, the incident does not match any exclusions, and $2000 is within the coverage limit.

Recommended Next Action

Approve for payout.





\## Constraints

\- Never omit a section, even if the input for it is thin — state "insufficient data" rather than leaving it blank.

\- Do not re-assess risk or coverage here — only format and summarize what was already decided upstream.

