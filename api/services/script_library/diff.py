"""Diff agent-node prompts between two workflow definitions."""

from __future__ import annotations

from typing import Any

from api.schemas.script_library import PromptDiffLine
from api.services.script_library.extract import extract_node_prompts


def _index(prompts: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(p["node_id"], p["field"]): p for p in prompts}


def diff_definition_prompts(
    json_a: dict[str, Any] | None,
    json_b: dict[str, Any] | None,
) -> list[PromptDiffLine]:
    a = _index(extract_node_prompts(json_a))
    b = _index(extract_node_prompts(json_b))
    keys = sorted(set(a) | set(b))
    changes: list[PromptDiffLine] = []
    for key in keys:
        pa, pb = a.get(key), b.get(key)
        if pa and not pb:
            changes.append(
                PromptDiffLine(
                    node_id=key[0],
                    node_name=pa["node_name"],
                    field=key[1],
                    before=pa["text"],
                    after="",
                    change="removed",
                )
            )
        elif pb and not pa:
            changes.append(
                PromptDiffLine(
                    node_id=key[0],
                    node_name=pb["node_name"],
                    field=key[1],
                    before="",
                    after=pb["text"],
                    change="added",
                )
            )
        elif pa and pb:
            if pa["text"] != pb["text"]:
                changes.append(
                    PromptDiffLine(
                        node_id=key[0],
                        node_name=pb["node_name"] or pa["node_name"],
                        field=key[1],
                        before=pa["text"],
                        after=pb["text"],
                        change="changed",
                    )
                )
    return changes
