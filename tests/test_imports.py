def test_agent_import():
    from agent import Agent

    assert Agent is not None


def test_tool_registry():
    from tools import TOOL_REGISTRY

    assert "open_app" in TOOL_REGISTRY
    assert len(TOOL_REGISTRY) == 7
