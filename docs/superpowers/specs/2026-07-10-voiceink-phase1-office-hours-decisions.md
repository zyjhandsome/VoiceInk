# VoiceInk Phase 1 语音库地基 — Office Hours 压测与设计决策

> 日期:2026-07-10
> 模式:Builder(开源 / 个人作品 / 自用)
> 关联:`2026-07-10-voiceink-phase1-voice-library-design.md`(原始 spec)
> 状态:方向已压测,进入实现规划(plan)前的设计基线补丁。

本文件记录对原 spec 的一次 YC Office Hours 式压测结论,只覆盖被修正/被确认的点,不重复原 spec。原 spec 仍是主设计文档,本文件是它的**决策补丁**。

## 1. 结论速览

原 spec 质量高、边界克制。核心约束("零破坏 + 旁路挂接")经代码核对成立:出字路径 `_on_final_result` → (润色/直出) → `_output_text` → `paste_async`,入库挂在 `_output_text` 成功之后异步执行,不碰四条红线信号。以下是压测后被**修正或收紧**的决策。

## 2. 被修正的设计决策

### D1 · 历史开关:默认开 → 首次启动一次性询问

- **变更**:不再"默认开且藏在设置里"。首次启动弹一次性选择(默认高亮「开启」,附「随时可在设置关闭」)。
- **理由**:slogan 是「本地隐私」的工具静默记录用户粘贴过的一切,是心智违背。首启询问代价近零,口碑更稳。
- **落地**:`config` 新增 `history.enabled`(默认 `true`)+ `history.onboarded`(默认 `false`)。`onboarded=false` 时首启弹窗,用户选择后置 `true`。

### D2 · 写入模型:采用「逐段即时写行 + session_id 分组」(方案 C)

- **变更**:放弃 spec 3.3 的「内存维护当前会话 buffer,会话结束定稿写一条」。改为每个 segment 落库时**立即写一行**,带 `session_id`;历史窗口按 `session_id` 分组展示 / 拼接 / 导出。
- **理由**:持续模式下每段独立走完识别/润色/粘贴,且 README 与 `app.py:388` 明确「最后一段在 stop 之后才回来」。方案 B 需处理 stop 与末段回来的竞态,以及会话中途崩溃丢数据。方案 C 写入原子、崩溃安全、无竞态,聚合体验通过查询层 `GROUP BY session_id` 达成,FTS5 仍按行索引不受影响。
- **落地要点**:
  - 数据模型新增 `session_id`(持续模式一场一个 id;按住说话每次一个独立 id,天然单行)。
  - 新增 `seq`(段内序号)保证同一 session 内拼接顺序稳定。
  - 历史窗口列表以 session 为一个条目(展示该 session 首行摘要 + 段数),展开看各段;导出按 `seq` 拼接 `raw_text` / `polished_text`。

### D3 · 按需摘要:整体推迟到 Phase 2

- **变更**:Phase 1 **不做**「按需单条摘要」。删除 spec 3.4 的摘要按钮与 3.2 的 `summary` 字段(或保留列但 Phase 1 不写)。
- **理由**:口述单条本就短,云摘要价值有限;它是 Phase 1 里**唯一**需要联网 / API key / 错误降级 / 禁用态的功能点,复杂度与使用频率不匹配。移除后 Phase 1 **完全无网络依赖**,更纯、更快 ship。Phase 2 本地小模型让摘要免费又私密,是它的正确归宿。
- **备选**:若确要先试云摘要手感,可保留,但明确定位为「手感试验」而非核心价值,且不得阻塞 Phase 1 交付。

## 3. 被确认 + 收紧的决策

### D4 · target_app:存,但收紧口径

- 确认值得存。**收紧**:
  1. 在 `_handle_paste_result` 那一刻捕获前景进程名并透传给 `HistoryStore`,**不**在异步写库时再查(那时前景窗口可能已切走)。`text_paster.py:57 get_foreground_window_info()` 已能拿到 (hwnd, title, pid)。
  2. **只存进程名**(如 `chrome.exe`),不存窗口标题——标题常含隐私内容(邮件主题、文档名)。

### D5 · polished_text 分段对齐

- 持续模式下 `polished_text` 是各段润色结果的拼接。降级为原文的段(`_on_polish_error` 路径)也要正确落到 polished 侧,保证 raw / polished 逐段对齐,否则搜索命中与导出错位。

### D6 · Phase 1 范围维持不变

- 沉淀 + 回看 + 搜索 + 导出,不碰即时召回 / 语义搜索 / 会议界面。
- 记录:真正的「whoa」是**全局快捷键秒搜历史**——这是 Phase 2 的第一发子弹,不进 Phase 1。

## 4. 修正后的数据模型(相对 spec 3.2 的差异)

在 spec 字段基础上:
- **新增** `session_id`、`seq`(见 D2)。
- **移除 / 冻结** `summary`(见 D3)。
- **收紧** `target_app` 语义为「进程名 only」(见 D4)。
- FTS5 仍建在 `raw_text` + `polished_text`,按行索引。

## 5. 实现规划阶段要回答的开放问题

1. 首启询问弹窗放在现有哪个 UI 组件里触发(启动流程 vs 托盘首启)。
2. 历史窗口的 session 分组列表 UI:折叠/展开 or 单行代表整场。
3. `session_id` 生成时机:在 `_on_continuous_hotkey_start` / `_start_continuous_listening` 建立,`_stop_continuous_user_session` 关闭(但不依赖它来触发写入)。
4. 自动清理(保留天数 / 最大条数)按 session 计数还是按行计数——建议按 session 条目计数更符用户直觉。

## 6. 不变的红线(来自 README / OpenWiki)

- 不新增 / 不改动四条核心信号(`ready`、`model_load_progress`、`segment_ready`、`esc_pressed`)。
- 入库只在既有处理槽旁路挂接,不进主输出链路,不拖慢粘贴。
- 遵守 README 变更审查清单,同步更新 README,通过 `tests/test_readme_features.py`。
- `HistoryStore` 单测:写入、session 分组聚合、FTS 搜索、自动清理、总开关关闭时不入库、崩溃安全(段写入原子性)。

---

## The Assignment(下一步具体动作)

在写任何 `HistoryStore` 代码之前,做这一件事——它会验证方案 C 的核心假设:

**用 20 行脚本量一次你真实的持续会话竞态窗口。** 在 `_output_text` 成功分支和 `_stop_continuous_user_session` 里各打一条带时间戳的日志,然后自己录一段"说三句、停顿、按 Esc"的持续会话,看最后一段的 `_output_text` 到底落在 Esc **之前还是之后**、差多少毫秒。

- 如果末段总是在 Esc 之后回来 → 印证方案 C 的必要性(逐段写行是对的)。
- 顺便确认 `_handle_paste_result` 那一刻抓到的前景进程名是否就是你期望的目标应用(验证 D4 的透传时机)。

拿到这两个真实观测,再进 plan 阶段设计 `HistoryStore` 接口,你就不是在猜竞态,而是在照着数据设计。
