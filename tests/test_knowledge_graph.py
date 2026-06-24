import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_assistant():
    asst = MagicMock()
    asst.history = [
        {"text": "привет я люблю python и программирование"},
        {"text": "сегодня хорошая погода"},
        {"text": "python это отличный язык"},
    ]
    asst.notes = [
        {"text": "купить молоко"},
        {"text": "почитать про нейросети"},
    ]
    asst.dialogue = None
    return asst


class TestKnowledgeGraph:
    def test_rebuild(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        count = kg.rebuild()
        assert count > 0
        assert len(kg.nodes) > 0

    def test_rebuild_no_data(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        mock_assistant.history = []
        mock_assistant.notes = []
        kg = KnowledgeGraph(mock_assistant)
        count = kg.rebuild()
        assert count >= 0

    def test_get_top_nodes(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        top = kg.get_top_nodes(5)
        assert len(top) <= 5

    def test_get_top_edges(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        edges = kg.get_top_edges(5)
        assert isinstance(edges, list)

    def test_get_connections(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        conns = kg.get_connections("python")
        assert isinstance(conns, list)

    def test_get_connections_nonexistent(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        conns = kg.get_connections("xyzabc123")
        assert conns == []

    def test_search(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        results = kg.search("python")
        assert isinstance(results, list)

    def test_get_graph_data(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        data = kg.get_graph_data()
        assert "nodes" in data
        assert "edges" in data

    def test_get_summary(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        summary = kg.get_summary()
        assert "total_nodes" in summary
        assert "total_edges" in summary

    def test_get_insights_with_data(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        insights = kg.get_insights()
        assert len(insights) > 0

    def test_get_insights_no_data(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        mock_assistant.history = []
        mock_assistant.notes = []
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        insights = kg.get_insights()
        assert len(insights) > 0

    def test_incremental_update(self, mock_assistant):
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(mock_assistant)
        kg.rebuild()
        mock_assistant.history.append({"text": "новое сообщение про python"})
        kg.incremental_update()
        assert kg._last_history_len == len(mock_assistant.history)
