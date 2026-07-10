# ADR-0001 · 语音库写入模型与记录字段语义

> 日期:2026-07-10 · 状态:已接受 · 关联:spec §3.2/§3.3、决策补丁 D2/D4/D5
> 来源:grill-with-docs 拷问 Question 1(会话定稿生命周期)

## 背景

Phase 1 要把每次转写沉淀进本地库。持续模式下每个 VAD segment 独立走完
`segment_ready → _on_final_result → [润色 QThread] → _output_text → paste_async`,
且末段常在 Esc(`esc_pressed`)**之后**才回来。因此「一次会话如何落库」直接决定
是否会出现竞态、崩溃丢数据、以及时长/时间字段的语义。

## 决策

### 1. 写入模型:方案 C —— 逐段即时写行 + `session_id` 分组

- 每个 segment 在 `_output_text` 粘贴成功后**各写一行**(原子 INSERT),带 `session_id` + `seq`。
- 会话聚合放在**查询层**(`GROUP BY session_id`),不维护可变的「当前会话行」。
- **迟到分段**(Esc 之后回来的段)只是再 INSERT 一行(同 `session_id`、下一 `seq`),
  无需软关闭 / 时长回填 / 竞态处理。
- 按住说话:每次松开 = 一个独立 `session_id`,天然单行。

**否决的备选**
- 方案 A(单行 + 增量 UPDATE + 迟到分段软关闭并入):需维护可变行、软关闭、时长回填,复杂且脆。
- spec 3.3 原案(内存 buffer,会话结束定稿写一条):有 stop/末段竞态,且中途崩溃丢整场数据。

### 2. 崩溃持久性

- 逐段原子写入 ⇒ 已产出的段都在库里;崩溃最多丢「最后一个尚未产出的段」。此风险**可接受**。

### 3. 字段语义

- **`duration_ms`**:按**每段时长**存(行 = 该 segment 录音时长)。整场会话时长**不入库**,
  需要时查询层用该 `session_id` 下派生(如 `MAX(created_at) - MIN(created_at)` 或末段 end − 首段 start)。
- **`created_at`**:= 该段**定稿时刻**。历史列表按会话排序时,一场会话取该 `session_id` 下的
  **`MIN(created_at)`**(首段出字时刻);按住说话单行时 `MIN` 退化为自身。
- **`session_id` / `seq`**:见上;`seq` 保证同 session 内拼接/导出顺序稳定。
- **`target_app`**:前景进程名 only(D4)。
- **`raw_text` / `polished_text`**:逐段对齐,降级段的原文也落 polished 侧(D5)。

## 影响

- 对 spec §3.2 数据模型:新增 `session_id`、`seq`;`duration_ms` 语义收紧为段级;`summary` 冻结(D3)。
- 对实现:`HistoryStore` 接口以「写一行 segment」为核心,不是「维护会话状态」。
- 对测试:需覆盖逐段写入原子性、`GROUP BY session_id` 聚合、迟到分段并入。
