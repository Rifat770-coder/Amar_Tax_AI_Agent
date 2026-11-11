"""Construct real CrewAI objects, but stub kickoff: no paid provider calls."""
from unittest.mock import patch

import pytest

import amar_tax  # Configure project-local storage before importing CrewAI.

pytest.importorskip("crewai")

from crewai import Crew, Process
from crewai.tasks.task_output import TaskOutput

from amar_tax.crew import run_crew
from amar_tax.database import load_database
from amar_tax.engine import run_offline
from amar_tax.models import Profile
from amar_tax.connection import ConnectionConfig


@pytest.mark.parametrize("use_custom", [False, True])
def test_real_crew_wiring_and_structured_handoff(monkeypatch, use_custom):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setenv("AMAR_TAX_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder-never-sent")
    monkeypatch.setenv("CREWAI_TELEMETRY_DISABLED", "true")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    p = Profile(age=34, gender="female", profession="salaried", has_tin=True,
                location="dhaka_chattogram_city", investment=200000,
                income_sources=[{"kind":"salaried", "amount":1500000}])
    db, source = load_database()
    expected = run_offline(p, db, source)

    def fake_kickoff(crew):
        assert crew.process == Process.sequential
        assert len(crew.agents) == 4
        assert crew.verbose
        assert crew.memory is False
        if use_custom:
            assert crew.agents[0].llm.model == "org/model"
            assert crew.agents[0].llm.custom_openai
        for i, task in enumerate(crew.tasks):
            assert task.agent.role and task.agent.goal and task.agent.backstory
            assert task.agent.verbose
            assert task.output_pydantic is not None
            if i:
                assert task.context == crew.tasks[:i]
        outputs = [expected.classification, expected.calculation, expected.documents, expected.review]
        for task, output in zip(crew.tasks, outputs):
            task.output = TaskOutput(description=task.description, raw=output.model_dump_json(),
                                     pydantic=output, agent=task.agent.role)
        tools = {tool.name: tool for agent in crew.agents for tool in agent.tools}
        assert "thresholds" in tools["lookup_tax_db"].run()
        assert tools["classify_taxpayer"].run() == expected.classification.model_dump_json()
        assert tools["calculate_slab_tax"].run(classification_json=expected.classification.model_dump_json()) == expected.calculation.model_dump_json()

    with patch.object(Crew, "kickoff", fake_kickoff):
        config = ConnectionConfig("https://proxy.example/v1", "org/model", "test-proxy-key") if use_custom else None
        actual = run_crew(p, db, source, config=config)
    assert actual.calculation.net_tax == 110000
    assert actual.review.status == "Passed"
    assert actual.mode.startswith("CrewAI")
