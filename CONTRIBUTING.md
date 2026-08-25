# Contributing / 贡献指南

AI Tutor V0.1 is local-first and keeps its domain engine deterministic and model-independent. / AI Tutor V0.1 坚持本地优先，并保持领域引擎可确定计算且不绑定模型。

## Development / 开发

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -v
```

## Guidelines / 原则

- Put domain rules in the engine, not dashboard JavaScript or prompts.
- Validate model output before persistence.
- Preserve stable concept IDs and learner history during expansion.
- Keep Blueprint, objective graph, learner mastery, and Roadmap distinct.
- Persist through `TutorService` and `JsonRepository`, never direct JSON edits.
- Add tests and update both README languages when public behavior changes.
- Never commit `data/`, credentials, local absolute paths, or personal examples.

- 领域规则应进入引擎，而不是看板 JavaScript 或 Prompt。
- 大模型输出持久化前必须校验。
- 扩图时保持 ID 稳定并保留学习历史。
- 区分 Blueprint、客观知识图、学习者掌握度和派生 Roadmap。
- 通过服务层持久化，不直接编辑 JSON。
- 行为变化应补测试，公共用法变化应同步更新中英文 README。
- 不得提交学习数据、凭据、本机路径或个人示例。

## Validation / 验证

```bash
python -m unittest discover -v
ai-tutor doctor
git diff --check
```

Manual cases are documented in [the smoke-test guide](docs/smoke-test-cases.md).

## Compatibility and license / 兼容性与许可证

Stored schemas and CLI JSON are compatibility surfaces. Add migration or backward-compatible loading when they change. By contributing, you agree that your contributions are licensed under the repository's [Apache License 2.0](LICENSE).

持久化 Schema 和 CLI JSON 属于兼容性边界，变化时应提供迁移或向后兼容读取。提交贡献即表示同意按照仓库的 [Apache License 2.0](LICENSE) 授权该贡献。
