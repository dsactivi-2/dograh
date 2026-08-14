"""Unit tests for script library prompt extract + diff (no DB)."""

from api.services.script_library.diff import diff_definition_prompts
from api.services.script_library.extract import extract_node_prompts, prompts_blob


def _def(nodes):
    return {"nodes": nodes}


def test_extract_prompt_fields():
    j = _def(
        [
            {
                "id": "n1",
                "type": "agent",
                "data": {
                    "name": "Greeter",
                    "prompt": "Say hello politely",
                    "system_prompt": "You are helpful",
                },
            }
        ]
    )
    prompts = extract_node_prompts(j)
    fields = {p["field"] for p in prompts}
    assert "prompt" in fields
    assert "system_prompt" in fields
    assert any(p["node_name"] == "Greeter" for p in prompts)
    assert "Say hello" in prompts_blob(j)


def test_diff_added_removed_changed():
    a = _def(
        [
            {
                "id": "n1",
                "type": "agent",
                "data": {"name": "A", "prompt": "hello world"},
            },
            {
                "id": "n2",
                "type": "agent",
                "data": {"name": "B", "prompt": "bye"},
            },
        ]
    )
    b = _def(
        [
            {
                "id": "n1",
                "type": "agent",
                "data": {"name": "A", "prompt": "hello there"},
            },
            {
                "id": "n3",
                "type": "agent",
                "data": {"name": "C", "prompt": "new node"},
            },
        ]
    )
    changes = diff_definition_prompts(a, b)
    kinds = {c.change for c in changes}
    assert "changed" in kinds
    assert "removed" in kinds
    assert "added" in kinds
    changed = next(c for c in changes if c.change == "changed")
    assert "hello world" in changed.before
    assert "hello there" in changed.after
