# ADR-0009 · session_id 生命周期(自动重启不得切分会话)

> 日期:2026-07-10 · 状态:已接受 · 关联:ADR-0001、决策补丁开放问题 #3
> 来源:grill-with-docs 拷问 Question 9(session_id 生成时机)

## 背景

`_start_continuous_listening` 有两个调用来源:
- 用户主动开始:`_on_continuous_hotkey_start`(设 `_continuous_user_stopped=False`);
- **内部自动重启**:`_on_recognizer_error` → `QTimer.singleShot(1500, _start_continuous_listening)`,
  ASR 出错后自动重启,用户无感知。

若把 `session_id` 生成放进 `_start_continuous_listening`,一场会话中途只要 ASR 报错自动重启一次,
就会 mint 新 `session_id`,用户眼中的**一整场**会话被劈成两条记录——直接破坏方案 C 的
「按 `session_id` 聚合」。

## 决策

**`session_id` 的生成绑定「用户意图」,而非内部重启:**

- 持续模式:`session_id` **不在** `_start_continuous_listening` 生成。改为在用户主动开始时置空/待建,
  **写入第一段时惰性分配**;仅 `_stop_continuous_user_session`(用户 Esc/×)结束它。
  **自动重启不碰 `session_id`**,重启后的分段继续并入同一场会话。
- 按住说话模式:每次 `_on_recording_finished` = 一个独立 `session_id`,`seq` 从 0。
- 显式不变量:**ASR 错误自动重启不得切分会话**。

## 影响

- `App` 维护 `_current_session_id`(或等价物)+ 每会话 `seq` 计数器;由用户停止/模式语义清零。
- `seq` 在入队时(主线程、串行)递增,保证同会话顺序稳定。
- 测试(不变量):模拟「持续会话中途 ASR 报错触发自动重启」→ 重启前后的分段应落在**同一** `session_id`;
  用户 Esc 后再开始 → 新 `session_id`;按住说话每次独立 `session_id`。
