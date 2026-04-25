from engine.contracts import ComponentId
from sim.retrieval.search_mock import late_interaction_search


def test_run_id_filter_shape_for_mock_search():
    rows = late_interaction_search("wild-card query", run_id="demo-run", top_k=1)
    assert len(rows) == 1
    assert rows[0].run_id == "demo-run"
    assert isinstance(rows[0].component, ComponentId)
