"""Extract searchable prompts from workflow definition JSON."""

from __future__ import annotations

from typing import Any


PROMPT_FIELDS = (
    "prompt",
    "system_prompt",
    "qa_system_prompt",
    "global_prompt",
    "user_prompt",
    "first_message",
    "message",
)


def extract_node_prompts(workflow_json: dict[str, Any] | None) -> list[dict[str, str]]:
    """Return list of {node_id, node_name, node_type, field, text}."""
    if not isinstance(workflow_json, dict):
        return []
    nodes = workflow_json.get("nodes") or []
    out: list[dict[str, str]] = []
    if not isinstance(nodes, list):
        return out
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "")
        node_type = str(node.get("type") or "")
        data = node.get("data") if isinstance(node.get("data"), dict) else {}
        node_name = str(data.get("name") or data.get("label") or node_id)
        for field in PROMPT_FIELDS:
            val = data.get(field)
            if isinstance(val, str) and val.strip():
                out.append(
                    {
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "field": field,
                        "text": val,
                    }
                )
        # nested prompts
        for k, v in data.items():
            if k in PROMPT_FIELDS:
                continue
            if isinstance(v, str) and k.endswith("prompt") and v.strip():
                out.append(
                    {
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_type": node_type,
                        "field": k,
                        "text": v,
                    }
                )
    return out


def prompts_blob(workflow_json: dict[str, Any] | None) -> str:
    parts = [p["text"] for p in extract_node_prompts(workflow_json)]
    names = [p["node_name"] for p in extract_node_prompts(workflow_json)]
    return "\n".join(parts + names)
