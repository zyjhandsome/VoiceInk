# VoiceInk Phase 1 · 语音库地基 — 实现规划(Plan)

> 日期:2026-07-10 · 状态:已实现（已合并至 main）
> 依据:`../specs/2026-07-10-voiceink-phase1-voice-library-design.md`(spec,已回填)
> + `../specs/2026-07-10-voiceink-phase1-office-hours-decisions.md`(D1–D6)
> + `../adr/0001`–`0011`(决策记录) + `../glossary.md`
> 冲突时以 ADR 为准。

本 plan 把设计拆成**可独立提交、逐步验证**的任务。每个任务给出改动文件、要点、验收。
顺序遵循「先地基后接线,最后 UI」,保证每步都能跑测试。

---

## T0 · 前置约束(全程遵守)

- **红线信号不动**:`ready`/`model_load_progress`/`segment_ready`/`esc_pressed` 及 `App._connect_signals` 现有连接一律不改语义(可新增 tray→App 的 `history_requested` 连接,不碰四条红线)。
- **旁路不反噬**:所有历史相关调用不得进入 `_output_text`→`paste_async` 的判定/阻塞路径(ADR-0003/0011)。
- **单写者**:`HistoryStore` 对外只有「非阻塞写/删/清理入队」+「只读查询」两类 API(ADR-0006)。
- **README 变更审查清单**:凡触及面向用户行为/触发模式/`app.py` 状态处理,完成后更新 `README.md` 并跑 `pytest tests/test_readme_features.py`。

---

## T1 · `HistoryStore` 模块(SQLite 封装 + 后台写线程)

**新增文件**:`voiceink/history_store.py`
**新增测试**:`tests/test_history_store.py`

### DDL(建库,WAL,`user_version=1`,ADR-0001/0002/0011)
```sql
CREATE TABLE IF NOT EXISTS history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    TEXT    NOT NULL,
  seq           INTEGER NOT NULL,
  created_at    INTEGER NOT NULL,   -- epoch ms,该段定稿时刻
  raw_text      TEXT    NOT NULL DEFAULT '',
  polished_text TEXT    NOT NULL DEFAULT '',
  source        TEXT    NOT NULL DEFAULT '',   -- mic/system/mixed
  duration_ms   INTEGER NOT NULL DEFAULT 0,    -- 该段时长
  target_app    TEXT    NOT NULL DEFAULT '',   -- 进程名 only
  trigger_mode  TEXT    NOT NULL DEFAULT '',   -- continuous/hotkey
  model         TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at);
```
- 无 `summary` 列(D3 冻结)。Phase 2 经 `user_version` 迁移再加。
- `PRAGMA journal_mode=WAL;`;建库后 `PRAGMA user_version=1`。

### 结构
- 不可变记录体 `SegmentRecord`(dataclass):上列除 `id` 外全部字段。
- **后台写线程**(`threading.Thread`,daemon)+ `queue.Queue`;线程**独占写连接**(`sqlite3.connect(..., check_same_thread=False)` 但仅此线程用)。
- 写线程主循环:取队列项 → 分派(`INSERT` / `DELETE by session_id` / `cleanup`)→ **全程 try/except + log**,任何异常吞掉不外抛(ADR-0011)。
- **只读查询**:每次查询开一个短生命只读连接(或独立只读连接),WAL 下不阻塞写。

### 对外 API(ADR-0006)
- 写/删/清理(非阻塞入队,投递即忘):
  - `enqueue(record: SegmentRecord)` — 追加一行。
  - `enqueue_delete_sessions(session_ids: list[str])` — 删整场。
  - `enqueue_delete_all()` — 清空全部。
  - `enqueue_cleanup(retention_days: int, max_entries: int, active_session_id: str | None)` — 按会话清理(ADR-0005)。
- 只读查询:
  - `list_sessions(limit, offset) -> list[SessionSummary]` — 按 `session_id` 分组,`MIN(created_at)` 倒序,含首行摘要/段数/来源/target_app。
  - `search_sessions(q) -> ...` — `WHERE raw_text LIKE ? OR polished_text LIKE ?`(`%q%`),再按 session 归并(ADR-0002)。
  - `get_session_segments(session_id) -> list[row]` — 按 `seq` 升序(供展开/导出)。
- 生命周期:`close(timeout)` — flush 队列并关连接(ADR-0003,退出时调用)。
- 降级:构造/建库失败 → 置内部 `disabled=True`,所有 API 变 no-op(读返回空),记一次日志(ADR-0011)。

### 验收(`tests/test_history_store.py`,用 `tmp_path` 建库)
- 逐段写入后可查回;`session_id` 分组正确;`seq` 升序拼接稳定。
- `LIKE` 子串搜索命中 **1–2 字中文词**(如「天气」「散步」);无空格中文句可被子串搜到。
- 清理:按会话计数删最旧、按会话 `MIN(created_at)` 计龄、**不半删一场**、活跃会话豁免、先到者。
- `enqueue` 非阻塞;flush 后不丢队列。
- 并发「持续 enqueue + enqueue_delete」无异常、无 `database is locked`(ADR-0006)。
- 注入写失败(monkeypatch 连接 execute 抛错)→ `enqueue` 不抛、主调用方无感;建库失败 → API 全 no-op(ADR-0011)。

