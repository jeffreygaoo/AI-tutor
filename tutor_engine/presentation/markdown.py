"""Render selected Tutor Engine views as readable Markdown visualizations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _cell(value: Any) -> str:
    """Return a value that cannot break a Markdown table row."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        value = f"{value:.3f}".rstrip("0").rstrip(".")
    text = str(value).replace("|", "\\|")
    return text.replace("\r\n", "<br>").replace("\n", "<br>")


def _list(values: Sequence[Any] | None) -> str:
    return _cell("、".join(str(value) for value in (values or ())))


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    header = "| " + " | ".join(_cell(item) for item in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_cell(item) for item in row) + " |" for row in rows]
    return "\n".join((header, separator, *body))


def _concept_names(blueprint: Mapping[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for section in blueprint.get("landscape", ()):
        for concept in section.get("concepts", ()):
            names[concept["id"]] = concept.get("name", concept["id"])
    return names


def _mermaid_label(value: Any) -> str:
    """Escape user-authored labels embedded in quoted Mermaid nodes."""
    return str(value or "—").replace("\\", "\\\\").replace('"', "&quot;").replace("\r", " ").replace("\n", " ")


def _mindmap(value: Mapping[str, Any]) -> str:
    expansion_candidates = set(value.get("expansion_candidates", ()))
    lines = ["```mermaid", "mindmap", f'  root(("{_mermaid_label(value.get("subject_id"))}"))']
    for section_number, section in enumerate(value.get("landscape", ()), start=1):
        lines.append(f'    section_{section_number}["{_mermaid_label(section.get("name", section.get("id")))}"]')
        for concept_number, concept in enumerate(section.get("concepts", ()), start=1):
            status = concept.get("status")
            labels = [status] if status else []
            if concept.get("id") in expansion_candidates:
                labels.append("可展开")
            suffix = f" · {' · '.join(labels)}" if labels else ""
            lines.append(f'      concept_{section_number}_{concept_number}["{_mermaid_label(concept.get("name", concept.get("id")))}{_mermaid_label(suffix)}"]')
    if value.get("advanced_directions"):
        lines.append('    advancement["进阶方向"]')
        for number, direction in enumerate(value.get("advanced_directions", ()), start=1):
            lines.append(f'      direction_{number}["{_mermaid_label(direction.get("name", direction.get("id")))}"]')
    lines.append("```")
    return "\n".join(lines)


def _dependency_graph(value: Mapping[str, Any], names: Mapping[str, str]) -> str:
    dependencies = value.get("core_dependencies", ())
    if not dependencies:
        return "> 当前核心骨架没有可展示的直接前置依赖。"
    concept_ids = list(dict.fromkeys(
        concept_id
        for relation in dependencies
        for concept_id in (relation.get("source"), relation.get("target"))
        if concept_id
    ))
    node_ids = {concept_id: f"node_{number}" for number, concept_id in enumerate(concept_ids, start=1)}
    lines = ["```mermaid", "flowchart LR"]
    for concept_id in concept_ids:
        lines.append(f'  {node_ids[concept_id]}["{_mermaid_label(names.get(concept_id, concept_id))}"]')
    for relation in dependencies:
        lines.append(f'  {node_ids[relation["source"]]} --> {node_ids[relation["target"]]}')
    lines.append("```")
    return "\n".join(lines)


def _directions_details(value: Mapping[str, Any], names: Mapping[str, str]) -> str:
    blocks = []
    for direction in value.get("advanced_directions", ()):
        entry_names = [names.get(item, item) for item in direction.get("entry_concept_ids", ())]
        scope_label = "当前范围内" if direction.get("in_scope", False) else "可选进阶"
        blocks.append("\n".join((
            "<details>",
            f'<summary>{_cell(direction.get("name", direction.get("id")))} · {scope_label}</summary>',
            "",
            _cell(direction.get("description")),
            "",
            f"- 入口 Concept：{_list(entry_names)}",
            "",
            "</details>",
        )))
    return "\n\n".join(blocks) if blocks else "> 暂无进阶方向。"


def render_blueprint(value: Mapping[str, Any]) -> str:
    """Render a Blueprint as a mind map plus focused decision views."""
    scope = value.get("scope", {})
    names = _concept_names(value)
    parts = [
        f"# Subject Blueprint：{_cell(value.get('subject_id', ''))}",
        "## 学习范围",
        "\n".join((
            f"> **学习目标：** {_cell(scope.get('goal'))}",
            ">",
            f"> **目标水平：** {_cell(scope.get('target_level'))}　·　**每周投入：** {_cell(f'{scope["weekly_hours"]} 小时' if scope.get('weekly_hours') is not None else None)}",
            "",
            f"- 包含范围：{_list(scope.get('included'))}",
            f"- 排除范围：{_list(scope.get('excluded'))}",
        )),
        "## 领域全景思维导图",
        _mindmap(value),
        "> 思维导图用于建立全局 Mental Model；节点后的文字表示学习状态与是否支持按需展开。",
        "## 核心骨架",
        _table(
            ("层", "Concept", "纳入方式", "Goal", "重要度", "Leverage", "Core Score", "直接后继", "间接后继", "选择原因"),
            tuple(
                (
                    item.get("topological_layer", max(0, int(item.get("stage", 1)) - 1)),
                    names.get(item.get("concept_id"), item.get("concept_id")),
                    item.get("inclusion_type"),
                    item.get("goal_relevance"),
                    item.get("importance_score"),
                    item.get("leverage_score"),
                    item.get("core_score"),
                    item.get("direct_dependents"),
                    item.get("indirect_dependents"),
                    item.get("selection_reason"),
                )
                for item in value.get("core_backbone", ())
            ),
        ),
        "## 核心依赖关系",
        _dependency_graph(value, names),
        "> 箭头方向：前置 Concept → 后续 Concept。",
        "## 进阶方向",
        _directions_details(value, names),
    ]
    return "\n\n".join(parts) + "\n"


def render_roadmap(value: Mapping[str, Any]) -> str:
    rows = []
    for stage in value.get("stages", ()):
        for concept in stage.get("concepts", ()):
            mastery = concept.get("mastery", {})
            rows.append((stage.get("stage"), stage.get("status"), concept.get("name", concept.get("id")), concept.get("status"), mastery.get("score"), concept.get("leverage_score")))
    return "\n\n".join((
        f"# 学习路径：{_cell(value.get('subject', ''))}",
        _table(("阶段", "阶段状态", "Concept", "学习状态", "掌握度", "杠杆分数"), rows),
    )) + "\n"


def render_directions(value: Mapping[str, Any]) -> str:
    return "\n\n".join((
        f"# 进阶方向：{_cell(value.get('subject', ''))}",
        _table(
            ("方向", "说明", "入口 Concept", "当前范围内", "入口已就绪"),
            tuple((item.get("name", item.get("id")), item.get("description"), _list(item.get("entry_concept_ids")), item.get("in_scope", False), item.get("entry_ready", False)) for item in value.get("directions", ())),
        ),
    )) + "\n"


def render_markdown(command: str, value: Mapping[str, Any]) -> str:
    renderers = {
        "blueprint": render_blueprint,
        "roadmap": render_roadmap,
        "directions": render_directions,
    }
    try:
        renderer = renderers[command]
    except KeyError as exc:
        raise ValueError(f"Markdown output is not supported for command: {command}") from exc
    return renderer(value)
