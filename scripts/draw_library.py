#!/usr/bin/env python3
"""True-random shelf drawer with automatic gender filtering from assets/roles/role_card.json."""
import argparse
import json
import secrets
from engine import require_clean_assets, load_chapter_catalog, read_role_card


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", help="List eligible chapters for a specific book ID (e.g. P30)")
    parser.add_argument("--gender", choices=("女", "男"), help="Override gender filter (defaults to role_card.json)")
    args = parser.parse_args()

    lock, _ = require_clean_assets()
    rc = read_role_card(lock)
    target_gender = args.gender or rc.get("gender", "女")
    allowed = ("全部", target_gender)

    catalog = load_chapter_catalog(lock, gender_filter=target_gender)
    assert all(c["gender"] in allowed for c in catalog.values())

    shelves: dict[str, dict[str, list[dict]]] = {}
    for c in catalog.values():
        shelves.setdefault(c["shelf_id"], {}).setdefault(c["book_id"], []).append(c)

    if args.book:
        cs = [c for c in catalog.values() if c["book_id"] == args.book]
        if not cs:
            parser.error(f"unknown or ineligible book for gender={target_gender}: {args.book}")
        out = {
            "gender_filter": target_gender,
            "book": args.book,
            "book_title": cs[0]["book_title"],
            "shelf_id": cs[0]["shelf_id"],
            "chapters": [{k: c[k] for k in ("chapter_key", "chapter_title", "gender")} for c in cs],
        }
    else:
        shelf = secrets.choice(sorted(shelves))
        out = {
            "gender_filter": target_gender,
            "shelf": shelf,
            "books": [
                {"book_id": bid, "book_title": chs[0]["book_title"], "eligible_chapters": len(chs)}
                for bid, chs in sorted(shelves[shelf].items())
            ],
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
