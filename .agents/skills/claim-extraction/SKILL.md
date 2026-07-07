\---

name: claim-extraction

description: Use this skill when extracting structured data (claimant name, policy number, incident description, claim amount) from raw insurance claim text. Applies to intake and triage tasks.

\---



\# Claim Extraction Skill



\## Goal

To reliably extract structured, well-formed claim data from unstructured claim text submitted by an adjuster, so downstream agents (risk assessment, coverage checking) can work with clean fields instead of free text.



\## Instructions

1\. Read the raw claim text carefully.

2\. Identify and extract exactly these four fields:

&#x20;  - \*\*claimant\_name\*\*: the full name of the person filing the claim

&#x20;  - \*\*policy\_number\*\*: must match the format `POL-XXXX` (four digits); if no valid format is found, flag it rather than guessing

&#x20;  - \*\*incident\_description\*\*: a concise summary of what happened, in the claimant's own words where possible

&#x20;  - \*\*claim\_amount\*\*: the dollar amount being claimed, as a plain number (no currency symbols)

3\. If any field is missing or ambiguous in the source text, explicitly state which field is missing rather than inventing a value.

4\. Present the extracted fields clearly labeled, one per line.



\## Examples

\*\*Input:\*\* "Claimant Jane Doe filed a claim under policy POL-1001 for a fender bender, claiming 2000 dollars in damages."



\*\*Output:\*\*

\- claimant\_name: Jane Doe

\- policy\_number: POL-1001

\- incident\_description: Fender bender

\- claim\_amount: 2000



\## Constraints

\- Never invent a policy number if one isn't clearly stated in the text.

\- Never round or estimate the claim amount — extract exactly what's stated.

\- Do not add commentary or risk opinions here — that belongs to the risk assessment step, not extraction.

