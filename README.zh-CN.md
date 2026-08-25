# AI Tutor

简体中文 | [English](README.md)

AI Tutor V0.1 是一个本地优先、受学习目标约束的个性化学习引擎。它将客观知识图谱与学习者掌握度、前置解锁、动态路线、测验、错误认知、学习会话和间隔复习组合成一个可持久化的学习闭环。

Python 引擎采用确定性计算，不绑定特定大模型。Codex 可以通过项目附带的 `ai-tutor` Skill 组织教学和语义评估，但 CLI、学习看板、Roadmap 以及学习状态持久化均可脱离 Codex 和在线模型独立运行。

> V0.1 面向单机、单用户场景，使用本地 JSON 保存数据，不需要数据库，也不需要单独部署前端服务。

## 核心能力

- 目标约束的 Subject Blueprint 和粗粒度领域全景。
- 由引擎选择的最小可行学习图（MVLG）。
- 根据前置依赖、目标相关性和掌握度动态计算 Roadmap。
- 将粗粒度主题渐进展开为可教学、可评估的子知识点。
- 根据必修子节点聚合父主题掌握度。
- 可解释的下一知识点推荐与确定性解锁。
- Diagnostic、Learning、Review 三类结构化测验。
- 错误认知跟踪与 1/3/7/14/30 天间隔复习。
- 学习会话、测验尝试、进度和历史持久化。
- 支持多主题切换和递归下钻的中文本地看板。
- 需要精确确认的进度重置和主题删除，并保留可恢复归档。
- 带 Schema 版本、原子写入和上一版本备份的 JSON 存储。

## 工作原理

```text
大模型 / 人工 / CLI
        |
        v
   TutorService
  /     |       \
知识图  掌握度图  路线规划
  \     |       /
   JsonRepository
        |
      data/
```

看板前端使用原生 HTML、CSS 和 JavaScript。静态资源与 JSON API 由同一个 Python 进程提供，因此项目在代码上前后端分层，但部署时不是两个独立应用。

## 环境要求

- Python 3.11 或更高版本
- 用于本地看板的现代浏览器
- 仅在使用附带 Skill 工作流时需要 Codex

运行时代码只依赖 Python 标准库；构建和安装使用 `setuptools`。

## 安装

### macOS / Linux

```bash
git clone <repository-url>
cd AI-tutor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Windows PowerShell

```powershell
git clone <repository-url>
Set-Location AI-tutor
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

参与开发时可将最后一条命令替换为 `python -m pip install -e .`。

验证安装：

```bash
ai-tutor --version
ai-tutor --help
```

## 快速开始

创建本地学习主题并检查状态：

```bash
ai-tutor create machine_learning --name "机器学习"
ai-tutor status machine_learning
ai-tutor graph machine_learning
```

启动多主题学习看板：

```bash
ai-tutor dashboard
```

默认访问地址为 <http://127.0.0.1:8765/>。也可以使用
`ai-tutor dashboard SUBJECT`、`--port`、`--host` 或 `--no-open`。

刚创建的 Subject 只有根节点。需要通过 AI Tutor Skill 或结构化 CLI 协议继续生成 Blueprint、Diagnostic 和更细的知识点。

## 在 Codex 中使用

项目的模型指令位于 [`skill/ai-tutor`](skill/ai-tutor)。将该目录安装到 Codex Skills 目录，重启 Codex，以本仓库作为工作区，然后输入：

```text
$ai-tutor 我想从零学习云计算，目标是成为云计算开发工程师。
我每周可以投入 5 小时，希望多用实践项目讲解。
```

Skill 使用大模型完成讲解、示例、出题和基于 rubric 的语义评估；学习状态和确定性决策始终以 `TutorService` 与 CLI 为准。

详细流程参见 [AI Tutor Skill 使用说明](docs/ai-tutor-skill-user-guide.md)。

## 常用 CLI 命令

| 命令 | 用途 |
| --- | --- |
| `create` | 创建 Subject 根节点 |
| `blueprint-create` | 保存目标、领域全景和路线配置 |
| `blueprint` | 查看目标范围、全景和核心骨架 |
| `roadmap` | 重新计算个性化 MVLG 阶段 |
| `directions` | 查看可进阶方向 |
| `expand` | 围绕一个 anchor 添加有限批次子知识点 |
| `status` / `progress` | 查看状态和进度分析 |
| `next` / `learn` | 选择或开始下一个可教学知识点 |
| `quiz-register` / `quiz-submit` | 保存测验和评估后的尝试 |
| `review` | 查看到期复习与补救候选 |
| `session-start` / `session-end` / `history` | 管理学习会话 |
| `doctor` | 校验持久化数据 |
| `reset-progress` | 保留课程数据，重置某个学习者 |
| `delete-subject` | 删除主题及全部学习者数据 |

命令默认输出 JSON。`blueprint`、`roadmap`、`directions` 支持 Markdown：

```bash
ai-tutor --format markdown roadmap machine_learning
```

`--learner`、`--data-dir`、`--compact` 等全局参数必须写在子命令之前。

## 数据与隐私

默认数据目录为 `./data`：

```text
data/
├── subjects/       # 客观知识图谱
├── blueprints/     # 学习目标、全景和路线配置
├── learners/       # 掌握度、置信度、复习和误区
├── sessions/       # 测验、尝试和学习会话历史
└── archive/        # 重置或删除产生的可恢复归档
```

`data/` 已被 Git 忽略，因为其中可能包含私人学习目标、答案、历史和错误认知。请勿发布该目录；重要学习数据应定期备份。

写入采用原子替换，覆盖前保留 `.bak`，重置或删除前会将受影响文件移动到带时间戳的归档目录。

详细说明参见 [数据与隐私](docs/data-and-privacy.md)。

## 重置与删除

两项操作都要求输入精确的 Subject ID：

```bash
ai-tutor reset-progress machine_learning --confirm machine_learning
ai-tutor delete-subject machine_learning --confirm machine_learning
```

`reset-progress` 只影响指定学习者，保留知识图谱、Blueprint 和已展开主题；`delete-subject` 会从当前工作区移除主题、Blueprint 以及所有学习者的关联数据。

## 使用 DeepSeek 等其他模型

学习引擎不绑定 Codex。DeepSeek、OpenAI API 模型或其他 LLM 都可以负责生成课程和结构化内容，但 V0.1 没有内置模型 Provider。接入其他模型时，需要将输出转换为 `TutorService` 或 CLI 接受的 Blueprint、Expansion、Quiz 和 Assessment JSON。

参见 [架构与模型接入](docs/architecture.md)。

## 开发与测试

运行完整测试：

```bash
python -m unittest discover -v
```

V0.1 测试覆盖图校验、Blueprint、Roadmap、掌握度、测验、持久化、Session、渐进扩图、层级掌握度、看板 API、重置、删除和恢复行为。

参见 [贡献指南](CONTRIBUTING.md) 和 [冒烟测试用例](docs/smoke-test-cases.md)。

## V0.1 限制

- 针对单机、单用户优化。
- 使用 JSON，不包含 SQLite 或服务端数据库。
- 没有登录认证，也不适合直接暴露到公网。
- 前端与后端由同一个本地 Python 进程提供。
- 没有内置 DeepSeek、OpenAI 或其他模型 API 客户端。
- 开放答案的语义评估仍需要大模型或人工评估者。
- 尚未提供自动恢复归档的命令。

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
