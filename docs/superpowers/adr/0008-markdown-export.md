# ADR-0008 · Markdown 导出形态

> 日期:2026-07-10 · 状态:已接受 · 关联:spec §3.4、决策补丁开放问题 #2
> 来源:grill-with-docs 拷问 Question 8(导出形态)

## 决策

1. **导出内容 = 有效文本**:有润色则用 `polished_text`,否则用 `raw_text`(用户实际拿到的那份)。
   不默认双份并排。可选「同时保留原文」开关留待未来,Phase 1 不做。
2. **组织方式**:
   - **单条导出** → 一个 `.md`:该会话各段按 `seq` 拼成正文,顶部 YAML frontmatter 元数据头。
   - **批量导出** → **一个合并 `.md`**,每场会话为一个 `##` 小节,按会话时间排序(不导出成碎文件)。
3. **文件名 / 元数据头**:
   - 单条:`voiceink-YYYYMMDD-HHMMSS.md`(取会话 `MIN(created_at)`)。
   - 批量:`voiceink-export-YYYYMMDD-HHMMSS.md`。
   - 元数据头 YAML frontmatter(时间/来源/目标应用/时长/模型/段数),为 Phase 2 导入 Obsidian/Notion 铺路。

## 影响

- 导出是只读操作(SELECT + 拼装),用只读连接(ADR-0006)。
- 拼装顺序严格按 `session_id` 分组、`seq` 升序。
- 测试:单条拼段顺序正确、批量多会话分节、frontmatter 字段齐全、有效文本取值(有/无润色)。
