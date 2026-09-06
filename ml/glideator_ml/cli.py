from __future__ import annotations

import argparse
import json

from .config import load_config, require_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glideator-ml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a model experiment")
    run.add_argument("task", choices=["s2s", "xc"])
    run.add_argument("--config", required=True)

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Evaluate an existing production/reference artifact",
    )
    evaluate.add_argument("task", choices=["xc"])
    evaluate.add_argument("--config", required=True)

    compare = subparsers.add_parser(
        "compare",
        help="Compare a candidate with its promotion reference",
    )
    compare.add_argument("task", choices=["xc"])
    compare.add_argument("--config", required=True)

    backfill = subparsers.add_parser(
        "backfill",
        help="Backfill tracking from saved experiment artifacts",
    )
    backfill.add_argument("task", choices=["s2s", "xc"])
    backfill.add_argument("--config", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if config["task"] != args.task:
        raise SystemExit(
            f"Config task {config['task']!r} does not match CLI task {args.task!r}"
        )

    exit_code = 0
    if args.command == "evaluate":
        require_sections(config, "data", "evaluation", "reference", "artifact", "tracking")
        from .xc.reference import run_xc_onnx_reference

        report = run_xc_onnx_reference(config)
    elif args.command == "compare":
        require_sections(config, "artifact", "promotion")
        from .xc.promotion import run_xc_promotion_check

        report = run_xc_promotion_check(config)
        if not report["eligible"]:
            exit_code = 2
    elif args.task == "s2s":
        require_sections(config, "data", "model", "evaluation", "artifact", "tracking")
        from .s2s.run import backfill_s2s_tracking, run_s2s

        report = (
            run_s2s(config)
            if args.command == "run"
            else backfill_s2s_tracking(config)
        )
    elif args.task == "xc":
        require_sections(config, "data", "model", "evaluation", "artifact", "tracking")
        from .xc.run import backfill_xc_tracking, run_xc

        report = (
            run_xc(config)
            if args.command == "run"
            else backfill_xc_tracking(config)
        )
    else:
        raise SystemExit(f"Unsupported command/task: {args.command}/{args.task}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
