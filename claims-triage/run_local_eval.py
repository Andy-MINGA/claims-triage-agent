import asyncio
import json
import sys
import time
sys.path.insert(0, "tests/eval")

from google.adk.runners import InMemoryRunner
from google.genai import types
from app.agent import app as claims_app
from metrics import evaluate

DATASET_PATH = "tests/eval/datasets/claims-triage-dataset.json"


async def run_case(case):
    runner = InMemoryRunner(agent=claims_app.root_agent, app_name="claims_triage_eval")
    session = await runner.session_service.create_session(
        app_name="claims_triage_eval", user_id="eval_user"
    )
    prompt_text = case["prompt"]["parts"][0]["text"]
    msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])

    final_response = ""
    async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=msg):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response = part.text

    return final_response


async def main():
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    for i, case in enumerate(dataset["eval_cases"]):
        if i > 0:
            print("\nWaiting 60 seconds to respect free-tier rate limits...")
            time.sleep(60)
        case_id = case["eval_case_id"]
        print(f"\n{'='*60}")
        print(f"Running case: {case_id}")
        print(f"{'='*60}")

        try:
            response = await run_case(case)
        except Exception as e:
            print(f"FAILED to run case: {e}")
            results.append({"case_id": case_id, "error": str(e)})
            continue

        reference = None
        if "reference" in case:
            reference = case["reference"]["response"]["parts"][0]["text"]

        instance = {
            "prompt": case["prompt"]["parts"][0]["text"],
            "response": response,
            "reference": reference,
        }

        verdict = evaluate(instance)
        results.append({
            "case_id": case_id,
            "response": response,
            "score": verdict["score"],
            "explanation": verdict["explanation"],
        })

        print(f"Response: {response[:200]}...")
        print(f"Score: {verdict['score']}/5")
        print(f"Explanation: {verdict['explanation']}")

    print(f"\n\n{'='*60}")
    print("EVAL SUMMARY")
    print(f"{'='*60}")
    for r in results:
        if "error" in r:
            print(f"{r['case_id']}: ERROR - {r['error']}")
        else:
            print(f"{r['case_id']}: {r['score']}/5")

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nFull results saved to eval_results.json")


if __name__ == "__main__":
    asyncio.run(main())