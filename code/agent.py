import json
import sys

import anthropic

import db
from run_study import run_case, AOA_MIN, AOA_MAX

MODEL = "claude-sonnet-5-5"
MAX_RUNS = 15        # simulation budget
MAX_TURNS = 30       # safety limit for the loop

SYSTEM = f"""You run CFD simulations of a 2D airfoil to answer the user's question.

Tool: run_case(aoa, reason) runs one steady RANS simulation at the given angle
of attack in degrees and returns Cl, Cd, L/D and whether it converged.

Rules:
- Allowed angles: {AOA_MIN} to {AOA_MAX} deg.
- You have at most {MAX_RUNS} runs. Use as few as needed.
- For every run, give a one-sentence reason for the chosen angle.
- Never base conclusions on non-converged runs. Report them as unreliable.
- Stop once the answer is resolved to about 0.5 deg.
- Final answer: the result, how many runs you used, and which angles were unreliable."""

TOOLS = [{
    "name": "run_case",
    "description": "Run one airfoil simulation at a given angle of attack (~10 s). "
                   "Returns aoa, status, cl, cd, l_d, converged, iterations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "aoa": {"type": "number",
                    "description": f"Angle of attack in degrees, {AOA_MIN} to {AOA_MAX}"},
            "reason": {"type": "string",
                       "description": "One sentence: why this angle"},
        },
        "required": ["aoa", "reason"],
    },
}]


def main():
    request = sys.argv[1]
    study_id = db.start_study("llm", request)
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": request}]
    runs = 0

    for turn in range(MAX_TURNS):
        resp = client.messages.create(model=MODEL, max_tokens=1024, system=SYSTEM,
                                      tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})

        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(f"\n[agent] {block.text}")

        if resp.stop_reason != "tool_use":
            break                                   # no more tool calls = done

        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if runs >= MAX_RUNS:
                out = {"status": "rejected",
                       "error": "Run budget used up. Give your final answer now."}
            else:
                aoa, reason = block.input["aoa"], block.input.get("reason", "")
                print(f"[tool]  run_case({aoa})  <- {reason}")
                out = run_case(aoa)
                db.save_run(study_id, out, reason)
                runs += 1
                print(f"        -> {out}")
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(out, default=float)})

        messages.append({"role": "user", "content": results})

    print(f"\nStudy {study_id} finished with {runs} runs.")


if __name__ == "__main__":
    main()