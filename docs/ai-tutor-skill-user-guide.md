# AI Tutor Skill 使用说明

本文说明如何在 Codex 中使用本项目的 `ai-tutor` Skill，如何开始、继续、测试和复习一个学科，以及如何通过 CLI 检查学习状态和排查问题。

## 1. 这个 Skill 是什么

`ai-tutor` 不是一份固定课程，也不只是一个“回答问题”的提示词。它由两个部分组成：

1. **Codex / LLM**：理解学习目标、讲解知识、生成例子和 Quiz、分析开放式回答、识别 misconception。
2. **Python Tutor Engine**：保存知识图、学习状态和历史，计算 Mastery、判断解锁、安排复习、推荐下一知识点。

核心闭环是：

```text
学习目标
  ↓
渐进构建 Knowledge Graph
  ↓
Diagnostic
  ↓
选择当前知识点
  ↓
讲解 → 示例 → 提问 → 练习 → Quiz
  ↓
结构化答案评价
  ↓
Mastery / Confidence / Misconception 更新
  ↓
解锁与复习调度
  ↓
推荐下一知识点
```

这里最重要的边界是：

- Codex 负责需要语言理解和教学判断的部分。
- Engine 负责确定性计算和持久化状态。
- 用户说“我懂了”不会直接产生 `mastered` 状态。
- 关闭 Codex 后，学习状态仍保存在 JSON 数据中。

## 2. 当前安装状态

本机已经完成以下安装：

- Skill：`C:\Users\leinao\.codex\skills\ai-tutor`
- 项目：`D:\Codex\Tutor`
- Python 虚拟环境：`D:\Codex\Tutor\.venv`
- CLI：`D:\Codex\Tutor\.venv\Scripts\ai-tutor.exe`
- Engine 版本：`0.1.0`

建议始终在 `D:\Codex\Tutor` 工作区中使用该 Skill。Skill 需要访问这里的 Engine、虚拟环境和 `data/` 目录。

如果刚安装或更新了 Skill，建议重启 Codex 或新建一个任务，以确保 Skill 列表已经刷新。

## 3. 最简单的使用方式

在 Codex 中新建一个任务，工作区选择：

```text
D:\Codex\Tutor
```

然后输入：

```text
$ai-tutor 我想从零学习机器学习。
```

`$ai-tutor` 是显式调用。首次试用时建议保留此前缀，确保 Codex 使用本 Skill，而不是进行普通问答。

也可以一次给出更多背景：

```text
$ai-tutor 我想从零学习机器学习。
目标是能够独立完成一个分类项目，并理解常见模型为什么有效。
我每周可以投入 5 小时，数学基础一般，希望优先用直观例子讲解。
```

信息越完整，初始图和诊断越容易贴近目标。最有价值的信息包括：

- 想学什么；
- 为什么学；
- 希望最终做出什么；
- 当前水平；
- 每周可投入时间；
- 喜欢的讲解方式；
- 已知的薄弱环节。

## 4. 常用自然语言指令

### 4.0 查看领域全景、核心骨架和进阶方向

```text
$ai-tutor 为机器学习生成一份目标范围内的领域全景、核心骨架和进阶方向。
我的目标是完成表格分类项目，不包含强化学习。
```

Blueprint 会区分：

- `Scope`：目标、目标水平、包含和排除范围；
- `Landscape`：约 20–60 个粗粒度领域节点；
- `Core Backbone`：Engine 根据依赖中心性、下游覆盖、目标相关性、迁移价值、Mental Model 价值与学习成本计算的核心概念；
- `Advanced Directions`：完成骨架后可选择的深入方向；
- `Roadmap`：把骨架按 prerequisite 层级组织成动态阶段。

常用查询：

```text
$ai-tutor 展示机器学习的领域全景。
$ai-tutor 展示机器学习核心骨架和动态 Roadmap。
$ai-tutor 我完成核心骨架后可以向哪些方向深入？
```

Blueprint 只生成全局粗粒度地图。进入某个分支后，系统才围绕对应 anchor 按需展开最多 20 个更细知识节点。

