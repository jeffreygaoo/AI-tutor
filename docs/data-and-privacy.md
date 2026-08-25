# Data and privacy / 数据与隐私

AI Tutor V0.1 is local-first and sends no data to a model provider by itself. Content passed to an external model or a future provider adapter remains governed by that provider's settings and policies.

AI Tutor V0.1 本身不会主动把数据发送给模型 Provider；传给外部模型或未来适配层的内容仍受对应 Provider 的设置和政策约束。

## Stored data / 存储内容

`data/` may contain Subject graphs, Blueprint goals, mastery, confidence, misconceptions, review dates, quizzes, answers, assessed attempts, session history, backups, and reset/delete archives. `data/` is ignored by Git, but important data should be backed up separately.

`data/` 可能包含知识图、学习目标、掌握度、误区、复习日期、题目、回答、评估、会话历史、备份和归档。它已被 Git 忽略，但重要数据仍应单独备份。

## Publication checklist / 发布检查

1. Confirm `data/` remains ignored and untracked.
2. Inspect `git status` and every new JSON, Markdown, log, screenshot, and fixture.
3. Remove usernames, home paths, emails, phone numbers, tokens, and credentials.
4. Use `<project-root>`, `<data-dir>`, and `${CODEX_HOME}` placeholders.
5. Remember screenshots may reveal browser profiles, paths, goals, or accounts.

公开前应确认 `data/` 未被跟踪，逐项检查新文件，并用通用占位符替代个人信息。本地截图同样可能泄露隐私。

## Backups and deletion / 备份与删除

Normal overwrites keep `.bak`; reset and deletion first move affected files into `data/archive/`. This is recoverable deletion, not secure erasure. Permanent erasure requires separately handling backups and archives after verifying exact targets; V0.1 does not automate it.

普通覆盖保留 `.bak`，重置和删除前会把文件移入 `data/archive/`。这属于可恢复删除，并非安全擦除；V0.1 不自动执行永久清理。

## Operational safety / 运行安全

- Keep the dashboard on `127.0.0.1`; V0.1 has no authentication.
- Avoid concurrent writers against one JSON data directory.
- Back up learning data before upgrades.
- Keep model API keys in a secret store or environment, never tracked files.

- 看板应监听 `127.0.0.1`，不要直接暴露到公网。
- 避免多个进程并发写同一 JSON 目录。
- 升级前备份学习数据。
- API Key 应放在密钥系统或环境中，不得进入被跟踪文件。