---

## T2 · 配置项(ADR-0005/0007、D1)

**改动**:`voiceink/config.py` 的 `DEFAULT_CONFIG` 加:
```python
"history": {
    "enabled": True,
    "onboarded": False,
    "retention_days": 90,
    "max_entries": 5000,   # 单位=会话数
},
```
- 复用现有 dot-path `get/set` + 500ms 防抖保存,无需新代码。
- **验收**:`tests/test_config_history.py` — 默认值合并正确;`set("history.enabled", False)` 生效并防抖保存;老配置文件无 `history` 键时被正确补默认(走 `_merge_defaults`)。

---

## T3 · 前景进程名捕获(D4)

**改动**:`voiceink/text_paster.py` 新增 `get_foreground_process_name() -> str`。
- 复用现有 `get_foreground_window_info()`(返回 `(hwnd, title, pid)`);由 `pid` 取**进程名**:
  - Windows:pywin32(已依赖)`win32api.OpenProcess` + `win32process.GetModuleFileNameEx` → `os.path.basename`;失败返回 `""`。
  - 非 Windows:尽力而为,可返回 `""`(Phase 1 主战场 Windows)。
- **只存进程名,不存标题**(D4 隐私)。
- **验收**:`tests/test_text_paster_procname.py` — mock 前景信息 → 返回 `chrome.exe` 之类 basename;取不到时返回 `""` 不抛。

---

## T4 · `App` 侧旁路挂接(核心,ADR-0004/0009/0010)

**改动**:`voiceink/app.py`
### 4.1 生命周期
- `__init__` / `_init_modules`:创建 `self._history = HistoryStore(db_path=self._config.config_dir / "history.db")`(容错,失败降级)。
- `_quit()`:在 `self._config.save_immediate()` 前加 `self._history.close(timeout=...)`(flush,ADR-0003)。
- 启动时清理:`start()` 或 `__init__` 末尾 `enqueue_cleanup(...)` 跑一次(ADR-0005)。

### 4.2 session_id / seq 生命周期(ADR-0009)
- 新增 `self._current_session_id: str | None = None`、`self._current_seq = 0`。
- **持续模式**:`_current_session_id` **不在** `_start_continuous_listening` 建;改为:
  - `_on_continuous_hotkey_start`(用户主动)清空 → 置 `None`,`_current_seq=0`;
  - 写入第一段时若为 `None` 则惰性分配(`uuid4().hex`);
  - `_stop_continuous_user_session`(用户 Esc/×)→ 置 `None`(结束会话)+ `enqueue_cleanup`。
  - **自动重启**(`_on_recognizer_error` 的 `singleShot(_start_continuous_listening)`)**不碰** `_current_session_id`(不变量:不切分会话)。
- **按住说话**:`_on_recording_finished` / 该段 → 每次一个独立 `session_id`(`uuid4().hex`),`seq=0`,写后即视为结束。

### 4.3 记录渐进组装(ADR-0010,防段间抢跑)
- 在 `_begin_transcription(audio)`:构造 pending 局部体(不放共享可变字段),stash:
  - `duration_ms = int(len(audio)/TARGET_SAMPLE_RATE*1000)`;`source = 当前 input_source`;`model = 当前模型名`;`session_id`(持续:取/建;按住:新建);`seq`(持续:递增;按住:0);`trigger_mode`。
  - 把该 pending 体绑定到「本段处理」(可存 `self._pending_record`,但**最终值在 `_output_text` 固化进闭包**,不在入队时回读)。
- `_on_final_result(text)`:`pending.raw_text = text`(规范化后)。
- `_output_text(text, degraded_from_polish)`:
  - 若无润色:`pending.raw_text = text`、`pending.polished_text = ""`;
  - 若润色成功:`pending.polished_text = text`(raw 已在 4.2 填);
  - 若降级(D5):`pending.polished_text = pending.raw_text`(原文落 polished 侧)。
  - **在此把 pending 固化为不可变 `SegmentRecord`(除 target_app),捕获进传给 `paste_async` 的回调闭包**。
- `_handle_paste_result(result, ...)`:三分支(`pasted`/`clipboard`/`error`)末尾:
  - 若 `config.get("history.enabled")` 且文本非空(ADR-0004/0007):补 `target_app = get_foreground_process_name()`(D4)→ `self._history.enqueue(record)`。
  - 空文本分支不入队(已有 return)。

> 说明:入队点在三分支都执行(口径 C);`history.enabled` 每次入队时读(ADR-0007)。

