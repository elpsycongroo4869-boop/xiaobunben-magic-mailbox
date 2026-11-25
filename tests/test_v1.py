#!/usr/bin/env python3
"""Automated verification suite for xiaobunben-magic-mailbox v1.0.0 Public Release Candidate."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent


class MagicMailboxV1ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="mb_v100_rc_")
        self.pkg = Path(self._td.name) / "pkg"
        shutil.copytree(PKG_ROOT, self.pkg, ignore=shutil.ignore_patterns("exp_runs", "__pycache__"))
        self.eng = str(self.pkg / "scripts/engine.py")
        self.guard = str(self.pkg / "scripts/asset_guard.py")
        self.drawer = str(self.pkg / "scripts/draw_library.py")

    def tearDown(self) -> None:
        self._td.cleanup()

    def run_cli(self, script: str, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, script, *args], cwd=self.pkg, capture_output=True, text=True)

    def test_01_asset_lock_and_immutable_v014_history(self) -> None:
        res = self.run_cli(self.guard, ["verify"])
        self.assertEqual(res.returncode, 0, res.stderr)
        obj = json.loads(res.stdout)
        self.assertTrue(obj["ok"])
        self.assertEqual(obj["asset_count"], 11)
        lock = json.loads((self.pkg / "assets/asset_lock.json").read_text(encoding="utf-8"))
        self.assertEqual(len(lock["v014_frozen_baseline_sha256"]), 11)
        self.assertEqual(
            lock["v014_frozen_baseline_sha256"]["outer_tactile_craft"],
            "386751c2aa5061845c1447be6c5a27e9d443509342d4736bce51eb702ec434b6",
        )

    def test_02_zero_personal_info_leaks(self) -> None:
        banned = re.compile(r"0408|零四零八|老公|黑丝|丝袜(?!奶茶)|chatgpt\.com/space|page_949")
        for root, dirs, files in os.walk(self.pkg):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "exp_runs")]
            for fn in files:
                if fn == "test_v1.py" or fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                    continue
                fp = Path(root) / fn
                txt = fp.read_text(encoding="utf-8", errors="ignore")
                hits = banned.findall(txt)
                self.assertFalse(hits, f"Privacy leak {hits} found in {fp.relative_to(self.pkg)}")

    def test_03_public_100books_shuffled_and_both_genders(self) -> None:
        lib = json.loads((self.pkg / "assets/books/library_100books_public.json").read_text(encoding="utf-8"))
        self.assertEqual(len(lib["books"]), 100)
        self.assertEqual(len(lib["shelves"]), 10)
        self.assertTrue(all(s["book_count"] == 10 for s in lib["shelves"]))
        for g in ("女", "男"):
            r1 = self.run_cli(self.drawer, ["--gender", g])
            self.assertEqual(r1.returncode, 0, r1.stderr)
            d1 = json.loads(r1.stdout)
            self.assertEqual(len(d1["books"]), 10)
            r2 = self.run_cli(self.drawer, ["--gender", g, "--book", d1["books"][0]["book_id"]])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            d2 = json.loads(r2.stdout)
            self.assertTrue(all(c["gender"] in ("全部", g) for c in d2["chapters"]))

    def test_04_photo_layout_mismatch_blocked(self) -> None:
        rd = self.pkg / "exp_runs/mismatch_test"
        self.assertEqual(self.run_cli(self.eng, ["--chapter", "P30/4", "--run-dir", str(rd), "step1-draw"]).returncode, 0)
        self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step2-story", "--story-json", json.dumps({"producer_point": "红谷夕照比色", "emotion_cause": "惊喜分享"}, ensure_ascii=False)]).returncode, 0)
        self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step3-letter-draft", "--draft", "亲爱的，今天的晚霞分成了三层红。"]).returncode, 0)
        self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step4-letter-final", "--reread", "自然", "--keep-draft"]).returncode, 0)
        inner = json.dumps({"photo_aspect": "3:4", "scene": "红谷", "wardrobe": "浅米风衣", "visual_priority": "自然眼神", "natural_character": "舒展微笑", "lighting": "夕阳", "camera": "35mm"}, ensure_ascii=False)
        self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step5-inner-photo", "--inner-json", inner]).returncode, 0)
        outer = json.dumps({"layout_mode": "top_photo_4x3_vertical", "stationery": "棉纸", "keepsake": "色卡", "handwriting": "钢笔", "doodles": "小云朵", "tabletop": "石台"}, ensure_ascii=False)
        res = self.run_cli(self.eng, ["--run-dir", str(rd), "step6-compile", "--outer-json", outer])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("PHOTO_LAYOUT_ASPECT_MISMATCH", res.stdout + res.stderr)

    def test_05_female_and_male_full_pipeline_across_all_six_layouts(self) -> None:
        specs = [
            ("P30/4", "left_photo_3x4", "3:4", "横向3:2", "竖向3:4"),
            ("P30/4", "right_photo_3x4", "3:4", "横向3:2", "竖向3:4"),
            ("P68/1", "collage_4x3_left", "4:3", "横向3:2", "横向4:3"),
            ("P68/1", "collage_4x3_right", "4:3", "横向3:2", "横向4:3"),
            ("P39/3", "top_photo_4x3_vertical", "4:3", "竖向2:3", "横向4:3"),
            ("P39/3", "bottom_photo_4x3_vertical", "4:3", "竖向2:3", "横向4:3"),
        ]
        letter = "亲爱的：\n\n隔着屏幕没法见面，但我还是想把今天最真实的一刻写进信里寄给你。"
        for ck, mode, code, canvas, p_asp in specs:
            rd = self.pkg / f"exp_runs/v1_{mode}"
            self.assertEqual(self.run_cli(self.eng, ["--chapter", ck, "--run-dir", str(rd), "step1-draw"]).returncode, 0)
            self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step2-story", "--story-json", json.dumps({"producer_point": "真实旅途瞬间", "emotion_cause": "跨越距离的倾诉"}, ensure_ascii=False)]).returncode, 0)
            self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step3-letter-draft", "--draft", letter]).returncode, 0)
            self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step4-letter-final", "--reread", "真挚自然", "--keep-draft"]).returncode, 0)
            inner = json.dumps({"photo_aspect": code, "scene": "旅途实景", "wardrobe": "符合故事的独立穿搭", "visual_priority": "自然五官与眼神", "natural_character": "真实情绪流露", "lighting": "自然窗光与斜阳", "camera": f"{p_asp} 35mm"}, ensure_ascii=False)
            self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step5-inner-photo", "--inner-json", inner]).returncode, 0)
            outer = json.dumps({"layout_mode": mode, "stationery": "手工棉纸与信封", "keepsake": "一枚小纪念物", "handwriting": "深色钢笔亲笔手写", "doodles": "页角小涂鸦", "tabletop": f"自然木桌，{mode}随性摆拍"}, ensure_ascii=False)
            self.assertEqual(self.run_cli(self.eng, ["--run-dir", str(rd), "step6-compile", "--outer-json", outer]).returncode, 0)
            rv = self.run_cli(self.eng, ["--run-dir", str(rd), "verify"])
            self.assertEqual(rv.returncode, 0, rv.stdout + rv.stderr)
            ptxt = (rd / "final_prompt.txt").read_text(encoding="utf-8")
            self.assertIn(canvas, ptxt)
            self.assertIn(p_asp, ptxt)
            self.assertIn(letter, ptxt)
            self.assertIn("照片画面完整无遮挡", ptxt)
            self.assertIn("每一字清晰可读", ptxt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