### 4.1 开始一个新学科

```text
$ai-tutor 我想从零学习概率论。
```

```text
$ai-tutor 我想学习财务报表分析，目标是能够独立分析上市公司年报。
```

```text
$ai-tutor 帮我建立一个计算机网络学习项目。我知道一点 HTTP，但不理解 TCP 和路由。
```

新学科的正常流程是：

1. 创建 Subject；
2. 只展开当前需要的一小部分知识图；
3. 进行简短 Diagnostic；
4. 根据结果计算可学习节点；
5. 推荐第一个知识点；
6. 开始教学 Session。

系统不会一开始生成几百个概念。Knowledge Graph 会随着学习逐步扩展。

### 4.2 继续上一次学习

```text
$ai-tutor 继续学习机器学习。
```

```text
$ai-tutor 恢复我上次的概率论学习，告诉我现在应该学什么。
```

正常情况下，Skill 会先读取 `status`，必要时读取 `graph`，然后由 Engine 返回下一节点和推荐理由。它不应该根据聊天记忆猜测进度。

### 4.3 查看进度

```text
$ai-tutor 我现在学到哪里了？
```

```text
$ai-tutor 给我一份机器学习的学习进度报告。
```

```text
$ai-tutor 展示最近几次学习 Session 的历史。
```

进度报告可以包含：

- 概念总数和已掌握数；
- 状态分布；
- 平均 Mastery；
- 平均 Confidence；
- Quiz/练习尝试次数；
- 未解决 misconception；
- 到期复习数量；
- Session 数量；
- Review retention；
- 当前和下一知识点。

### 4.4 测试某个知识点

```text
$ai-tutor 测试一下我对概率的掌握程度。
```

```text
$ai-tutor 不要继续讲解，直接测试我对线性回归的理解。
```

Quiz 至少覆盖四类能力：

| 类型 | 检查内容 | 示例 |
| --- | --- | --- |
| Recall | 是否记得基本定义 | “PE 是什么？” |
| Understanding | 是否理解原因和机制 | “为什么 PE 可以用于估值？” |
| Application | 是否能处理当前类型的问题 | “股价与 EPS 已知，计算 PE。” |
| Transfer | 是否能迁移到不同情境 | “低 PE、负增长和高 PE、高增长应如何比较？” |

Skill 会收集完整回答，再由 Codex 按隐藏 rubric 生成结构化评价。最终 Mastery 由 Engine 计算，而不是由 Codex随意指定。

### 4.5 复习

```text
$ai-tutor 复习一下最近容易忘的知识。
```

```text
$ai-tutor 查看今天到期的复习任务。
```

```text
$ai-tutor 针对我尚未解决的错误认知安排一次复习。
```

复习优先级通常是：

1. 已到期的 spaced review；
2. 未解决的 misconception；
3. `weak` 概念；
4. 信心不足的 `familiar` 概念。

当前复习间隔是：

```text
1 天 → 3 天 → 7 天 → 14 天 → 30 天
```

复习成功会延长间隔，失败会缩短间隔。Review Quiz 会额外产生 `delayed_review` 证据。

### 4.6 结束本次学习

当你准备结束时，明确告诉 Tutor：

```text
今天先到这里，结束本次学习 Session。
```

```text
保存进度并结束今天的学习。
```

Skill 不会因为单个助手回复结束就自动关闭 Session。明确结束后，Engine 会记录结束时间和本次事件历史。

## 5. 一次完整使用示例

下面是一条推荐的首次体验路径。

### 第一步：提出目标

```text
$ai-tutor 我想从零学习机器学习。
最终希望完成一个表格数据二分类项目。
每周能投入 5 小时，数学基础一般，请优先使用直观例子。
```

### 第二步：完成 Diagnostic

Tutor 会给出少量问题。请按真实水平回答，不需要提前搜索答案。Diagnostic 的价值在于定位起点，而不是取得高分。

### 第三步：学习当前概念

正常教学节奏应是：

```text
短解释 → 一个例子 → 一个问题 → 等待回答 → 针对性反馈
```

