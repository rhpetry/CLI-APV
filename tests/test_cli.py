from __future__ import annotations

import json
from pathlib import Path

from apv.cli import main
from apv.sparql_client import SparqlClient


CANONICAL_PREFIXES = """
@prefix apv: <http://www.inf.ufrgs.br/ontologies/APV#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


def test_json_success_preserves_report_shape_and_uses_canonical_check_name(
    write_turtle, capsys
) -> None:
    path = write_turtle(
        CANONICAL_PREFIXES
        + """
        <https://example.org/ontology> a owl:Ontology ;
            apv:GlobalMinimumLanguageCoverage "en" ;
            apv:ClassMinAnnotationCoverage "rdfs:label" .
        <https://example.org/C> a owl:Class ; rdfs:label "Class"@en .
        """
    )

    exit_code = main(["--local", str(path), "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert set(report) == {"constraints", "violations"}
    global_result = next(
        result
        for result in report["violations"]
        if result["check"] == "GlobalMinimumLanguageCoverage"
    )
    assert set(global_result) == {"check", "parameter", "violations"}


def test_validation_violations_return_one(write_turtle, capsys) -> None:
    path = write_turtle(
        CANONICAL_PREFIXES
        + """
        <https://example.org/ontology> a owl:Ontology ;
            apv:ClassMinAnnotationCoverage "rdfs:label" .
        <https://example.org/C> a owl:Class .
        """
    )

    assert main(["--local", str(path), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert any(result["violations"] for result in report["violations"])


def test_text_output_uses_canonical_global_name(write_turtle, capsys) -> None:
    path = write_turtle(
        CANONICAL_PREFIXES
        + """
        <https://example.org/ontology> a owl:Ontology ;
            apv:GlobalMinimumLanguageCoverage "en" .
        """
    )

    assert main(["--local", str(path), "--text"]) == 0
    output = capsys.readouterr().out
    assert "apv:GlobalMinimumLanguageCoverage" in output
    assert "No GlobalMinimumLanguageCoverage violations found." in output


def test_invalid_constraint_returns_two(write_turtle, capsys) -> None:
    path = write_turtle(
        CANONICAL_PREFIXES
        + """
        <https://example.org/ontology> a owl:Ontology ;
            apv:ClassMinAnnotationCoverage "0^rdfs:label" .
        """
    )

    assert main(["--local", str(path), "--json"]) == 2
    assert "Cardinality must be positive" in capsys.readouterr().err


def test_missing_local_file_returns_two(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.ttl"

    assert main(["--local", str(missing)]) == 2
    assert "Error:" in capsys.readouterr().err


def test_remote_client_uses_credentials(monkeypatch) -> None:
    captured = {}

    class FakeStore:
        def __init__(self, endpoint, **kwargs):
            captured["endpoint"] = endpoint
            captured["kwargs"] = kwargs

        def setCredentials(self, user, password):
            captured["credentials"] = (user, password)

    monkeypatch.setattr("apv.sparql_client.SPARQLStore", FakeStore)
    SparqlClient.from_remote_endpoint(
        "https://example.org/sparql", user="alice", password="secret"
    )

    assert captured["endpoint"] == "https://example.org/sparql"
    assert captured["credentials"] == ("alice", "secret")


def test_apollo_examples_demonstrate_clean_and_failing_runs(capsys) -> None:
    examples = Path(__file__).parents[1] / "examples"

    assert main(["--local", str(examples / "apollo_sv.owl"), "--json"]) == 0
    original = json.loads(capsys.readouterr().out)
    assert not any(result["violations"] for result in original["violations"])

    assert main(
        ["--local", str(examples / "apollo_sv-edited.owl"), "--json"]
    ) == 1
    edited = json.loads(capsys.readouterr().out)
    violation_counts = {
        result["check"]: len(result["violations"])
        for result in edited["violations"]
        if result["violations"]
    }
    assert violation_counts == {
        "GlobalMinimumLanguageCoverage": 2485,
        "ClassMinAnnotationCoverage": 1947,
        "RelationMinAnnotationCoverage": 547,
        "InstanceMinAnnotationCoverage": 25,
        "MinAnnotationLength": 22,
        "MaxAnnotationLength": 10,
        "AnnotationRegularExpression": 113,
    }
