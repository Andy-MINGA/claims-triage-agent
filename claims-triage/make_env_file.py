import json
import os

with open("../mcp_server/firebase-service-account.json", encoding="utf-8") as f:
    firebase_json = f.read()

gemini_key = os.environ["GEMINI_API_KEY"]

# YAML block scalar keeps the JSON safe regardless of quotes/commas inside it
yaml_content = f"""GEMINI_API_KEY: "{gemini_key}"
FIREBASE_CREDENTIALS_JSON: |
{chr(10).join('  ' + line for line in firebase_json.splitlines())}
"""

with open("env-vars.yaml", "w", encoding="utf-8") as f:
    f.write(yaml_content)

print("env-vars.yaml written successfully.")