如果讲解过长，可以直接说：

```text
请缩短讲解，一次只讲一个关键点，并多问我问题。
```

### 第四步：完成 Quiz

完成 Recall、Understanding、Application、Transfer 四类问题。遇到不会的问题可以直接说不会；真实证据比猜测更有价值。

### 第五步：查看更新结果

```text
$ai-tutor 根据刚才的结果告诉我：Mastery、Confidence、发现的误区，以及下一步应该学什么。
```

### 第六步：结束并恢复

结束：

```text
今天先到这里，结束本次学习 Session。
```

稍后新建任务或重启 Codex，再输入：

```text
$ai-tutor 继续学习机器学习。
```

预期结果是：Tutor 能恢复 Knowledge Graph、Mastery、Confidence、misconception、Review 和下一知识点。

## 6. 如何理解学习状态

Learning Graph 中的常见状态：

| 状态 | 含义 |
| --- | --- |
| `locked` | 前置知识未达到阈值，暂不可学习 |
| `available` | 前置条件满足，可以开始 |
| `learning` | 当前正在学习或证据处于中间水平 |
| `weak` | 已有尝试，但表现明显不足 |
| `familiar` | 有一定理解，但分数或 Confidence 尚不足 |
| `mastered` | Mastery 与 Confidence 均达到掌握标准 |

当前 Mastery 证据权重：

| 证据 | 权重 |
| --- | ---: |
| Concept Quiz | 0.30 |
| Practice | 0.25 |
| Application | 0.20 |
| Transfer | 0.15 |
| Delayed Review | 0.10 |

分数区间：

```text
0.00–0.29  weak
0.30–0.59  learning
0.60–0.79  familiar
0.80–1.00  mastered 候选
```

`mastered` 还要求 Confidence 至少为 `0.60`。例如：

```text
Mastery = 0.90
Confidence = 0.30
```

表示当前表现很好，但样本太少，状态仍不应被视为真正掌握。

## 7. Misconception 如何工作

系统不只记录“答错”，还尝试识别可复用的错误认知。例如：

```text
低 PE 永远代表股票更便宜
```

misconception 应满足：

- 是一个明确的错误心智模型；
- 可能在多个问题中重复出现；
- 可以通过反例和迁移题检验；
- 不是笔误、遗漏或一次性的模糊回答。

后续补救流程是：

```text
指出关键区别
→ 给出反例
→ 针对性练习
→ 换一种表面形式重新测试
```

只有新的学习证据才能支持误区已经解决，普通对话中的“明白了”不会直接改写状态。

## 8. 多个学习者

CLI 支持通过 `--learner` 分离不同学习者的数据。例如：

```powershell
$Tutor = ".\.venv\Scripts\ai-tutor.exe"
& $Tutor --learner alice status machine_learning
& $Tutor --learner bob status machine_learning
```

注意：`--learner` 是全局参数，必须放在子命令之前。

Codex 中也可以明确指定：

```text
$ai-tutor 以 learner_id=alice 继续学习机器学习。
```

同一 Subject 的客观 Knowledge Graph 可以共享，但每个 learner 的 Mastery、misconception、Session 和 Review 独立保存。

## 9. CLI 使用说明

多数情况下不需要手动操作 CLI，Skill 会代为调用。CLI 主要用于开发、排障、验收和查看原始 JSON。

在 PowerShell 中：

```powershell
cd D:\Codex\Tutor
$Tutor = ".\.venv\Scripts\ai-tutor.exe"
& $Tutor --version
& $Tutor --help
```

### 9.1 命令总览

