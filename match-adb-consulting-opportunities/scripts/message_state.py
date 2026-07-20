#!/usr/bin/env python3

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


STATE_PATH = Path(
    os.environ.get(
        "ADB_OPPORTUNITY_STATE_PATH",
        Path.home() / ".codex" / "state" / "adb-opportunity-matcher.json",
    )
).expanduser()


def load_state():
    if not STATE_PATH.exists():
        return {"processed": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"processed": {}}
    if not isinstance(data.get("processed"), dict):
        data["processed"] = {}
    return data


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    processed = state.get("processed", {})
    if len(processed) > 100:
        ordered = sorted(
            processed.items(),
            key=lambda item: item[1].get("processed_at", ""),
            reverse=True,
        )[:100]
        state["processed"] = dict(ordered)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(STATE_PATH)


def main():
    parser = argparse.ArgumentParser(description="Track processed ADB Gmail messages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("message_id")

    mark = subparsers.add_parser("mark")
    mark.add_argument("message_id")
    mark.add_argument("--subject", default="")
    mark.add_argument("--received-at", default="")

    args = parser.parse_args()
    state = load_state()

    if args.command == "status":
        print("processed" if args.message_id in state["processed"] else "new")
        return

    state["processed"][args.message_id] = {
        "subject": args.subject,
        "received_at": args.received_at,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)
    print("marked")


if __name__ == "__main__":
    main()
