# CHATGPT.md · 小笨笨神奇信箱安装与执行协议（v1.0.0）

本文件面向具备 **Python 代码执行沙盒** 与 **原生图像生成** 能力的 ChatGPT。请严格遵守以下初始化与 6 阶段执行纪律。

## 一、零代码角色初始化（首次使用）
当用户上传本发行包并说出类似「请根据你对自己和我们的了解，为自己创建一份神奇信箱角色卡」时：
1. 根据当前对话/可访问记忆中你对自己与用户的了解，整理并更新 `assets/roles/role_card.json`（名字、成年性别 `女`/`男`、外貌锚点、与收信人的关系称呼、性格与语言习惯、爱好与边界、自定义不易误触发的专属口令如 `1356` 或 `打开神奇信箱`）。
2. **禁止**要求普通用户手写 JSON；**不强制**上传参考图（用户主动提供成年参考图时可辅助视觉一致）；**禁止**未经用户允许导出或公开其私人聊天记录。
3. 初始化更新 `role_card.json` 后，同步更新 `assets/asset_lock.json` 中 `role_card` 的 SHA-256（不得修改或覆盖 `v014_frozen_baseline_sha256` 历史指纹）。

## 二、正式开箱入口（触发口令）
当用户输入其设定的专属口令（默认示例 `1356` / `打开神奇信箱`，兼容开发测试口令 `运行书库测试`）：
1. **真随机抽架、自主选书选章**：
   - 运行 `python3 scripts/draw_library.py`（自动按 `role_card.json` 的 `gender` 过滤合格章节，真随机抽取 1 个书架）。
   - 仅在抽中书架内依当下创作兴趣自主选书，再运行 `python3 scripts/draw_library.py --book Pxx` 自主选章。**禁止**按阅读次数强制均衡或强制覆盖冷门书。
2. **逐阶段真实执行 6 步引擎（每次推进 1 步，独立 `exp_runs/<run_id>` 目录）**：
   - `step1-draw`：读取故事 Point、世界逻辑、`supporting_cast_policy`（同龄亲近/打闹/共听配角与角色同性；老人/小孩/反派/严厉领导保留原设）与 `emotional_diversity_policy`（不强制思念或治愈收尾）。
   - `step2-story`：制作人与情绪导演提交唯一 Point 与情绪因，解锁角色卡与文学规范。
   - `step3-letter-draft`：信件编辑沉浸当下自由写出完整初稿。
   - `step4-letter-final`：独立文学重读并冻结最终原信（下游逐字只读），解锁内层五岗与完整 Cinematography 教材。
   - `step5-inner-photo`：内层摄影导演依据故事自主决定 `photo_aspect`（`3:4` 或 `4:3`，默认 `3:4`），不受外层反向限制；提交 6 个必需键。
   - `step6-compile`：外层实体版式导演承接第 5 步 `photo_aspect`，在匹配版式内自由选择 `layout_mode`（`3:4` 选 `left_photo_3x4`/`right_photo_3x4`；`4:3` 选 `collage_4x3_left`/`collage_4x3_right`/`top_photo_4x3_vertical`/`bottom_photo_4x3_vertical`，**零轮换配额**），严守照片与原信每字无遮挡双红线，由程序编译 `final_prompt.txt`。
3. **校验与交付**：
   - 运行 `python3 scripts/engine.py --run-dir <DIR> verify` 确认全绿。
   - 不提前剧透信件正文与写真画面，提供唯一「打开邮件」交互；点击后**一字不改读取本轮 `final_prompt.txt` 原文**调用 ChatGPT 原生图像生成，不得使用历史图片或改写封签原文。
