# AI Tutor V0.1 主流程冒烟测试

## SMK-001：创建学科、渐进扩图并推荐首个知识点

前置条件：使用全新的临时数据目录。

步骤：

1. 创建 `machine_learning` 学科。
2. 在根节点下加入 `probability`、`statistics`，设置 `probability -> statistics` 前置关系。
3. 查询 `next`。
4. 执行 `doctor`。

预期结果：

- 学科与三个概念成功持久化。
- 首个推荐节点为 `probability`，返回可解释的推荐理由。
- `statistics` 尚未解锁。
- `doctor.status` 为 `ok`。

## SMK-002：诊断测试、Mastery 与 misconception 持久化

前置条件：已完成 SMK-001 的知识图初始化。

步骤：

1. 注册覆盖 Recall、Understanding、Application、Transfer 的 Diagnostic Quiz。
2. 提交四道题的低分结构化评价。
3. 在 Transfer 题中提交 `equiprobable_outcomes` misconception。
4. 使用新 CLI 进程查询 `review`。

预期结果：

- Quiz 提交成功，知识点状态为 `weak`。
- misconception 被写入且未解决。
- 重新启动进程后，`review.remediation_candidates` 仍包含该知识点和误区。

## SMK-003：学习、掌握、解锁、Session 与重启恢复

前置条件：使用完成扩图但没有学习记录的数据目录。

步骤：

1. 启动 Learning Session。
2. 开始学习 `probability`。
3. 提交包含 Quiz、Practice、Application、Transfer、Delayed Review 的高分证据。
4. 结束 Session。
5. 分别使用新进程查询 `status`、`progress`、`history` 和 `graph`。

预期结果：

- `probability` 状态为 `mastered`。
- `statistics` 被解锁并成为下一推荐节点。
- Session 已结束并包含学习事件。
- Progress 显示一个已掌握知识点和一个已完成 Session。
- 重启后 Mastery、下一节点、Session History 和 `next_review` 均未丢失。

## 自动执行

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_smoke -v
```

## SMK-004：中文名称 UTF-8 往返

前置条件：使用全新的临时数据目录。

步骤：

1. 使用中文名称 `机器学习` 创建 Subject。
2. 使用新的 CLI 进程查询 `graph`。
3. 直接以 UTF-8 读取持久化 JSON。

预期结果：

- CLI 创建响应中的名称为 `机器学习`。
- 新进程查询结果中的名称仍为 `机器学习`。
- JSON 文件中的名称也是 `机器学习`，不存在替换字符或 mojibake。
