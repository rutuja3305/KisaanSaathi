from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .repository import KnowledgeRepository

_COLUMNS = (
    "scheme", "source", "authority_tier", "official_url", "current_version",
    "effective_date", "last_verified", "freshness", "validation_status",
)


def render_report(rows: list[dict[str, object]]) -> str:
    headers = ("Scheme", "Source", "Tier", "Official URL", "Current Version",
               "Effective Date", "Last Verified", "Freshness", "Validation")
    values = [headers]
    for row in rows:
        values.append(tuple(str(row[column] or "-") for column in _COLUMNS))
    widths = [max(len(item[index]) for item in values) for index in range(len(headers))]
    return "\n".join(
        " | ".join(item[index].ljust(widths[index]) for index in range(len(headers)))
        for item in values
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Report government source validation state")
    parser.add_argument("--db", required=True, help="SQLite knowledge database path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    repository = KnowledgeRepository.from_path(args.db)
    try:
        report = repository.validation_report(now=datetime.now(timezone.utc))
        if args.as_json:
            print(json.dumps(report, indent=2))
        else:
            print(render_report(report))
            print("\nClassifications:")
            for classification in sorted({row["classification"] for row in report}):
                count = sum(row["classification"] == classification for row in report)
                print(f"- {classification}: {count}")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
