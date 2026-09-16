"""批量给 restaurants.json 自动打标并写回。"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tagging import auto_tags  # noqa: E402

DATA_PATH = ROOT / "data" / "restaurants.json"


def main() -> None:
    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for item in items:
        item["tags"] = auto_tags(item["name"])
    DATA_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counter: Counter[str] = Counter()
    for item in items:
        for tag in item["tags"]:
            counter[tag] += 1
        print(f"{item['name']}\t{', '.join(item['tags'])}")
    print("\n=== 标签分布 ===")
    for tag, n in counter.most_common():
        print(f"{tag}\t{n}")


if __name__ == "__main__":
    main()
