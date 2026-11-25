#!/usr/bin/env python3
"""Activate a complete default profile; do not modify immutable presets."""
import argparse
import json
from asset_guard import BASE_DIR, LOCK_PATH, load_lock, verify_all, sha256_file, now_iso


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("female", "male"))
    args = parser.parse_args()
    if not verify_all()["ok"]:
        parser.error("ASSET_LOCK_MISMATCH: restore or authorize existing changes first")
    lock = load_lock()
    presets = json.loads((BASE_DIR / lock["assets"]["default_profiles"]["path"]).read_text(encoding="utf-8"))
    card = presets[args.profile]
    path = BASE_DIR / lock["assets"]["role_card"]["path"]
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta = lock["assets"]["role_card"]
    meta.update(sha256=sha256_file(path), bytes=path.stat().st_size)
    lock.setdefault("audit_log", []).append({"timestamp": now_iso(), "action": "activate_default_profile", "profile": args.profile, "sha256": meta["sha256"]})
    LOCK_PATH.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert verify_all()["ok"]
    print(json.dumps({"ok": True, "profile": args.profile, "sender_name": card["sender_name"], "gender": card["gender"], "trigger_command": card["trigger_command"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
