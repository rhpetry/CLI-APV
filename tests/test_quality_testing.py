from __future__ import annotations

from rdflib import Graph

from apv.quality_testing import (
    check_annotation_regular_expression,
    check_class_min_annotation_coverage,
    check_class_uri_formation_rule,
    check_global_minimum_language_coverage,
    check_instance_min_annotation_coverage,
    check_instance_of_min_annotation_coverage,
    check_instance_uri_formation_rule,
    check_max_annotation_length,
    check_min_annotation_length,
    check_relation_min_annotation_coverage,
    check_relation_uri_formation_rule,
)
from apv.sparql_client import SparqlClient


def client_for(turtle: str) -> SparqlClient:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return SparqlClient(local_graph=graph)


def test_coverage_uses_exact_cardinality_per_language_case_insensitively() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        <https://example.org/C1> a owl:Class ;
            rdfs:label "One"@pt-BR, "Two"@pt-br .
        """
    )
    requirement = [("http://www.w3.org/2000/01/rdf-schema#label", 1)]

    violations = check_class_min_annotation_coverage(client, ["pt-BR"], requirement)

    assert len(violations) == 1
    assert "has 2 values, requires exactly 1" in violations[0][1]


def test_annotation_regex_requires_whole_value_match() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        ex:code a owl:AnnotationProperty .
        ex:item ex:code "prefix-123-suffix" .
        """
    )

    violations = check_annotation_regular_expression(
        client, [("https://example.org/code", "[0-9]+")]
    )

    assert len(violations) == 1


def test_relation_scope_matches_web_application() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        ex:object a owl:ObjectProperty .
        ex:data a owl:DatatypeProperty .
        ex:annotation a owl:AnnotationProperty .
        """
    )

    violations = check_relation_uri_formation_rule(
        client, r"https://example\.org/allowed"
    )

    assert set(violations) == {
        "https://example.org/object",
        "https://example.org/data",
        "https://example.org/annotation",
    }


def test_global_language_check_is_limited_to_apv_constrained_properties() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <https://example.org/> .
        ex:C a owl:Class ;
            rdfs:label "Label"@en ;
            ex:unconstrained "Sem tradução"@pt-BR .
        """
    )

    violations = check_global_minimum_language_coverage(
        client,
        ["en", "pt-BR"],
        [("http://www.w3.org/2000/01/rdf-schema#label", 1)],
        [],
        [],
        [],
    )

    assert violations == [
        (
            "https://example.org/C",
            "Annotation http://www.w3.org/2000/01/rdf-schema#label is missing required language pt-BR",
        )
    ]


def test_uri_checks_cover_classes_and_instances() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        ex:WrongClass a owl:Class .
        ex:WrongInstance a ex:WrongClass .
        """
    )

    assert check_class_uri_formation_rule(
        client, r"https://example\.org/C[0-9]+"
    ) == ["https://example.org/WrongClass"]
    assert check_instance_uri_formation_rule(
        client, r"https://example\.org/I[0-9]+"
    ) == ["https://example.org/WrongInstance"]


def test_relation_and_instance_coverage_and_class_scoped_coverage() -> None:
    label = "http://www.w3.org/2000/01/rdf-schema#label"
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <https://example.org/> .
        ex:relation a owl:ObjectProperty ; rdfs:label "Relation"@en .
        ex:Class a owl:Class .
        ex:instance a ex:Class ; rdfs:label "Instance"@en .
        """
    )

    assert check_relation_min_annotation_coverage(client, ["en"], [(label, 1)]) == []
    assert check_instance_min_annotation_coverage(client, ["en"], [(label, 1)]) == []
    assert check_instance_of_min_annotation_coverage(
        client, ["en"], [("https://example.org/Class", [(label, 1)])]
    ) == []


def test_minimum_and_maximum_annotation_lengths() -> None:
    client = client_for(
        """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        ex:note a owl:AnnotationProperty .
        ex:item ex:note "four" .
        """
    )

    assert len(check_min_annotation_length(client, [("https://example.org/note", 5)])) == 1
    assert len(check_max_annotation_length(client, [("https://example.org/note", 3)])) == 1
