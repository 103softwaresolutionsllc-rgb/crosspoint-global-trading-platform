import pytest

from fincept_terminal.workflows.executor import WorkflowExecutor
from fincept_terminal.workflows.schema import WorkflowDefinition, WorkflowNode


@pytest.mark.asyncio
async def test_workflow_executor_risk_check_only() -> None:
    wf = WorkflowDefinition(
        name="test",
        nodes=[
            WorkflowNode(
                id="risk", type="trading/risk_check", title="Risk", config={"equity": 100000}
            )
        ],
    )
    result = await WorkflowExecutor().run(wf)
    assert result.success
    assert "risk" in result.node_outputs