| 命令 | 用途 |
| --- | --- |
| `create` | 创建新 Subject 和根概念 |
| `status` | 查询简要状态、当前节点和下一节点 |
| `graph` | 查看概念、关系及 learner state |
| `next` | 计算下一最佳概念和理由 |
| `learn` | 将可学习概念进入 learning 状态 |
| `evaluate` | 直接提交数值型 Mastery 证据 |
| `expand` | 提交一批渐进图扩展 |
| `quiz-register` | 注册结构化 Quiz |
| `quiz-submit` | 提交回答与逐题结构化评价 |
| `review` | 查看到期复习和补救候选 |
| `session-start` | 开始 Learning Session |
| `session-end` | 结束当前 Learning Session |
| `history` | 查看 Session 历史和事件 |
| `progress` | 查看详细进度分析 |
| `doctor` | 校验持久化数据和活动 Session |
| `blueprint-create` | 创建目标范围、粗粒度全景、算法骨架和进阶方向 |
| `blueprint` | 查看 Subject Blueprint 全景 |
| `roadmap` | 查看按依赖分层并叠加个人状态的核心路线 |
| `directions` | 查看进阶方向和入口准备状态 |

### 9.2 常用命令

```powershell
$Tutor = ".\.venv\Scripts\ai-tutor.exe"

# 创建学科
& $Tutor create machine_learning --name "Machine Learning"

# 开始 Session
& $Tutor session-start machine_learning

# 查看推荐节点
& $Tutor next machine_learning

# 开始学习指定概念
& $Tutor learn machine_learning --concept probability

# 查看状态和进度
& $Tutor status machine_learning
& $Tutor progress machine_learning

# 查看复习
& $Tutor review machine_learning

# 结束 Session
& $Tutor session-end machine_learning

# 查看历史并检查数据
& $Tutor history machine_learning
& $Tutor doctor machine_learning
```

### 9.3 全局参数

全局参数应写在子命令之前：

```powershell
& $Tutor --learner alice --compact status machine_learning
```

| 参数 | 作用 |
| --- | --- |
| `--learner ID` | 指定学习者，默认 `default` |
| `--data-dir PATH` | 指定数据目录 |
| `--compact` | 输出单行 JSON |
| `--version` | 显示版本 |

也可以通过环境变量改变默认数据目录：

```powershell
$env:AI_TUTOR_DATA_DIR = "D:\MyTutorData"
& $Tutor status machine_learning
```

### 9.4 从 stdin 提交 JSON

`expand`、`quiz-register` 和 `quiz-submit` 支持 `--input -`：

```powershell
Get-Content -Raw .\quiz.json | & $Tutor quiz-register --input -
```

## 10. 数据保存在哪里

默认数据目录：

```text
D:\Codex\Tutor\data
```

主要结构：

```text
data/
├── subjects/
│   └── machine_learning.json
├── learners/
│   └── default/
│       └── machine_learning.json
└── sessions/
    └── default/
        └── machine_learning/
            ├── quizzes/
            ├── attempts/
            └── learning_sessions/
```

- `subjects` 保存客观 Concept Graph；
- `learners` 保存个人 Mastery、Confidence、状态、误区和 Review；
- `sessions` 保存 Quiz、Attempt 和 Learning Session History。

数据采用带 `schema_version` 的 JSON。覆盖已有文件前会保留 `.json.bak`。如果主 JSON 损坏，Repository 会尝试读取上一版备份。

## 11. 排障

### 11.1 Codex 没有识别 `$ai-tutor`

检查：

```text
C:\Users\leinao\.codex\skills\ai-tutor\SKILL.md
```

然后重启 Codex 或新建任务。还应确认任务工作区是：

```text
D:\Codex\Tutor
```

### 11.2 找不到 Python 或 `ai-tutor`

本机不依赖全局 `python`。直接使用：

```powershell
D:\Codex\Tutor\.venv\Scripts\ai-tutor.exe --version
```

如果 `.venv` 被删除，需要重新创建并安装项目。

### 11.3 Subject 不存在

错误示例：

```text
subject not found: machine_learning
```

先确认 `data/subjects/machine_learning.json` 是否存在。新学科需要先执行 `create`，或在 Codex 中明确说“从零开始学习某学科”。

### 11.4 Concept 被锁定

```text
concept is locked: regression
```

这通常不是程序错误，而是前置知识没有达到 relation threshold。运行：

```powershell
& $Tutor graph machine_learning
& $Tutor next machine_learning
```

