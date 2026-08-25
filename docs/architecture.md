# Architecture and model integration / 架构与模型接入

## Runtime shape / 运行形态

AI Tutor V0.1 is a single local Python application with three interfaces: the `ai-tutor` CLI, a local HTTP dashboard, and the model-facing Skill. Plain HTML/CSS/JavaScript and JSON APIs are served by the same Python process. It is separated by responsibility, but not deployed as independent frontend and backend services.

AI Tutor V0.1 是一个本地 Python 应用，对外提供 CLI、本地 HTTP 看板和面向大模型的 Skill。原生 HTML/CSS/JavaScript 与 JSON API 由同一 Python 进程提供，因此职责上前后端分层，但并非两个独立部署的服务。

```text
CLI ───────────────┐
Dashboard API ─────┼──> TutorService ──> Graph / Mastery / Planner
Skill + LLM ───────┘                         |
                                             v
                                      JsonRepository → data/
```

## Source of truth / 状态真相源

`TutorService` is the application boundary. Graph validation, prerequisite unlocking, mastery updates, hierarchy aggregation, review scheduling, and roadmap selection are deterministic engine responsibilities. `JsonRepository` persists their results atomically.

`TutorService` 是应用边界。图校验、前置解锁、掌握度更新、层级聚合、复习调度和 Roadmap 选择均由确定性引擎负责，结果通过 `JsonRepository` 原子持久化。

The model may propose a Blueprint, concepts, lessons, quizzes, and rubric-based assessments. It must not become an alternative state store or directly mutate persisted JSON. 大模型可以提出教学内容和结构化评估，但不能成为另一套状态存储。

## Core objects / 核心对象

- **Blueprint**：目标边界、粗粒度全景、核心骨架和可选进阶方向。
- **Knowledge graph**：客观知识点、层级、前置依赖、学习目标和评估要求。
- **Mastery graph**：学习者证据、置信度、误区、状态和复习计划。
- **Roadmap (MVLG)**：根据目标、知识图和当前掌握度计算的个性化派生视图。
- **Expansion**：在 anchor 下添加有限批次子节点，不会替换 Blueprint。

## Dynamic roadmap / 动态路线

Completing a child can change parent mastery, unlock downstream concepts, promote remediation, and change the next Roadmap calculation. History remains intact. Regenerate the Blueprint only when the goal or scope materially changes.

完成子知识点可能改变父主题掌握度、解锁后续节点或触发补救，从而影响下一次 Roadmap；已有历史不会丢失。只有目标或范围发生实质变化时才应重新生成 Blueprint。

## Other models / 其他模型

Codex is optional. A DeepSeek or other provider adapter should provide the Skill constraints and current state, validate structured Blueprint/Expansion/Quiz/Assessment output, submit it through `TutorService` or CLI, and return validation errors for correction. Credentials must remain outside the repository and learning data. V0.1 contains no provider SDK, network client, authentication, or secret-management layer.

Codex 并非必需。接入其他模型时应在领域引擎外增加适配层，并始终由引擎校验和持久化。V0.1 暂不包含 Provider SDK、网络客户端、认证或密钥管理层。
