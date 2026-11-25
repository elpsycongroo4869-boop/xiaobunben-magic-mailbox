#!/usr/bin/env python3
"""Independent Asset Lockfile Guard for Magic Mailbox (v0.1.1).

Prevents accidental cross-module mutation, silent summarization, or full-doc overwrites
during iterative development. Pure Python standard library.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCK_PATH = BASE_DIR / "assets" / "asset_lock.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lock(lock_path: Path = LOCK_PATH) -> dict:
    if not lock_path.is_file():
        raise FileNotFoundError(f"Asset lockfile missing: {lock_path}")
    return json.loads(lock_path.read_text(encoding="utf-8"))


def scan_drift(lock: dict, base_dir: Path = BASE_DIR) -> tuple[list[dict], list[dict]]:
    changed = []
    missing = []
    for aid, meta in lock["assets"].items():
        p = base_dir / meta["path"]
        if not p.is_file():
            missing.append({"asset_id": aid, "path": meta["path"]})
            continue
        actual_sha = sha256_file(p)
        if actual_sha != meta["sha256"]:
            changed.append({
                "asset_id": aid,
                "path": meta["path"],
                "expected_version": meta["version"],
                "expected_sha256": meta["sha256"],
                "actual_sha256": actual_sha,
                "expected_bytes": meta["bytes"],
                "actual_bytes": p.stat().st_size,
            })
    return changed, missing


def verify_all(lock_path: Path = LOCK_PATH, base_dir: Path = BASE_DIR) -> dict:
    lock = load_lock(lock_path)
    changed, missing = scan_drift(lock, base_dir)
    if missing or changed:
        return {
            "ok": False,
            "error": "ASSET_LOCK_MISMATCH",
            "missing": missing,
            "changed": changed,
            "hint": "检测到未登记的资产变更。若为授权修改，请使用 asset_guard.py update --allow <asset_id> 显式升级；若为误改，请恢复原文件。",
        }
    return {
        "ok": True,
        "experiment_id": lock.get("experiment_id"),
        "asset_count": len(lock["assets"]),
        "versions": {k: v["version"] for k, v in lock["assets"].items()},
    }


def _bump_patch(ver: str) -> str:
    parts = ver.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
    return ver + ".1"


def cmd_update(args: argparse.Namespace) -> int:
    lock = load_lock(LOCK_PATH)
    allowed = set(args.allow)
    unknown = allowed - set(lock["assets"].keys())
    if unknown:
        print(json.dumps({"ok": False, "error": "UNKNOWN_ASSET_ID", "unknown": sorted(unknown)}, ensure_ascii=False, indent=2))
        return 2

    changed, missing = scan_drift(lock, BASE_DIR)
    if missing:
        print(json.dumps({"ok": False, "error": "MISSING_ASSET_FILES", "missing": missing}, ensure_ascii=False, indent=2))
        return 2

    unauthorized = [c for c in changed if c["asset_id"] not in allowed]
    if unauthorized:
        print(json.dumps({
            "ok": False,
            "error": "UNAUTHORIZED_CROSS_MODULE_MUTATION",
            "allowed_assets": sorted(allowed),
            "unauthorized_changes": unauthorized,
            "message": "拒绝更新锁文件！检测到未授权模块发生变动，请先还原未授权模块再升级目标资产。",
        }, ensure_ascii=False, indent=2))
        return 3

    updated = []
    for c in changed:
        aid = c["asset_id"]
        old_ver = lock["assets"][aid]["version"]
        new_ver = args.bump if len(allowed) == 1 and args.bump else _bump_patch(old_ver)
        lock["assets"][aid]["version"] = new_ver
        lock["assets"][aid]["sha256"] = c["actual_sha256"]
        lock["assets"][aid]["bytes"] = c["actual_bytes"]
        updated.append({"asset_id": aid, "old_version": old_ver, "new_version": new_ver, "sha256": c["actual_sha256"]})

    if not updated:
        print(json.dumps({"ok": True, "updated": [], "message": "所选授权资产内容未发生变化，无需更新。"}, ensure_ascii=False, indent=2))
        return 0

    lock.setdefault("audit_log", []).append({
        "timestamp": now_iso(),
        "action": "authorized_update",
        "allowed_assets": sorted(allowed),
        "updated": updated,
        "reason": args.reason,
    })
    LOCK_PATH.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "updated": updated}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="校验全部独立资产是否与 asset_lock.json 指纹完全一致")
    upd = sub.add_parser("update", help="仅允许升级显式授权的资产模块，若其他模块有未授权改动则报错拒绝")
    upd.add_argument("--allow", nargs="+", required=True, help="本次授权修改的 asset_id 列表")
    upd.add_argument("--bump", help="单模块升级时显式指定新版本号（可选，默认 patch+1）")
    upd.add_argument("--reason", required=True, help="修改原因说明")
    args = ap.parse_args()

    if args.cmd == "verify":
        res = verify_all()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1
    if args.cmd == "update":
        return cmd_update(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