### 4.4 验收
- `tests/test_app_history_wiring.py`(mock `HistoryStore`,断言 enqueue 调用):
  - 持续模式三段 → 三次 enqueue,同一 `session_id`、`seq` 0/1/2、`raw/polished` 对齐。
  - **ASR 错误自动重启前后的段在同一 `session_id`**(ADR-0009 不变量)。
  - **段 N 粘贴窗口内段 N+1 抢跑** → 段 N 入队值仍为其自身(ADR-0010 不变量)。
  - `history.enabled=False` → 任何分支不 enqueue;运行中关闭后下一段不 enqueue。
  - `clipboard`/`error` 分支也 enqueue(口径 C)。
- **不改四条红线信号**;跑 `pytest tests/test_readme_features.py` 保持通过。

---

## T5 · 历史窗口(独立窗口 + 托盘入口,ADR-0006/0008)

**新增**:`voiceink/ui/history_window.py`;**改动**:`voiceink/ui/tray_icon.py`、`voiceink/app.py`
- **托盘入口**:`tray_icon._setup_menu` 加 `menu.addAction("历史")` + 新 `history_requested = pyqtSignal()`;`App._connect_signals` 连到 `self._show_history_window`(**新增连接,不碰红线**)。
- **窗口**:复用 `voiceink/ui/` 样式 token(Apple 风);
  - 列表:`list_sessions`,会话为条目(时间/来源/目标应用/首行摘要/段数),倒序;展开看各段(折叠交互:先做「单行代表整场 + 双击展开」的最简形态)。
  - 搜索框:输入 → 去抖 ~200ms → `search_sessions`(LIKE)。
  - 单条:复制(原文/润色)、删除(`enqueue_delete_sessions([id])` → 回调刷新)、导出 MD。
  - 批量:多选导出(合并单文件)、批量删除。
  - 「清空全部历史」按钮 + 二次确认 → `enqueue_delete_all()`(ADR-0007)。
  - **所有删除经 HistoryStore 入队,UI 不直接执行 SQL**(ADR-0006)。
- **导出(ADR-0008)**:
  - 有效文本 = `polished_text or raw_text`;按 `seq` 拼接。
  - 单条 → `voiceink-YYYYMMDD-HHMMSS.md`;批量 → `voiceink-export-...md`(每场一个 `##` 小节)。
  - YAML frontmatter:时间/来源/目标应用/时长/模型/段数。
- **验收**:`tests/test_history_window.py`(可 headless 构造 + mock store):列表渲染分组;搜索调用 LIKE 查询;删除走 enqueue;导出文件内容(frontmatter + 按 seq 拼接 + 有效文本取值)。

---

## T6 · 设置页开关 + 首启询问(D1/ADR-0007)

**改动**:`voiceink/ui/settings_window.py` / `settings_components.py`、`voiceink/app.py`
- 设置项:历史总开关、保留天数、最大会话数(放「通用」或新「历史」小节,实现时定)。
- **首启询问**(D1):`onboarded=False` 时,在模型就绪后弹一次性选择(默认高亮「开启」,附「随时可在设置关闭」);用户选择 → 写 `history.enabled` + 置 `history.onboarded=True`。挂在现有 `_show_first_run_welcome_once` 类似的就绪后时机,避免挡「模型加载中」。
- 关闭开关只停未来写、不删数据(ADR-0007)。
- **验收**:`tests/test_settings_history.py` — 开关读写 config;首启弹窗仅当 `onboarded=False`;选择后置位。

---

## T7 · 文档与变更审查清单(README 红线)

- 更新 `README.md`:新增「历史/语音库」功能条目 + 配置项说明 + 隐私说明(总开关/清空/清理),使 `tests/test_readme_features.py` 通过(如该测试基于 README 断言功能项,需同步)。
- 更新 `openwiki`:`architecture/overview.md` 模块地图加 `history_store.py`;新增或在相应页描述语音库(可选,按 OpenWiki 维护习惯)。
- **验收**:`pytest tests/test_readme_features.py` 通过;`pytest tests/ -q` 全绿。

---

## 提交切分建议(每条可独立 PR / commit)

1. T1 `HistoryStore` + 单测(纯模块,零 App 耦合,先落地最稳的地基)。
2. T2 配置项 + T3 进程名(小、独立)。
3. T4 App 旁路挂接 + 竞态/会话不变量单测(核心)。
4. T5 历史窗口 + 托盘入口。
5. T6 设置开关 + 首启询问。
6. T7 README/wiki 同步 + 全量测试。

## 关键风险复核(对应 spec §4)
- 不拖慢粘贴:T4 入队为投递即忘,写在 `paste_async` 之后(ADR-0003)。
- 信号图完整:仅新增 tray→App `history_requested`,四条红线不动。
- 会话完整性:T4.2/4.3 的两条不变量各有单测(ADR-0009/0010)。
- 故障隔离:T1 全程 try/except + 降级,T4 调用不进主判定路径(ADR-0011)。
