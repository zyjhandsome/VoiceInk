# ADR-0010 · 记录渐进组装与段间竞态安全

> 日期:2026-07-10 · 状态:已接受 · 关联:ADR-0001、ADR-0004、ADR-0009
> 来源:grill-with-docs 拷问 Question 10(记录组装方式)

## 背景

`_output_text` 在调用异步 `paste_async` **之前**就置 `_is_transcribing = False`(app.py:591)。
持续模式下,段 N 处于「粘贴窗口」期间,若用户仍在说话、`AudioRecorder` 发来段 N+1 的
`segment_ready`,`_on_segment_ready` 见 `_is_transcribing==False` 会**立即** `_begin_transcription(N+1)`,
`_on_final_result` 覆盖 `_current_transcription`。若段 N 的 `_handle_paste_result` 入队时**回读 App 共享变量**,
读到的将是 N+1 的原文 —— 数据张冠李戴。

## 决策

1. **记录逐槽渐进组装成不可变对象,通过粘贴回调闭包携带,绝不在入队那一刻回读 App 可变状态:**
   - `_begin_transcription`(有 audio、串行):stash `duration_ms`、`source`、`model`,确保/取 `session_id`+`seq`;
   - `_on_final_result`:填 `raw_text`;
   - `_output_text`:填 `polished_text`(无润色/降级按 D5)、`degraded` 标志,并**在此把整条记录固化进
     传给 `paste_async` 的回调闭包**;
   - `_handle_paste_result`:只补 `target_app`(D4)+ 结果分支,然后 `enqueue`。
2. **`duration_ms` 来源**:`_begin_transcription` 用 `len(audio) / TARGET_SAMPLE_RATE * 1000`(16kHz 单声道)计算,
   下游不再找 audio。
3. 显式不变量:**持续模式段间抢跑不得污染任一已固化记录**。

## 影响

- 入队前的记录是闭包内的局部不可变体,不依赖 `_current_transcription` 等共享字段的当下值。
- 不新增/不改动四条红线信号;只在既有槽内读状态 + 组装 + 入队。
- 测试(竞态不变量):模拟段 N 粘贴窗口内段 N+1 抢跑 → 段 N 入队的 `raw_text`/`polished_text`/`duration_ms`
  仍为段 N 自身值;逐段 raw/polished 对齐(D5)。
