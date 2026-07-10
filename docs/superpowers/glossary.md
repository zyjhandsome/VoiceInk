# VoiceInk Phase 1 · 术语表(Ubiquitous Language)

> 通过 grill-with-docs 拷问逐步沉淀的领域词汇。代码标识符保持英文,解释用中文。
> 关联:`specs/2026-07-10-voiceink-phase1-voice-library-design.md`(spec)、`specs/2026-07-10-voiceink-phase1-office-hours-decisions.md`(决策补丁)、`adr/`(决策记录)。

| 术语 | 定义 | 备注 |
|------|------|------|
| **segment(分段)** | 持续模式下由 VAD(`SpeechSegmenter`)按停顿切出的一段语音,经 ASR(可选润色)后产出一段文本。是写入库的**最小原子单位**。 | 停顿阈值 `SILENCE_HOLD_SEC=0.85s`。 |
| **session(会话)** | 一次连续的语音输入活动。持续模式:从按住热键开始监听到 Esc/× 结束,聚合为一个 `session_id`(含多个 segment 行)。按住说话:每次松开 = 一个独立 `session_id`,天然单行。 | 聚合发生在**查询层**,不是单条记录。 |
| **session_id** | 标识一场会话的 id,同一会话内所有 segment 行共享。持续模式在会话开始建立。 | 见 ADR-0001 / 决策补丁 D2。 |
| **seq** | 同一 `session_id` 内 segment 的序号,保证拼接/导出顺序稳定。 | 从 0 或 1 递增(实现规划阶段定)。 |
| **迟到分段(late segment)** | Esc 之后才走到 `_output_text` 的 segment(ASR/润色回调晚到)。在方案 C 下它只是再 INSERT 一行(同 `session_id`、下一 `seq`),无需特殊处理。 | 方案 C 消解了方案 A 的软关闭/竞态问题。 |
| **方案 C(逐段即时写行)** | 每个 segment 产出后各写一行(原子 INSERT),带 `session_id`+`seq`;会话聚合在查询层 `GROUP BY session_id`。 | 取代 spec 3.3 的「内存 buffer + 会话结束定稿」。 |
| **入库旁路(passive sink)** | 写库挂在既有出字槽(`_output_text` 粘贴成功后)异步执行,不进主输出链路、不碰四条红线信号。 | README 红线。 |
| **raw_text** | 该 segment 的原始 ASR 文本(规范化后)。 | 搜索用 `LIKE` 扫描字段之一(ADR-0002)。 |
| **polished_text** | 该 segment 的润色后文本;未开润色为空;润色失败降级为原文的段,原文也要落到 polished 侧以保持逐段对齐(D5)。 | 搜索用 `LIKE` 扫描字段之一(ADR-0002)。 |
| **搜索(LIKE 扫描)** | Phase 1 用 `LIKE '%q%'` 全表扫描 `raw_text`/`polished_text`,放弃 FTS5。中文双字词也能命中;≤5000 行毫秒级。 | ADR-0002。 |
| **target_app** | 该段粘贴目标的前景**进程名**(如 `chrome.exe`),在 `_handle_paste_result` 那一刻捕获透传,**不存窗口标题**(隐私)。 | 决策补丁 D4。 |
| **历史总开关** | `history.enabled`;首次启动一次性询问(`history.onboarded`)。每次入队时读取,一关下一段即停;只停未来写入,已有历史保留。 | D1 / ADR-0007。 |
| **单写者原则** | 所有写(INSERT/清理/UI 删除)串行经唯一后台写线程;只有读用独立只读连接。杜绝写-写撞锁。 | ADR-0006。 |
| **有效文本(effective text)** | 导出/摘要口径:有润色用 `polished_text`,否则 `raw_text`——即用户实际拿到的那份。 | ADR-0008。 |
| **清空全部历史** | 与总开关解耦的显式动作(带二次确认),经写线程执行。 | ADR-0007。 |
