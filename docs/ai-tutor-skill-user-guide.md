# AI Tutor Skill 使用指南（V0.1）

本文说明如何在 Codex 中使用项目附带的 `ai-tutor` Skill 建立学习主题、诊断基础、下钻知识点、完成测验，并让 Roadmap 根据掌握度持续调整。

> 文中使用 `<project-root>` 表示仓库根目录，使用 `<data-dir>` 表示学习数据目录。请勿把用户名、私人目录、学习记录或凭据写入公开文档。

## 1. Skill 与引擎的分工

- **Skill** 约束大模型的教学流程，负责澄清目标、讲解、出题和语义评估。
- **Tutor Engine** 保存知识图与学习状态，确定解锁、Mastery、复习和 Roadmap。
- **Dashboard** 读取同一份本地状态，展示 Blueprint、Roadmap、知识点和历史。

大模型不是状态数据库。任何影响进度的结果，都应通过 `TutorService` 或 `ai-tutor` CLI 持久化。

## 2. 安装项目

### macOS / Linux

```bash
cd <project-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Windows PowerShell

```powershell
Set-Location <project-root>
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

验证：

```bash
ai-tutor --version
ai-tutor doctor
```

## 3. 安装 Skill

将仓库中的 `skill/ai-tutor/` 整体复制到 Codex Skills 目录，最终结构应为：

```text
<codex-home>/skills/ai-tutor/
├── SKILL.md
└── references/
```

常见的个人 Skills 根目录为 `${CODEX_HOME}/skills`；未配置 `CODEX_HOME` 时，以当前 Codex 安装显示的 Skills 目录为准。复制后重启 Codex，并以 `<project-root>` 作为工作区。也可以直接让 Codex 执行：

```text
请把这个仓库中的 skill/ai-tutor 安装为个人 Skill，并验证安装结果。
```

## 4. 从目标开始

推荐同时说明目标、基础、时间和偏好：

```text
$ai-tutor 我想系统学习云计算，目标是在 6 个月内具备云计算开发工程师能力。
我会 Python 和 Linux 基础，每周可投入 5 小时，希望项目驱动并重点学习 Kubernetes。
```

Skill 会规范化 Subject、生成粗粒度 Blueprint、进行少量诊断、建立最小可行学习图（MVLG），再推荐当前最值得学习的已解锁知识点。

```bash
ai-tutor blueprint cloud_computing
ai-tutor roadmap cloud_computing
ai-tutor status cloud_computing
```

## 5. 学习与下钻子主题

当 Roadmap 出现“分布式系统基础”“容器镜像”等粗粒度节点时，不必一次生成无限深的知识树。直接要求有限下钻：

```text
$ai-tutor 展开 cloud_computing 中的“分布式系统基础”，生成下一层可教学、可测量的必修知识点，并从第一个已解锁节点开始教我。
```

一次扩展应包含稳定且唯一的子节点 ID、`parent_id`、前置依赖、`required_for_parent` 和可观察的学习目标。学习子节点后，父主题掌握度会按必修子节点聚合；掌握度、解锁或误区变化后，再查询 `roadmap` 即可得到最新路线。无需重新生成 Blueprint，也不应丢弃已学记录。

继续下钻同样适用：

```text
$ai-tutor 继续展开“容器镜像”，但只生成完成当前目标所需的下一层知识点。
```

Dashboard 中也可以点击知识点进入下级视图。

## 6. 完整学习循环

```text
$ai-tutor 继续学习 cloud_computing。先检查到期复习，再选择下一知识点；讲解后给我练习和迁移题，并保存结果。
```

标准循环为：检查复习与误区 → 选择已解锁节点 → 讲解与实践 → 用 Recall、Understanding、Application、Transfer 等证据评估 → 保存评分与误区 → 更新父主题 Mastery、解锁和 Roadmap。

不要只回答“懂了”。可以要求可验证任务，例如解释差异、诊断故障、修改配置或完成小项目。

## 7. 常用请求

```text
$ai-tutor 查看 cloud_computing 当前进度、薄弱点和下一步推荐。
$ai-tutor 测试我对 Kubernetes 调度的掌握程度，不要先给答案。
$ai-tutor 复习今天到期的知识点，优先处理未解决误区。
$ai-tutor 展示 Blueprint、动态 Roadmap 和进阶方向，并解释三者区别。
```

## 8. Dashboard

```bash
ai-tutor dashboard
```

默认访问 <http://127.0.0.1:8765/>。V0.1 看板支持多个 Subject、学习路线、层级知识点、掌握度和历史；它没有认证，不应直接暴露到公网。

## 9. 数据与备份

默认数据位于 `<project-root>/data/`。自定义目录时，全局参数要放在子命令前：

```bash
ai-tutor --data-dir <data-dir> status cloud_computing
```

也可以设置 `AI_TUTOR_DATA_DIR`。`data/` 可能包含学习目标、回答、历史和错误认知，已被 Git 忽略。发布前仍应检查 Git 状态，并单独备份重要数据。详见 [数据与隐私](data-and-privacy.md)。

## 10. 重置与删除

```bash
ai-tutor reset-progress cloud_computing --confirm cloud_computing
ai-tutor delete-subject cloud_computing --confirm cloud_computing
```

两项操作都会先创建归档。重置只影响指定学习者并保留课程结构；删除会移除该 Subject、Blueprint 和所有学习者的关联数据。

## 11. 使用 DeepSeek 等模型

引擎与 Codex 解耦，可以换用 DeepSeek 或其他模型，但 V0.1 没有内置 Provider 适配器。新集成必须遵循 `skill/ai-tutor/SKILL.md`，输出引擎接受的 Blueprint、Expansion、Quiz 和 Assessment 结构，通过服务层或 CLI 读写状态，并把生成内容交给引擎校验。详见 [架构说明](architecture.md)。

## 12. 故障排查

- `ai-tutor` 找不到：激活虚拟环境，重新执行 `python -m pip install -e .`。
- Skill 未触发：确认目录为 `.../skills/ai-tutor/SKILL.md`，然后重启 Codex。
- 看板无数据：确认 Dashboard 与 CLI 使用同一 `--data-dir`。
- 节点未解锁：检查前置节点 Mastery，不要手动改状态。
- 数据异常：运行 `ai-tutor doctor`，检查 `.bak` 或 `archive/`。
- Roadmap 未变化：确认测验已提交并持久化，再运行 `ai-tutor roadmap SUBJECT`。

## 13. V0.1 边界

- 面向单机、单用户，不含登录和多租户隔离。
- JSON 存储不适合多进程并发写入。
- 语义评分需要大模型或人工评估。
- 归档恢复暂时需要人工操作。
- 项目采用 Apache License 2.0；再分发和修改时应遵守许可证及 NOTICE 相关要求。
