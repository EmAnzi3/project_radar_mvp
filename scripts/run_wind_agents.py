#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.wind_agents.planner import build_run_plan
from app.wind_agents.runner import executable_agent_ids, run_agents


def main() -> None:
    parser = argparse.ArgumentParser(description="Wind Radar agent runner")
    sub = parser.add_subparsers(dest="command", required=True)

    plan_cmd = sub.add_parser("plan", help="build the due queue without network collection")
    plan_cmd.add_argument("--as-of", help="YYYY-MM-DD; defaults to today")
    plan_cmd.add_argument("--output", help="optional JSON output path")

    run_cmd = sub.add_parser("run", help="execute implemented source adapters")
    run_cmd.add_argument(
        "--source",
        action="append",
        choices=executable_agent_ids(),
        help="source adapter to run; repeatable; default = all implemented",
    )

    args = parser.parse_args()

    if args.command == "plan":
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        payload = build_run_plan(as_of=as_of).as_dict()
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        print(text)
        return

    result = run_agents(args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
