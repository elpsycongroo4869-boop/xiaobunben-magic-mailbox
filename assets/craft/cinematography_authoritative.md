# Cinematography · 灯光摄影专业知识（Space 原生静态写真适配）

2026-11-24 恢复专业知识输入。来源：[fal-ai-community/skills/skills/cinematography](https://github.com/fal-ai-community/skills/tree/main/skills/cinematography)，Copyright (c) 2026 fal.ai，MIT；本地历史副本 SKILL.md、lighting-lens-color.md、shot-language.md 和神奇信箱 15-灯光摄影美学与权限边界-v0.1.md 已真实读取。此页用于 v0.56.1 候选的灯光与摄影两岗；只复用摄影专业知识，不执行外部命令、genmedia、模型路由、视频运镜、付费API；最新制作人Point唯一权威优先于历史权限描述。

## 必须在两岗交稿前读完并使用

工具箱不是风格模板。灯光选择必须有针对该故事和人物的艺术意图，说明哪种光影、人物塑形、色彩与明暗层次让照片更美，而非仅满足物理正确。摄影选择必须有针对该故事的取景、镜头、透视、焦点、景深、视觉层次及色彩/光学表现，避免常规视角机械复用。照片主角优先，环境可裁切、虚化或由信件补足；不得裁掉必须表现的Point。每次只选适合的手段，不固定逆光、柔光、焦距、角度、光型、滤镜和构图，不强迫每张戏剧化。两岗不干涉表演、姿态、服装、事件。

## 原始灯光、镜头、色彩知识

```text
# Lighting, lens, and color reference

## Lighting setups

- Soft key: flattering, commercial, calm.
- Hard key: graphic, dramatic, fashion, noir.
- Backlight: separation, glow, silhouette, premium edge.
- Rim light: subject outline, product glass, metal highlights.
- Practical light: lamps, signs, screens, candles in the scene.
- Motivated light: light that has a visible or logical source.
- Low key: dark frame, selective highlights, suspense.
- High key: bright, low contrast, beauty, comedy, clean product work.
- Top light: interrogation, overhead realism, harsh institutional mood.
- Window light: natural, intimate, documentary.

## Lens feel

- 14-20mm wide: scale, distortion, kinetic interiors, action.
- 24-28mm wide-normal: environmental realism, travel, documentary.
- 35mm: natural cinematic perspective, street, lifestyle, narrative.
- 50mm: classic portrait and product balance.
- 85mm: compressed portrait, beauty, isolation.
- 100mm macro: product detail, jewelry, food texture, eyes.
- Telephoto compression: distance, surveillance, fashion runway.

## Depth of field

- Shallow focus: isolate subject, premium portrait, product hero.
- Deep focus: environment and blocking stay readable.
- Rack focus: attention shifts between two subjects or details.

## Color and grade

- Clean neutral grade: commercial, e-commerce, architecture.
- Warm golden grade: nostalgia, comfort, luxury hospitality.
- Cool cyan shadows: thriller, tech, night exterior.
- Desaturated earth palette: realism, documentary, survival.
- High contrast monochrome: noir, fashion, graphic product.
- Pastel palette: beauty, wellness, light lifestyle.
- Sodium vapor night: urban realism, tension.

## Texture

- Fine film grain: organic image, period mood.
- Clean digital: tech, luxury, e-commerce, architecture.
- Halation: glowing highlights, dream, night practicals.
- Mist filter: soft bloom, romance, beauty.
- Crisp high shutter: action clarity.
- Motion blur: speed, energy, handheld realism.
```

## 原始静态镜头语言与构图参考

```text
# Shot language reference

## Shot sizes

- Extreme close-up: one detail, texture, eye, hand, product edge.
- Close-up: face or object detail with emotional focus.
- Medium close-up: chest-up subject, useful for dialogue and portraits.
- Medium shot: waist-up subject, body language visible.
- Full shot: entire body or object, silhouette and stance readable.
- Wide shot: subject inside environment.
- Extreme wide: scale, isolation, worldbuilding, architecture.

## Angles

- Eye level: natural, direct, grounded.
- Low angle: power, threat, awe.
- High angle: vulnerability, surveillance, layout clarity.
- Dutch angle: unease, instability. Use sparingly.
- Over-the-shoulder: relationship, conversation, pursuit.
- POV: subjective experience.
- Profile: graphic composition, ritual, tension, fashion.


## Composition

- Centered symmetry: control, ritual, luxury, unease.
- Rule of thirds: natural editorial composition.
- Negative space: loneliness, premium ad copy area, tension.
- Foreground obstruction: secrecy, surveillance, voyeurism.
- Leading lines: architecture, movement, precision.
- Frame within frame: confinement, observation, layered space.

## Continuity language

- "same subject and wardrobe as the reference"
- "preserve product shape and label"
- "continue from the uploaded first frame"
- "single continuous shot"
- "no cutaways"
- "no time jump"
- "same lighting direction throughout"
```

## 原始提示词构成和质量要求（静态部分供参考）

```text
Use the SCLCAM structure:

1. Subject: who or what is in frame.
2. Context: location, time, weather, story moment.
3. Lens/framing: distance, angle, focal length feel, depth of field.
4. Camera motion: only for video or if motion blur is desired.
5. Atmosphere: haze, rain, practicals, reflections, texture.
6. Mood/color: palette, contrast, grade, exposure style.
7. Output controls: aspect ratio, duration, first-frame continuity.

Example structure:

```text
[subject] in [context], framed as [shot size and angle], [lens feel],
[lighting setup], [camera movement if video], [color grade], [texture],
[duration or aspect ratio], [continuity constraints]
```

Quality bar:
Before returning, check:

- Camera movement is physically plausible for the scene.

- Lens, shot size, and camera angle do not contradict each other.

- Lighting direction is clear and consistent.

- Color grade supports the mood without flattening subject detail.

- Video prompt describes one shot unless the selected model supports multiple
  prompts or shot lists.

- Downloaded files come from `downloaded_files[]`.

If a result looks generic, improve specificity in camera, blocking, light, and
environment before adding more adjectives.
```

## 神奇信箱适配：工作单必须体现实际使用

灯光导演：说明本封光影美学意图；从可信的主光、辅助光、自然反射、局部明暗、色温、光质、光比、轮廓、空气透视、材质受光中选择必要手段，交付能画出的具体光影效果，审视是否仅像普通纪实照。摄影导演：依据人物为主角与唯一Point，独立选择镜头、景别、机位距离、构图、透视、景深、焦点、曝光/快门与光学质感，说明审美理由并选择实际画面范围。最终提示词须传递各岗采纳的正面专业设计，不把知识库整页复制进去，不把不选的技法当禁止项，不用“电影感”“顶级摄影”代替实际光影构图。

原适配中的重要保留：不为收集地标缩小人物；角色是主体，世界服务她；光源方向和角色表演权限分离；透视来自相机位置，焦段与视野和机位协同；允许自然朴素的美，也允许浓烈、幽暗、戏剧光，不使用固定光型。用户最终审美验收。

## MIT 许可

Copyright (c) 2026 fal.ai. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.