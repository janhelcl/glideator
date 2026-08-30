from __future__ import annotations

import argparse
import json

from .config import load_config
from .s2s.run import backfill_s2s_tracking, run_s2s


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glideator-ml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a model experiment")
    run.add_argument("task", choices=["s2s"])
    run.add_argument("--config", required=True)

    backfill = subparsers.add_parser(
        "backfill",
        help="Backfill tracking from saved experiment artifacts",
    )
    backfill.add_argument("task", choices=["s2s"])
    backfill.add_argument("--config", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if config["task"] != args.task:
        raise SystemExit(
            f"Config task {config['task']!r} does not match CLI task {args.task!r}"
        )

    if args.command == "run" and args.task == "s2s":
        report = run_s2s(config)
    elif args.command == "backfill" and args.task == "s2s":
        report = backfill_s2s_tracking(config)
    else:
        raise SystemExit(f"Unsupported command/task: {args.command}/{args.task}")

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
