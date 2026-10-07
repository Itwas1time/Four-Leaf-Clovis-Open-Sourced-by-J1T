"""Compare archaeological research areas with the bundled offline evidence.

Examples:
    python3 -m cli.discovery --bbox 34,-112,35,-111 --name "Arizona study area"
    python3 -m cli.discovery --candidates candidates.json --json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from core.discovery_planner import rank_candidates


def _parse_bbox(value: str) -> list[float]:
    try:
        bounds = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox must contain four numbers") from exc
    if len(bounds) != 4:
        raise argparse.ArgumentTypeError("bbox must be min_lat,min_lon,max_lat,max_lon")
    return bounds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clovis-plan",
        description="Compare research areas using local records and sourced observations. Scores are not discovery probabilities.",
    )
    parser.add_argument("--bbox", action="append", type=_parse_bbox, help="Study area; may be repeated")
    parser.add_argument("--name", action="append", help="Name corresponding to each --bbox")
    parser.add_argument("--candidates", type=Path, help="JSON file with a candidates array")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args(argv)

    if args.candidates:
        try:
            data = json.loads(args.candidates.read_text(encoding="utf-8"))
            candidates = data["candidates"] if isinstance(data, dict) else data
            if not isinstance(candidates, list):
                raise ValueError("candidates must be a list")
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            parser.error(f"Could not read candidates: {exc}")
    else:
        if not args.bbox:
            parser.error("Provide --bbox or --candidates")
        names = args.name or []
        if len(names) > len(args.bbox):
            parser.error("More --name values than --bbox values")
        candidates = [
            {"name": names[index] if index < len(names) else f"Study area {index + 1}", "bbox": bounds}
            for index, bounds in enumerate(args.bbox)
        ]

    try:
        results = rank_candidates(candidates)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps({"candidates": results}, indent=2))
        return 0

    print("CLOVIS | Discovery research planner")
    print(
        "Priority uses user-supplied strengths. Clovis has not verified sources or independence; "
        "the index is not a discovery probability or permission to dig.\n"
    )
    for row in results:
        rank = f"#{row['research_rank']}" if row["research_rank"] else "Unranked"
        index = f"{row['priority_index']:.1f}/100" if row["priority_index"] is not None else "insufficient independent evidence"
        context = row["documented_context"]
        print(f"{rank}  {row['name']} | {index}")
        print(f"  Target period: {row['target_period']} (not matched to bundled records) | Claimed permission: {row['permission_status']}")
        if row["independent_signals"]:
            print("  Counted user-supplied signals (unverified):")
            for signal in row["independent_signals"]:
                print(
                    f"    {signal['kind']} {signal['strength']:.2f} | "
                    f"source: {signal['source']} | observation: {signal['observation']}"
                )
        else:
            print("  Counted user-supplied signals: none")
        print(f"  Documented context: {context['open_context_site_records']} Open Context site records, "
              f"{context['nrhp_explicit_archaeology_records']} explicit archaeology NRHP records")
        if row["possible_find_classes"]:
            hints = ", ".join(item["class"] for item in row["possible_find_classes"])
            print(f"  Possible context from known records: {hints}")
        else:
            print("  Possible find class: unknown")
        print(f"  Context limit: {row['finds_note']}")
        print(f"  Next step: {row['next_step']}")
        print(f"  Fieldwork: {row['fieldwork_status']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
