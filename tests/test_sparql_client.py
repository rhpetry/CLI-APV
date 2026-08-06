from __future__ import annotations

import pytest

from apv.sparql_client import SparqlClient


def test_local_file_client_parses_and_queries_turtle(write_turtle) -> None:
    path = write_turtle(
        """
        @prefix ex: <https://example.org/> .
        ex:subject ex:predicate ex:object .
        """
    )
    client = SparqlClient.from_local_file(str(path), format="turtle")

    rows = list(client.query("SELECT ?subject WHERE { ?subject ?p ?o }"))

    assert str(rows[0][0]) == "https://example.org/subject"


def test_remote_query_uses_store_backed_graph(monkeypatch) -> None:
    captured = {}
    store = object()

    class FakeGraph:
        def __init__(self, *, store):
            captured["store"] = store

        def query(self, sparql, initNs):
            captured["sparql"] = sparql
            captured["init_ns"] = initNs
            return [("result",)]

    monkeypatch.setattr("apv.sparql_client.Graph", FakeGraph)
    client = SparqlClient(store=store)

    assert list(client.query("SELECT * WHERE {}")) == [("result",)]
    assert captured == {
        "store": store,
        "sparql": "SELECT * WHERE {}",
        "init_ns": {},
    }


def test_query_requires_a_backend() -> None:
    with pytest.raises(RuntimeError, match="No SPARQL backend configured"):
        list(SparqlClient().query("SELECT * WHERE {}"))
