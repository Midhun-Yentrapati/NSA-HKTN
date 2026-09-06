"""Ask the running Cadence network a question from the command line.

    python scripts/ask.py "I have today - what should I work on?"
    python scripts/ask.py --trace "What did I miss?"

--trace also prints which agents participated, which is the interesting part
when demonstrating the network rather than the answer.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:8081/api/v1/cadence/streaming_chat"
AGENT_NAMES = ("Cadence", "TimeKeeper", "WorkTracker", "LearningCoach",
               "MemoryKeeper", "DayPlanner", "PlanCritic")


def out(text: str) -> None:
    """Print without dying on a Windows console that cannot encode the character."""
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(str(text).encode(encoding, errors="replace").decode(encoding) + "\n")


def ask(question: str, url: str, timeout: int, trace: bool) -> int:
    body = {"user_message": {"text": question}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        out(f"HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:500]}")
        return 1
    except Exception as error:  # noqa: BLE001 - surface whatever went wrong
        out(f"{type(error).__name__}: {error}")
        return 1

    elapsed = time.time() - started
    lines = [line for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        out("Empty response.")
        return 1
    payload = json.loads(lines[-1]).get("response", {})

    if trace:
        participants = []
        for history in payload.get("chat_context", {}).get("chat_histories", []):
            for message in history.get("messages", []):
                text = message.get("text", "")
                if '"Name"' in text:
                    for name in AGENT_NAMES:
                        if f'"{name}"' in text and name not in participants:
                            participants.append(name)
        out("AGENTS THAT PARTICIPATED: " + (", ".join(participants) or "(none detected)"))
        out("")

    out(payload.get("text", "(no answer)"))
    out("")
    out(f"[{elapsed:.0f}s]")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the Cadence agent network a question.")
    parser.add_argument("question", help="What to ask.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--trace", action="store_true", help="Show which agents participated.")
    args = parser.parse_args()
    return ask(args.question, args.url, args.timeout, args.trace)


if __name__ == "__main__":
    raise SystemExit(main())
