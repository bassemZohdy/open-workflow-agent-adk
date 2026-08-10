"""Source exporters for portable workflow runtimes."""

from __future__ import annotations

from .models import OpenWorkflowDocument


def export_temporal(document: OpenWorkflowDocument) -> str:
    """Generate a deterministic Temporal Python workflow skeleton."""
    safe_name = "".join(char if char.isalnum() else "_" for char in document.document.name)
    lines = [
        '"""Generated from OpenWorkflow; implement activities before deployment."""',
        "from datetime import timedelta",
        "from temporalio import workflow",
        "",
        "",
        "@workflow.defn",
        f"class {safe_name.title().replace('_', '')}Workflow:",
        "    @workflow.run",
        "    async def run(self, input: dict) -> dict:",
        "        state = dict(input)",
    ]
    for item in document.do:
        activity_name = "".join(char if char.isalnum() else "_" for char in item.name)
        lines.extend(
            [
                f"        # OpenWorkflow task: {item.name}",
                f"        state['{activity_name}'] = await workflow.execute_activity(",
                f"            {activity_name}, state, start_to_close_timeout=timedelta(minutes=5)",
                "        )",
            ]
        )
    lines.append("        return state")
    return "\n".join(lines) + "\n"