查看 prerequisite 和 Engine 推荐理由。不要手动修改 Mastery 来绕过锁定。

### 11.5 已有活动 Session

```text
learning session already active: session_xxx
```

先运行 `status` 或 `history` 确认。如果是上一轮正常延续，就继续使用该 Session；如果确实已经结束，执行：

```powershell
& $Tutor session-end machine_learning
```

### 11.6 JSON 或状态异常

运行：

```powershell
& $Tutor doctor machine_learning
```

正常输出应包含：

```json
{
  "status": "ok",
  "schema_version": 1
}
```

如果 `recovered_from_backup` 非空，说明主文件读取失败，本次检查使用了 `.bak` 数据。此时应先备份整个 `data/`，再调查损坏原因。

### 11.7 Skill 源码更新后没有生效

开发源码位于：

```text
D:\Codex\Tutor\skill\ai-tutor
```

已安装副本位于：

```text
C:\Users\leinao\.codex\skills\ai-tutor
```

两者不是动态链接。修改源码后，需要重新同步安装副本并重启 Codex。

## 12. 验证安装是否正常

### CLI 检查

```powershell
cd D:\Codex\Tutor
.\.venv\Scripts\ai-tutor.exe --version
```

预期：

```text
ai-tutor 0.1.0
```

### 冒烟测试

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_smoke -v
```

当前冒烟测试覆盖：

1. 创建学科、扩图和首节点推荐；
2. Diagnostic、Mastery 和 misconception 持久化；
3. 学习、掌握、解锁、Session 和重启恢复。

### 完整测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 13. 推荐的使用习惯

- 第一次使用显式写 `$ai-tutor`。
- 一个 Session 聚焦一个或少量紧密相关的概念。
- Diagnostic 按真实水平回答，不为了高分查答案。
- 要求 Tutor “少讲、多问、一次一个概念”。
- 不会就明确说不会，这比猜测更有诊断价值。
- 每轮 Quiz 后查看 Mastery、Confidence 和 misconception。
- 明确说“结束 Session”，避免留下不必要的活动会话。
- 定期使用“复习到期知识”和“查看进度报告”。
- 不手动编辑 learner JSON 来提高分数或绕过 prerequisite。
- 重要数据可定期备份整个 `data/` 目录。

## 14. 当前限制

V0.1 有意保持简单：

- 使用 JSON，而不是 SQLite/PostgreSQL；
- 没有 React Graph UI；
- 没有 FastAPI；
- 没有 RAG、Vector DB 或 GraphRAG；
- Quiz 内容和开放答案语义评价依赖 Codex；
- Skill 需要能访问本项目工作区和本地 Engine；
- Knowledge Graph 采用渐进扩展，不追求一次生成完整学科。

这些限制是为了优先验证核心问题：

> 根据学习者当前真正掌握的知识，下一步最值得学习什么，为什么？

## 15. 快速指令速查

```text
$ai-tutor 我想从零学习机器学习。

$ai-tutor 继续学习机器学习。

$ai-tutor 我现在学到哪里了？

$ai-tutor 下一步应该学什么？为什么？

$ai-tutor 测试一下我对概率的掌握程度。

$ai-tutor 复习今天到期的知识。

$ai-tutor 针对我未解决的误区安排复习。

$ai-tutor 给我一份详细进度报告。

今天先到这里，结束本次学习 Session。
```

## 16. 相关资料

- [项目 README](../README.md)
- [Skill 主指令](../skill/ai-tutor/SKILL.md)
- [教学规则](../skill/ai-tutor/references/pedagogy.md)
- [图扩展规则](../skill/ai-tutor/references/graph-rules.md)
- [Mastery 规则](../skill/ai-tutor/references/mastery-rules.md)
- [Quiz 规则](../skill/ai-tutor/references/quiz-rules.md)
- [冒烟测试用例](smoke-test-cases.md)
- [OpenAI 官方 Codex/ChatGPT 用例](https://learn.chatgpt.com/use-cases)
- [OpenAI Developers](https://developers.openai.com/)
