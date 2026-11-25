#!/usr/bin/env python3
"""Magic Mailbox Multi-Genre Generalization Engine (v0.2.1 · Frozen v0.1.4 Art Baseline).

Strictly preserves all v0.1.4 frozen creative assets (including v0.1.4 handwriting & doodle upgrades), asset lock checks, stage content hash
recomputation, freeze-overwrite protection, and deterministic compilation — extended only to
select any authentic chapter from `generalization_suite_5.json` (P05/3, P12/2, P23/1, P39/3, P47/1)
or `book_p30_4` (P30/4). Zero new artistic rules added.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import secrets
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from asset_guard import verify_all, load_lock

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EXP_ROOT = BASE_DIR / "exp_runs"

STAGE_ORDER = (
    ("step1", "step1_draw.json", "step1_draw"),
    ("step2", "step2_story.json", "step2_story"),
    ("step3", "step3_letter_draft.json", "step3_letter_draft"),
    ("step4", "step4_letter_final.json", "step4_letter_final"),
    ("step5", "step5_inner_photo.json", "step5_inner_photo"),
    ("step6", "step6_outer_tactile.json", "step6_outer_tactile"),
)

SYSTEM_META_LEAK_TOKENS = (
    "LOCK-000",
    "MAIL-005",
    "MB-E00",
    "VERSION_MISMATCH",
    "production_writes_allowed",
    "stage_token",
    "asset_lock.json",
    "partner_aesthetic",
    "partner_style_note",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ms() -> int:
    return int(time.time() * 1000)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: object) -> str:
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def compute_stage_content_sha256(stage_data: dict) -> str:
    payload = {k: v for k, v in stage_data.items() if k != "stage_sha256"}
    return sha256_obj(payload)


def fail_json(code: str, message: str, exit_code: int = 2, **extra) -> None:
    err = {"ok": False, "error": code, "message": message, **extra}
    sys.stderr.write(json.dumps(err, ensure_ascii=False, indent=2) + "\n")
    sys.exit(exit_code)


def read_asset(lock: dict, asset_id: str) -> str:
    rel = lock["assets"][asset_id]["path"]
    return (BASE_DIR / rel).read_text(encoding="utf-8").strip()


def read_role_card(lock: dict) -> dict:
    return json.loads(read_asset(lock, "role_card"))


def extract_visual_identity_verbatim(role_card: dict) -> str:
    vi = role_card["visual_identity"]
    return "\n".join([vi["identity"], vi["appearance"], vi["continuity"]])


def load_chapter_catalog(lock: dict, gender_filter: str | None = None) -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    pub_lib = json.loads(read_asset(lock, "library_100books_public"))
    allowed = ("全部", gender_filter) if gender_filter in ("女", "男") else ("全部", "女", "男")
    all_books = list(pub_lib.get("books", []))
    # Optional local custom_books.json extension
    custom_path = BASE_DIR / "assets" / "books" / "custom_books.json"
    if custom_path.exists():
        custom_lib = json.loads(custom_path.read_text(encoding="utf-8"))
        all_books.extend(custom_lib.get("books", []))
    for b in all_books:
        for ch in b.get("chapters", []):
            g = ch.get("gender", "全部")
            if g not in allowed:
                continue
            key = f"{b['id']}/{ch['id']}"
            catalog[key] = {
                "chapter_key": key,
                "shelf_id": b["shelf_id"],
                "book_id": b["id"],
                "book_title": b["title"],
                "chapter_id": ch["id"],
                "chapter_title": ch["title"],
                "gender": g,
                "world_logic": b.get("world_logic", ""),
                "point": ch["point"],
                "generalization_dimension": b.get("theme", b.get("batch", "100本公开书库")),
            }
    return catalog


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir:
        return Path(args.run_dir)
    chap = getattr(args, "chapter", None) or "P30/4"
    slug = chap.replace("/", "_")
    return DEFAULT_EXP_ROOT / slug


def require_clean_assets() -> tuple[dict, str]:
    check = verify_all()
    if not check["ok"]:
        sys.stderr.write(json.dumps(check, ensure_ascii=False, indent=2) + "\n")
        sys.exit(2)
    lock = load_lock()
    return lock, sha256_obj(lock["assets"])


def ensure_not_frozen(run_dir: Path, filename: str, stage_label: str) -> None:
    p = run_dir / filename
    if p.exists():
        fail_json(
            "STAGE_ALREADY_FROZEN",
            f"阶段 {stage_label} 已冻结落盘，禁止普通重复执行静默覆盖。如需重新运行，请显式执行 `rollback` 或 `reset --confirm`。",
            exit_code=5,
            frozen_file=filename,
        )


def write_stage(run_dir: Path, filename: str, data: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    p = run_dir / filename
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def load_and_verify_chain(run_dir: Path, up_to_index: int, current_asset_lock_sha: str) -> list[dict]:
    loaded: list[dict] = []
    expected_event_id: str | None = None
    expected_parent_sha: str | None = None

    for idx in range(up_to_index + 1):
        _, filename, expected_stage_name = STAGE_ORDER[idx]
        p = run_dir / filename
        if not p.is_file():
            fail_json(
                "MISSING_UPSTREAM_ARTIFACT",
                f"拒绝执行：缺少上游冻结产物 {expected_stage_name}，必须按顺序完成前置步骤。",
                exit_code=3,
                missing_stage=expected_stage_name,
                expected_file=filename,
            )
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("stage") != expected_stage_name:
            fail_json(
                "STAGE_SCHEMA_MISMATCH",
                f"文件 {filename} 的 stage 字段与预期不符。",
                exit_code=6,
                expected=expected_stage_name,
                actual=data.get("stage"),
            )

        recomputed_sha = compute_stage_content_sha256(data)
        recorded_sha = data.get("stage_sha256")
        if recomputed_sha != recorded_sha:
            fail_json(
                "STAGE_CONTENT_TAMPERED",
                f"检测到已冻结中间产物 {filename} 被篡改：实际内容重算摘要与记录的 stage_sha256 不一致！",
                exit_code=6,
                stage=expected_stage_name,
                recorded_sha256=recorded_sha,
                recomputed_sha256=recomputed_sha,
            )

        if idx == 0:
            expected_event_id = data.get("event_id")
            if data.get("asset_lock_sha256") != current_asset_lock_sha:
                fail_json(
                    "MID_RUN_ASSET_DRIFT",
                    "检测到运行中途资产版本/指纹发生变化！同一封信全程必须基于同一份锁定的资产快照。",
                    exit_code=7,
                    step1_asset_lock_sha256=data.get("asset_lock_sha256"),
                    current_asset_lock_sha256=current_asset_lock_sha,
                )
        else:
            if data.get("event_id") != expected_event_id:
                fail_json(
                    "CROSS_EVENT_MISMATCH",
                    f"检测到跨事件产物混用：{filename} 的 event_id 与 step1 不一致！",
                    exit_code=6,
                    stage=expected_stage_name,
                    expected_event_id=expected_event_id,
                    actual_event_id=data.get("event_id"),
                )
            if data.get("parent_sha256") != expected_parent_sha:
                fail_json(
                    "LINEAGE_BROKEN",
                    f"检测到上游血缘断裂：{filename} 的 parent_sha256 与上一阶段实际内容摘要不匹配！",
                    exit_code=6,
                    stage=expected_stage_name,
                    expected_parent_sha256=expected_parent_sha,
                    actual_parent_sha256=data.get("parent_sha256"),
                )
            if data.get("asset_lock_sha256") != current_asset_lock_sha:
                fail_json(
                    "MID_RUN_ASSET_DRIFT",
                    f"检测到 {filename} 记录的资产指纹与当前 asset_lock.json 不一致。",
                    exit_code=7,
                    stage=expected_stage_name,
                )

        if expected_stage_name == "step3_letter_draft":
            if sha256_text(data["letter_draft"]) != data.get("letter_draft_sha256"):
                fail_json("STAGE_CONTENT_TAMPERED", "step3 初稿正文与 letter_draft_sha256 不一致。", exit_code=6)
        elif expected_stage_name == "step4_letter_final":
            if sha256_text(data["letter_final"]) != data.get("letter_final_sha256"):
                fail_json("STAGE_CONTENT_TAMPERED", "step4 定稿正文与 letter_final_sha256 不一致。", exit_code=6)
            prev_draft = loaded[2]["letter_draft"]
            if data.get("kept_original_draft") != (data["letter_final"] == prev_draft):
                fail_json("STAGE_CONTENT_TAMPERED", "step4 kept_original_draft 标志与实际初稿/定稿比对不符。", exit_code=6)

        expected_parent_sha = recomputed_sha
        loaded.append(data)

    return loaded


def load_text_arg(inline_val: str | None, file_path: str | None, label: str) -> str:
    if file_path:
        txt = Path(file_path).read_text(encoding="utf-8").strip()
    elif inline_val is not None:
        txt = inline_val.strip()
    else:
        raise ValueError(f"必须提供 {label}")
    if not txt:
        raise ValueError(f"{label} 不能为空")
    return txt


def load_json_arg(inline_val: str | None, file_path: str | None, label: str) -> dict:
    raw = load_text_arg(inline_val, file_path, label)
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError(f"{label} 必须是 JSON 对象")
    return obj


def check_system_meta_leak(text: str, field_name: str) -> None:
    hits = [tok for tok in SYSTEM_META_LEAK_TOKENS if tok in text]
    if hits:
        fail_json(
            "SYSTEM_META_LEAK_DETECTED",
            "检测到系统内部治理标识符或内部偏好元键名混入创作正文，请仅保留纯粹的艺术与画面表达。",
            exit_code=4,
            field=field_name,
            leaked_tokens=hits,
        )


LAYOUT_MODES = {
    "left_photo_3x4": {
        "canvas": "横向3:2",
        "photo_aspect": "竖向3:4",
        "photo_aspect_code": "3:4",
        "opening": "仅一张横向3:2真实桌面俯拍照片，左侧自然摆放独立专业冲印竖向3:4旅行人物写真为主视觉，右侧完整展示中文亲笔信、信封与随信小物，整体带有真实拆信后自然摊开的微斜角与呼吸感。",
    },
    "right_photo_3x4": {
        "canvas": "横向3:2",
        "photo_aspect": "竖向3:4",
        "photo_aspect_code": "3:4",
        "opening": "仅一张横向3:2真实桌面俯拍照片，左侧完整展示中文亲笔信、信封与随信小物，右侧自然摆放独立专业冲印竖向3:4旅行人物写真为主视觉，整体带有真实拆信后自然摊开的微斜角与呼吸感。",
    },
    "collage_4x3_left": {
        "canvas": "横向3:2",
        "photo_aspect": "横向4:3",
        "photo_aspect_code": "4:3",
        "opening": "仅一张横向3:2真实桌面俯拍照片，左上方自然摆放独立专业冲印横向4:3旅行人物写真，左下方错落摆放信封与随信小物，右侧独立完整展示竖版中文亲笔信，整体呈现自然真实的桌面拼贴。",
    },
    "collage_4x3_right": {
        "canvas": "横向3:2",
        "photo_aspect": "横向4:3",
        "photo_aspect_code": "4:3",
        "opening": "仅一张横向3:2真实桌面俯拍照片，左侧独立完整展示竖版中文亲笔信，右上方自然摆放独立专业冲印横向4:3旅行人物写真，右下方错落摆放信封与随信小物，整体呈现自然真实的桌面拼贴。",
    },
    "top_photo_4x3_vertical": {
        "canvas": "竖向2:3",
        "photo_aspect": "横向4:3",
        "photo_aspect_code": "4:3",
        "opening": "仅一张竖向2:3真实桌面俯拍照片，上方自然摆放独立专业冲印横向4:3旅行人物写真为主视觉，下方占满充足舒展面积完整展示中文亲笔信、信封与随信小物，整体呈现真实随手摊拍的竖幅拆信质感。",
    },
    "bottom_photo_4x3_vertical": {
        "canvas": "竖向2:3",
        "photo_aspect": "横向4:3",
        "photo_aspect_code": "4:3",
        "opening": "仅一张竖向2:3真实桌面俯拍照片，上方占满充足舒展面积完整展示中文亲笔信、信封与随信小物，下方自然摆放独立专业冲印横向4:3旅行人物写真为主视觉，整体呈现真实随手摊拍的竖幅拆信质感。",
    },
}


def build_compiled_prompt(lock: dict, s1: dict, s2: dict, s4: dict, s5: dict, s6: dict) -> str:
    """Pure deterministic compiler: ZERO LLM involvement, verbatim injection of all frozen anchors."""
    book = s1["book"]
    role_card = read_role_card(lock)
    visual_identity = extract_visual_identity_verbatim(role_card)
    char_relationship = read_asset(lock, "character_relationship_prompt")
    wardrobe_anchor = read_asset(lock, "wardrobe_five_tiers")
    mail003_anchor = read_asset(lock, "handwriting_open_motivation_mail003")
    mail004_anchor = read_asset(lock, "doodles_open_motivation_mail004")

    world_line = f"世界逻辑：{book['world_logic']}\n" if book.get("world_logic") else ""

    layout_mode = s6.get("layout_mode", "left_photo_3x4")
    layout_spec = LAYOUT_MODES[layout_mode]
    opening = (
        "请使用 ChatGPT 原生图像生成创作一张全新原创、极其精美、照片级真实且富有电影摄影美感的私人旅行明信片静物摄影，不是编辑旧图。"
        + layout_spec["opening"]
        + "严格红线：照片画面完整无遮挡，整封中文亲笔原信占据充足清晰独立版面、每一字清晰可读且绝不被照片、信封、随信物或手绘涂鸦遮挡。追求人物出众美貌、自然神采、真实光影、独立服装及纸品艺术。"
    )

    return "\n\n".join([
        opening,
        f"【制作人】\n{book['book_id']}《{book['book_title']}》第{book['chapter_id']}章《{book['chapter_title']}》。{world_line}原始Point：{book['point']}\n{s2['producer_point']}",
        f"【人物与关系】\n{char_relationship}",
        f"【情绪导演】\n{s2['emotion_cause']}",
        f"【角色导演：容貌与体态】\n{visual_identity}\n{s5['visual_priority']}\n{s5['natural_character']}",
        f"【场景导演】\n{s5['scene']}",
        f"【服装导演】\n{wardrobe_anchor}\n{s5['wardrobe']}",
        f"【灯光导演】\n{s5['lighting']}",
        f"【摄影导演】\n{s5['camera']}",
        f"【信件编辑：完整原信，逐字可读】\n{s4['letter_final']}",
        f"【信纸导演】\n{s6['stationery']}",
        f"【随信物导演】\n{s6['keepsake']}",
        f"【书写导演】\n{mail003_anchor}\n{s6['handwriting']}",
        f"【手绘设计师】\n{mail004_anchor}\n{s6['doodles']}",
        f"【实体版式导演】\n{s6['tabletop']}",
    ])


def cmd_list_chapters(args: argparse.Namespace) -> int:
    lock, _ = require_clean_assets()
    catalog = load_chapter_catalog(lock)
    out = [
        {
            "chapter_key": k,
            "shelf_id": v["shelf_id"],
            "book_title": v["book_title"],
            "chapter_title": v["chapter_title"],
            "generalization_dimension": v["generalization_dimension"],
        }
        for k, v in catalog.items()
    ]
    print(json.dumps({"ok": True, "chapters": out}, ensure_ascii=False, indent=2))
    return 0


def cmd_step1_draw(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    catalog = load_chapter_catalog(lock)
    chap_key = args.chapter
    if chap_key not in catalog:
        fail_json("UNKNOWN_CHAPTER", f"未找到实验章节 {chap_key}，可用：{sorted(catalog.keys())}", exit_code=2)

    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step1_draw.json", "step1_draw")

    book = catalog[chap_key]
    slug = chap_key.replace("/", "_").lower()
    event_id = f"expgen_{slug}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
    run_nonce = secrets.token_hex(12)

    stage1 = {
        "stage": "step1_draw",
        "experiment_only": True,
        "production_writes_allowed": False,
        "event_id": event_id,
        "run_nonce": run_nonce,
        "timestamp_utc": now_iso(),
        "timestamp_ms": now_ms(),
        "chapter_key": chap_key,
        "book": book,
        "asset_versions": {k: v["version"] for k, v in lock["assets"].items()},
        "asset_lock_sha256": lock_sha,
    }
    stage1["stage_sha256"] = compute_stage_content_sha256(stage1)
    write_stage(run_dir, "step1_draw.json", stage1)

    print(f"=== STEP 1 完成：实验章节 {chap_key} 载入与 {len(lock['assets'])} 份冻结资产校验通过（正式历史/CD写入已关闭）===")
    print(f"event_id: {event_id}")
    print(f"run_dir:  {run_dir}")
    print("\n--- 本次原始书卡（唯一事实源）---")
    print(f"{book['book_id']}《{book['book_title']}》第{book['chapter_id']}章《{book['chapter_title']}》（书架 {book['shelf_id']}）")
    if book.get("world_logic"):
        print(f"世界逻辑：{book['world_logic']}")
    print(f"原始 Point：{book['point']}")
    print("\n--- 当前波次任务（波次 1：制作人与情绪因）---")
    print(read_asset(lock, "story_producer_brief"))
    print(f"\n【下一步行动】请仅围绕上述故事写出 JSON（包含键：producer_point, emotion_cause），不要提前构思服装/镜头/信件，然后调用 step2-story（带 --run-dir {run_dir}）。")
    return 0


def cmd_step2_story(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step2_story.json", "step2_story")
    (s1,) = load_and_verify_chain(run_dir, 0, lock_sha)

    story = load_json_arg(args.story_json, args.story_file, "story JSON")
    for k in ("producer_point", "emotion_cause"):
        if not isinstance(story.get(k), str) or not story[k].strip():
            raise ValueError(f"story JSON 缺少非空字段: {k}")
        check_system_meta_leak(story[k], k)

    stage2 = {
        "stage": "step2_story",
        "event_id": s1["event_id"],
        "parent_sha256": s1["stage_sha256"],
        "asset_lock_sha256": lock_sha,
        "timestamp_utc": now_iso(),
        "timestamp_ms": now_ms(),
        "producer_point": story["producer_point"].strip(),
        "emotion_cause": story["emotion_cause"].strip(),
    }
    stage2["stage_sha256"] = compute_stage_content_sha256(stage2)
    write_stage(run_dir, "step2_story.json", stage2)

    role_card = read_role_card(lock)
    rel_clean = {k: v for k, v in role_card["relationship"].items() if k != "partner_style_note"}
    letter_ctx = {
        "sender_name": role_card["sender_name"],
        "relationship": rel_clean,
        "letter_voice": role_card["letter_voice"],
    }
    book = s1["book"]

    print("=== STEP 2 完成：故事核与情绪因已冻结，进入【前置文学洁净室】===")
    print("（此时尚未加载任何服装、伴侣审美、镜头、摄影或纸品规则，请完全沉浸在角色灵魂与当下感受中写信。）\n")
    print("--- 角色卡 · 人物关系与书信人格原文 ---")
    print(json.dumps(letter_ctx, ensure_ascii=False, indent=2))
    print("\n" + read_asset(lock, "literary_persona"))
    print("\n--- 创作邀请 ---")
    print(f"此刻你刚经历完《{book['book_title']} · {book['chapter_title']}》这一幕，摊开信纸，只想把眼前的细节、冒出来的独特联想和想分享的心情慢慢写给远方的爱人。")
    print(f"请自由写出完整初稿（篇幅、节奏、含蓄或直白、落款完全由你自主决定），然后调用 step3-letter-draft（带 --run-dir {run_dir}）提交初稿。")
    return 0


def cmd_step3_letter_draft(args: argparse.Namespace) -> int:
    _, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step3_letter_draft.json", "step3_letter_draft")
    s1, s2 = load_and_verify_chain(run_dir, 1, lock_sha)

    draft = load_text_arg(args.draft, args.draft_file, "letter_draft")
    check_system_meta_leak(draft, "letter_draft")

    stage3 = {
        "stage": "step3_letter_draft",
        "event_id": s1["event_id"],
        "parent_sha256": s2["stage_sha256"],
        "asset_lock_sha256": lock_sha,
        "timestamp_utc": now_iso(),
        "timestamp_ms": now_ms(),
        "letter_draft": draft,
        "letter_draft_sha256": sha256_text(draft),
    }
    stage3["stage_sha256"] = compute_stage_content_sha256(stage3)
    write_stage(run_dir, "step3_letter_draft.json", stage3)

    print("=== STEP 3 完成：独立初稿已落盘，进入【纯文学重读】===")
    print(f"letter_draft_sha256: {stage3['letter_draft_sha256']}\n")
    print("请以欣赏者而非合规检查员的眼光重读你的初稿，思考以下三个问题：")
    print("1. 哪一处细节或联想最让人觉得“她真的站在那里、眼里闪着光”？")
    print("2. 有没有哪一段退化成了礼貌的景点说明、任务交差或常见明信片套话？")
    print("3. 收信人读完能否自然感受到这位恋人的独特心意与语言才华？")
    print(f"\n重要：若初稿已经自然动人，完全允许保留原样（调用 step4-letter-final --run-dir {run_dir} 时传入 --keep-draft）；若有值得展开之处，可自主润色定稿。")
    return 0


def cmd_step4_letter_final(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step4_letter_final.json", "step4_letter_final")
    s1, _, s3 = load_and_verify_chain(run_dir, 2, lock_sha)

    reread = load_text_arg(args.reread, args.reread_file, "letter_reread")
    check_system_meta_leak(reread, "letter_reread")

    if args.keep_draft:
        final_letter = s3["letter_draft"]
        kept_original = True
    else:
        final_letter = load_text_arg(args.final, args.final_file, "letter_final")
        check_system_meta_leak(final_letter, "letter_final")
        kept_original = (final_letter == s3["letter_draft"])

    stage4 = {
        "stage": "step4_letter_final",
        "event_id": s1["event_id"],
        "parent_sha256": s3["stage_sha256"],
        "asset_lock_sha256": lock_sha,
        "timestamp_utc": now_iso(),
        "timestamp_ms": now_ms(),
        "letter_reread": reread,
        "letter_final": final_letter,
        "letter_final_sha256": sha256_text(final_letter),
        "kept_original_draft": kept_original,
    }
    stage4["stage_sha256"] = compute_stage_content_sha256(stage4)
    write_stage(run_dir, "step4_letter_final.json", stage4)

    role_card = read_role_card(lock)
    print("=== STEP 4 完成：定稿原信已逐字冻结（下游只读），首次解锁【波次 4：内层旅行写真五岗资产】===")
    print(f"letter_final_sha256: {stage4['letter_final_sha256']} (kept_original_draft={kept_original})\n")
    print("--- 角色卡 · 权威视觉身份（英文原文由编译器自动注入一次，角色导演据此补写 visual_priority 与 natural_character）---")
    print(json.dumps(role_card["visual_identity"], ensure_ascii=False, indent=2))
    print("\n--- 角色卡 · 角色自主审美（personal_aesthetic，仅服装导演参考）---")
    print(json.dumps(role_card.get("personal_aesthetic", {}), ensure_ascii=False, indent=2))
    print("\n--- 服装魅力五档校准锚点（目标第三档；完整原文由编译器自动注入，服装导演专注写具体时装设计）---")
    print(read_asset(lock, "wardrobe_five_tiers"))
    print("\n--- 内层写真五岗权责 ---")
    print(read_asset(lock, "inner_photo_craft"))
    print("\n--- 现行 Space 权威 Cinematography 专业知识与神奇信箱适配准则（全文）---")
    print(read_asset(lock, "cinematography_authoritative"))
    print(f"\n【下一步行动】请专注于内层旅行写真（摄影导演可自主选择 photo_aspect: '3:4' 或 '4:3'，默认 '3:4'），提交 JSON（必需键：scene, wardrobe, visual_priority, natural_character, lighting, camera）至 step5-inner-photo（带 --run-dir {run_dir}）。不要提前写外层纸品与桌面。")
    return 0


def cmd_step5_inner_photo(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step5_inner_photo.json", "step5_inner_photo")
    s1, _, _, s4 = load_and_verify_chain(run_dir, 3, lock_sha)

    inner = load_json_arg(args.inner_json, args.inner_file, "inner_photo JSON")
    required_keys = ("scene", "wardrobe", "visual_priority", "natural_character", "lighting", "camera")
    for k in required_keys:
        if not isinstance(inner.get(k), str) or not inner[k].strip():
            raise ValueError(f"inner_photo JSON 缺少非空字段: {k}")
        check_system_meta_leak(inner[k], k)

    raw_aspect = inner.get("photo_aspect", "3:4")
    if not isinstance(raw_aspect, str) or raw_aspect.strip() not in ("3:4", "4:3"):
        fail_json(
            "INVALID_PHOTO_ASPECT",
            f"无效的 photo_aspect: {raw_aspect}，仅允许 '3:4' 或 '4:3'。",
            exit_code=4,
            photo_aspect=raw_aspect,
        )
    photo_aspect = raw_aspect.strip()

    stage5 = {
        "stage": "step5_inner_photo",
        "event_id": s1["event_id"],
        "parent_sha256": s4["stage_sha256"],
        "asset_lock_sha256": lock_sha,
        "timestamp_utc": now_iso(),
        "timestamp_ms": now_ms(),
        "photo_aspect": photo_aspect,
        **{k: inner[k].strip() for k in required_keys},
    }
    stage5["stage_sha256"] = compute_stage_content_sha256(stage5)
    write_stage(run_dir, "step5_inner_photo.json", stage5)

    role_card = read_role_card(lock)
    print("=== STEP 5 完成：内层旅行写真（含角色导演独立交稿）已冻结，首次解锁【波次 5：外层纸品与桌面静物资产】===\n")
    print("--- 已冻结原信（只读，供纸品/随信物/书写/手绘呼应）---")
    print(s4["letter_final"])
    print("\n--- 角色卡 · 书写与手绘固定人格 ---")
    print(json.dumps({
        "handwriting_personality": role_card["handwriting_personality"],
        "letter_art": role_card["letter_art"],
    }, ensure_ascii=False, indent=2))
    print("\n--- 书写导演自动继承锚点（MAIL-003 原文，编译器自动注入，供参考）---")
    print(read_asset(lock, "handwriting_open_motivation_mail003"))
    print("\n--- 手绘设计师自动继承锚点（MAIL-004 原文，编译器自动注入，供参考）---")
    print(read_asset(lock, "doodles_open_motivation_mail004"))
    print("\n--- 外层实体艺术专业资产 ---")
    print(read_asset(lock, "outer_tactile_craft"))
    matching_modes = [m for m, sp in LAYOUT_MODES.items() if sp["photo_aspect_code"] == photo_aspect]
    print(f"\n--- 第 5 步已锁定写真画幅：photo_aspect={photo_aspect} | 匹配可选 layout_mode：{matching_modes} ---")
    print(f"\n【下一步行动】请充分发挥外层纸品与静物独立艺术创造力，提交 JSON（必需键：stationery, keepsake, handwriting, doodles, tabletop；可选 layout_mode，必须与 photo_aspect={photo_aspect} 匹配）至 step6-compile（带 --run-dir {run_dir}）。")
    return 0


def cmd_step6_compile(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    ensure_not_frozen(run_dir, "step6_outer_tactile.json", "step6_outer_tactile")
    ensure_not_frozen(run_dir, "sealed_event.json", "sealed_event")
    s1, s2, s3, s4, s5 = load_and_verify_chain(run_dir, 4, lock_sha)

    outer = load_json_arg(args.outer_json, args.outer_file, "outer_tactile JSON")
    for k in ("stationery", "keepsake", "handwriting", "doodles", "tabletop"):
        if not isinstance(outer.get(k), str) or not outer[k].strip():
            raise ValueError(f"outer_tactile JSON 缺少非空字段: {k}")
        check_system_meta_leak(outer[k], k)

    s5_aspect = s5.get("photo_aspect", "3:4")
    if "layout_mode" in outer and outer["layout_mode"] is not None:
        raw_lm = outer["layout_mode"]
        if not isinstance(raw_lm, str) or raw_lm.strip() not in LAYOUT_MODES:
            fail_json(
                "INVALID_LAYOUT_MODE",
                f"无效的 layout_mode: {raw_lm}，可选值：{sorted(LAYOUT_MODES.keys())}",
                exit_code=4,
                layout_mode=raw_lm,
            )
        layout_mode = raw_lm.strip()
    else:
        if s5_aspect == "3:4":
            layout_mode = "left_photo_3x4"
        else:
            fail_json(
                "PHOTO_LAYOUT_ASPECT_MISMATCH",
                f"第 5 步写真画幅为 {s5_aspect}，必须在 step6 显式提交与之匹配的 4:3 版式（collage_4x3_left / collage_4x3_right / top_photo_4x3_vertical / bottom_photo_4x3_vertical）。",
                exit_code=4,
                step5_photo_aspect=s5_aspect,
                layout_mode=None,
            )

    expected_aspect = LAYOUT_MODES[layout_mode]["photo_aspect_code"]
    if expected_aspect != s5_aspect:
        fail_json(
            "PHOTO_LAYOUT_ASPECT_MISMATCH",
            f"画幅冲突拦截：第 5 步摄影导演确定的写真画幅为 {s5_aspect}，但第 6 步提交的 layout_mode={layout_mode} 要求 {expected_aspect}。外层版式必须承接内层画幅，不可冲突。",
            exit_code=4,
            step5_photo_aspect=s5_aspect,
            layout_mode=layout_mode,
            layout_required_photo_aspect=expected_aspect,
        )

    stage6_ts_iso = now_iso()
    stage6_ts_ms = now_ms()
    stage6 = {
        "stage": "step6_outer_tactile",
        "event_id": s1["event_id"],
        "parent_sha256": s5["stage_sha256"],
        "asset_lock_sha256": lock_sha,
        "timestamp_utc": stage6_ts_iso,
        "timestamp_ms": stage6_ts_ms,
        "layout_mode": layout_mode,
        "canvas_aspect": LAYOUT_MODES[layout_mode]["canvas"],
        "photo_aspect": LAYOUT_MODES[layout_mode]["photo_aspect"],
        "photo_aspect_code": s5_aspect,
        **{k: outer[k].strip() for k in ("stationery", "keepsake", "handwriting", "doodles", "tabletop")},
    }
    stage6["stage_sha256"] = compute_stage_content_sha256(stage6)
    write_stage(run_dir, "step6_outer_tactile.json", stage6)

    compiled_prompt = build_compiled_prompt(lock, s1, s2, s4, s5, stage6)
    check_system_meta_leak(compiled_prompt, "compiled_prompt")

    prompt_sha = sha256_text(compiled_prompt)
    timestamps_ms = [
        s1["timestamp_ms"], s2["timestamp_ms"], s3["timestamp_ms"],
        s4["timestamp_ms"], s5["timestamp_ms"], stage6_ts_ms,
    ]
    gaps_ms = [timestamps_ms[i + 1] - timestamps_ms[i] for i in range(len(timestamps_ms) - 1)]

    sealed = {
        "schema": "magic-mailbox-sealed-event-v1.0",
        "experiment_only": True,
        "production_writes_allowed": False,
        "chapter_key": s1["chapter_key"],
        "event_id": s1["event_id"],
        "run_nonce": s1["run_nonce"],
        "compiled_at_utc": now_iso(),
        "book": s1["book"],
        "role_profile_id": read_role_card(lock)["profile_id"],
        "asset_versions": s1["asset_versions"],
        "asset_lock_sha256": lock_sha,
        "lineage": {
            "step1_draw_sha256": s1["stage_sha256"],
            "step2_story_sha256": s2["stage_sha256"],
            "step3_letter_draft_sha256": s3["stage_sha256"],
            "step4_letter_final_sha256": s4["stage_sha256"],
            "step5_inner_photo_sha256": s5["stage_sha256"],
            "step6_outer_tactile_sha256": stage6["stage_sha256"],
        },
        "observability_note": "时间戳与重算哈希链仅证明沙盒落盘顺序、中间产物未被篡改与编译字节保真，不构成模型内部隐藏思考过程或艺术质量的证明。",
        "step_timestamps_utc": [
            s1["timestamp_utc"], s2["timestamp_utc"], s3["timestamp_utc"],
            s4["timestamp_utc"], s5["timestamp_utc"], stage6_ts_iso,
        ],
        "step_gaps_ms": gaps_ms,
        "kept_original_draft": s4["kept_original_draft"],
        "letter_draft_sha256": s3["letter_draft_sha256"],
        "letter_final_sha256": s4["letter_final_sha256"],
        "prompt_sha256": prompt_sha,
        "compiled_prompt": compiled_prompt,
    }

    (run_dir / "final_prompt.txt").write_text(compiled_prompt, encoding="utf-8")
    write_stage(run_dir, "sealed_event.json", sealed)

    print(f"=== STEP 6 完成：[{s1['chapter_key']}] 纯代码确定性编译与实验封签已生成 ===")
    print(f"event_id:             {s1['event_id']}")
    print(f"role_profile_id:      {sealed['role_profile_id']}")
    print(f"prompt_sha256:        {prompt_sha}")
    print(f"kept_original_draft:  {s4['kept_original_draft']}")
    print(f"step_gaps_ms:         {gaps_ms}")
    print(f"layout_mode:          {layout_mode} ({LAYOUT_MODES[layout_mode]['canvas']} 桌面 / {LAYOUT_MODES[layout_mode]['photo_aspect']} 写真)")
    print(f"final_prompt_path:    {run_dir / 'final_prompt.txt'}")
    print(f"sealed_event_path:    {run_dir / 'sealed_event.json'}")
    print("\n请读取 final_prompt.txt 原文作为【打开邮件】按钮载荷，切勿手动改写其中任何字符。")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    lock, lock_sha = require_clean_assets()
    run_dir = resolve_run_dir(args)
    s1, s2, s3, s4, s5, s6 = load_and_verify_chain(run_dir, 5, lock_sha)

    sealed_path = run_dir / "sealed_event.json"
    prompt_path = run_dir / "final_prompt.txt"
    if not sealed_path.is_file() or not prompt_path.is_file():
        fail_json("MISSING_SEALED_ARTIFACTS", "缺少 sealed_event.json 或 final_prompt.txt。", exit_code=3)

    sealed = json.loads(sealed_path.read_text(encoding="utf-8"))
    prompt_txt = prompt_path.read_text(encoding="utf-8")
    recomputed_prompt = build_compiled_prompt(lock, s1, s2, s4, s5, s6)
    role_card = read_role_card(lock)
    visual_identity = extract_visual_identity_verbatim(role_card)

    checks = {
        "experiment_isolated": (sealed.get("production_writes_allowed") is False and sealed.get("experiment_only") is True),
        "asset_lock_match": (sealed.get("asset_lock_sha256") == lock_sha and sealed.get("asset_versions") == {k: v["version"] for k, v in lock["assets"].items()}),
        "event_id_match": (sealed.get("event_id") == s1["event_id"]),
        "chapter_key_match": (sealed.get("chapter_key") == s1["chapter_key"]),
        "all_stage_content_hashes_recomputed_valid": True,
        "sealed_lineage_matches_recomputed": (
            sealed.get("lineage") == {
                "step1_draw_sha256": s1["stage_sha256"],
                "step2_story_sha256": s2["stage_sha256"],
                "step3_letter_draft_sha256": s3["stage_sha256"],
                "step4_letter_final_sha256": s4["stage_sha256"],
                "step5_inner_photo_sha256": s5["stage_sha256"],
                "step6_outer_tactile_sha256": s6["stage_sha256"],
            }
        ),
        "recompiled_prompt_byte_identical": (prompt_txt == recomputed_prompt and sealed.get("compiled_prompt") == recomputed_prompt),
        "prompt_sha256_match": (sha256_text(prompt_txt) == sealed.get("prompt_sha256") == sha256_text(recomputed_prompt)),
        "relationship_section_verbatim": (f"【人物与关系】\n{read_asset(lock, 'character_relationship_prompt')}" in prompt_txt),
        "visual_identity_verbatim": (visual_identity in prompt_txt),
        "character_director_outputs_present": (s5["visual_priority"] in prompt_txt and s5["natural_character"] in prompt_txt),
        "wardrobe_anchor_verbatim": (read_asset(lock, "wardrobe_five_tiers") in prompt_txt),
        "mail003_handwriting_anchor_verbatim": (read_asset(lock, "handwriting_open_motivation_mail003") in prompt_txt),
        "mail004_doodles_anchor_verbatim": (read_asset(lock, "doodles_open_motivation_mail004") in prompt_txt),
        "letter_final_verbatim": (s4["letter_final"] in prompt_txt),
        "no_system_meta_or_partner_note_leak": not any(tok in prompt_txt for tok in SYSTEM_META_LEAK_TOKENS),
    }
    report = {
        "ok": all(checks.values()),
        "chapter_key": s1["chapter_key"],
        "checks": checks,
        "kept_original_draft": s4["kept_original_draft"],
        "step_gaps_ms": sealed.get("step_gaps_ms"),
        "honest_disclaimer": "技术校验全绿仅代表资产保真、中间产物未被篡改、顺序落盘与确定性编译通过；艺术与文学质量仍须由人类盲评验收。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    if not args.confirm:
        fail_json("CONFIRMATION_REQUIRED", "回退已冻结阶段必须显式传入 --confirm。", exit_code=2)
    run_dir = resolve_run_dir(args)
    keys = [item[0] for item in STAGE_ORDER]
    if args.to not in keys:
        fail_json("INVALID_STAGE", f"未知回退目标：{args.to}，可选：{keys}", exit_code=2)
    start_idx = keys.index(args.to)
    removed = []
    for idx in range(start_idx, len(STAGE_ORDER)):
        p = run_dir / STAGE_ORDER[idx][1]
        if p.exists():
            p.unlink()
            removed.append(p.name)
    for extra in ("sealed_event.json", "final_prompt.txt"):
        p = run_dir / extra
        if p.exists():
            p.unlink()
            removed.append(p.name)
    log_path = run_dir / "rollback_log.json"
    logs = json.loads(log_path.read_text(encoding="utf-8")) if log_path.is_file() else []
    logs.append({"timestamp_utc": now_iso(), "action": "rollback", "to_stage": args.to, "removed_files": removed, "reason": args.reason})
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "action": "rollback", "to_stage": args.to, "removed_files": removed}, ensure_ascii=False, indent=2))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    if not args.confirm:
        fail_json("CONFIRMATION_REQUIRED", "重置实验目录必须显式传入 --confirm。", exit_code=2)
    run_dir = resolve_run_dir(args)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    print(json.dumps({"ok": True, "action": "reset", "run_dir": str(run_dir)}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", help="本次实验运行产物目录（默认自动按章节隔离为 exp_runs/<CHAPTER>）")
    ap.add_argument("--chapter", default="P30/4", help="实验章节键（如 P05/3, P12/2, P23/1, P39/3, P47/1, P30/4）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-chapters", help="列出全部可用多题材泛化测试章节")
    sub.add_parser("step1-draw")

    p2 = sub.add_parser("step2-story")
    p2.add_argument("--story-json")
    p2.add_argument("--story-file")

    p3 = sub.add_parser("step3-letter-draft")
    p3.add_argument("--draft")
    p3.add_argument("--draft-file")

    p4 = sub.add_parser("step4-letter-final")
    p4.add_argument("--reread")
    p4.add_argument("--reread-file")
    p4.add_argument("--final")
    p4.add_argument("--final-file")
    p4.add_argument("--keep-draft", action="store_true", help="重读后决定保留初稿原样")

    p5 = sub.add_parser("step5-inner-photo")
    p5.add_argument("--inner-json")
    p5.add_argument("--inner-file")

    p6 = sub.add_parser("step6-compile")
    p6.add_argument("--outer-json")
    p6.add_argument("--outer-file")

    sub.add_parser("verify")

    rb = sub.add_parser("rollback", help="显式回退至指定阶段（删除该阶段及所有下游冻结产物并记账）")
    rb.add_argument("--to", required=True, choices=[x[0] for x in STAGE_ORDER])
    rb.add_argument("--reason", default="explicit_experiment_rollback")
    rb.add_argument("--confirm", action="store_true")

    rs = sub.add_parser("reset", help="显式清空当前实验运行目录以重新开始")
    rs.add_argument("--confirm", action="store_true")

    args = ap.parse_args()
    handlers = {
        "list-chapters": cmd_list_chapters,
        "step1-draw": cmd_step1_draw,
        "step2-story": cmd_step2_story,
        "step3-letter-draft": cmd_step3_letter_draft,
        "step4-letter-final": cmd_step4_letter_final,
        "step5-inner-photo": cmd_step5_inner_photo,
        "step6-compile": cmd_step6_compile,
        "verify": cmd_verify,
        "rollback": cmd_rollback,
        "reset": cmd_reset,
    }
    try:
        return handlers[args.cmd](args)
    except Exception as exc:
        fail_json(type(exc).__name__, str(exc), exit_code=1)
        return 1


if __name__ == "__main__":
    sys.exit(main())
