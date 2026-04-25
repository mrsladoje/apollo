from sim.contracts import (
    compare_runs,
    late_interaction_search,
    query_historian,
    run_counterfactual,
)


def test_contract_functions_are_callable():
    assert callable(query_historian)
    assert callable(compare_runs)
    assert callable(run_counterfactual)
    assert callable(late_interaction_search)


def test_mock_search_is_available_through_frozen_contract(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_BACKEND", "mock")
    rows = late_interaction_search("thermal cascade", top_k=2)
    assert rows
    assert rows[0].score > 0

