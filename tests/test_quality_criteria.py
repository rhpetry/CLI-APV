from __future__ import annotations

import pytest
from rdflib import Graph

from apv.quality_criteria import (
    CANONICAL_APV_NAMESPACE,
    parse_annotation_coverage,
    retrieve_class_annotation_coverage,
    retrieve_class_uri_formation_rule,
    retrieve_annotation_regular_expression,
    retrieve_instance_annotation_coverage,
    retrieve_instance_of_annotation_coverage,
    retrieve_instance_uri_formation_rule,
    retrieve_language_tags,
    retrieve_max_annotation_length,
    retrieve_min_annotation_length,
    retrieve_relation_annotation_coverage,
    retrieve_relation_uri_formation_rule,
)
from apv.sparql_client import SparqlClient


def client_for(turtle: str) -> SparqlClient:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return SparqlClient(local_graph=graph)


def test_retrieves_canonical_constraints_and_expands_prefixes() -> None:
    client = client_for(
        f"""
        @prefix apv: <{CANONICAL_APV_NAMESPACE}> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <https://example.org/ontology> a owl:Ontology ;
            apv:GlobalMinimumLanguageCoverage "pt-BR en" ;
            apv:ClassURIFormationRule "https://example.org/C[0-9]+" ;
            apv:ClassMinAnnotationCoverage "rdfs:label 2^skos:example" .
        """
    )

    assert retrieve_language_tags(client) == ["pt-BR", "en"]
    assert retrieve_class_uri_formation_rule(client) == "https://example.org/C[0-9]+"
    assert retrieve_class_annotation_coverage(client) == [
        ("http://www.w3.org/2000/01/rdf-schema#label", 1),
        ("http://www.w3.org/2004/02/skos/core#example", 2),
    ]


def test_accepts_legacy_input_aliases() -> None:
    client = client_for(
        """
        @prefix apv: <http://inf.ufrgs.br/ontologies/apv#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <https://example.org/ontology> a owl:Ontology ;
            apv:GlobalMinLanguageCoverage "en" ;
            apv:ClassMinAnnotationCoverage "rdfs:label" .
        """
    )

    assert retrieve_language_tags(client) == ["en"]
    assert retrieve_class_annotation_coverage(client) == [
        ("http://www.w3.org/2000/01/rdf-schema#label", 1)
    ]


def test_coverage_parser_accepts_full_iris_with_fragments() -> None:
    assert parse_annotation_coverage(
        "2^https://example.org/vocabulary#description", "coverage"
    ) == [("https://example.org/vocabulary#description", 2)]


@pytest.mark.parametrize("token", ["0^rdfs:label", "2ˆrdfs:label", "unknown:label"])
def test_coverage_parser_rejects_invalid_tokens(token: str) -> None:
    with pytest.raises(ValueError):
        parse_annotation_coverage(token, "coverage")


def test_rejects_invalid_language_tag() -> None:
    client = client_for(
        f"""
        @prefix apv: <{CANONICAL_APV_NAMESPACE}> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <https://example.org/ontology> a owl:Ontology ;
            apv:GlobalMinimumLanguageCoverage "not_a_language" .
        """
    )
    with pytest.raises(ValueError, match="Invalid language tag"):
        retrieve_language_tags(client)


def test_retrieves_positive_annotation_lengths() -> None:
    client = client_for(
        f"""
        @prefix apv: <{CANONICAL_APV_NAMESPACE}> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        ex:note a owl:AnnotationProperty ;
            apv:MinAnnotationLength 2 ;
            apv:MaxAnnotationLength 10 .
        """
    )
    assert retrieve_min_annotation_length(client) == [("https://example.org/note", 2)]
    assert retrieve_max_annotation_length(client) == [("https://example.org/note", 10)]


def test_retrieves_all_remaining_constraint_types() -> None:
    client = client_for(
        f"""
        @prefix apv: <{CANONICAL_APV_NAMESPACE}> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix ex: <https://example.org/> .
        <https://example.org/ontology> a owl:Ontology ;
            apv:RelationURIFormationRule "https://example.org/relation/[a-z]+" ;
            apv:InstanceURIFormationRule "https://example.org/instance/[a-z]+" ;
            apv:RelationMinAnnotationCoverage "rdfs:label" ;
            apv:InstanceMinAnnotationCoverage "2^skos:example" .
        ex:note a owl:AnnotationProperty ;
            apv:AnnotationRegularExpression "[A-Z]+" .
        ex:Class a owl:Class ;
            apv:InstanceOfMinAnnotationCoverage "ex:note" .
        """
    )

    assert retrieve_relation_uri_formation_rule(client) == "https://example.org/relation/[a-z]+"
    assert retrieve_instance_uri_formation_rule(client) == "https://example.org/instance/[a-z]+"
    assert retrieve_relation_annotation_coverage(client) == [
        ("http://www.w3.org/2000/01/rdf-schema#label", 1)
    ]
    assert retrieve_instance_annotation_coverage(client) == [
        ("http://www.w3.org/2004/02/skos/core#example", 2)
    ]
    assert retrieve_annotation_regular_expression(client) == [
        ("https://example.org/note", "[A-Z]+")
    ]
    assert retrieve_instance_of_annotation_coverage(client) == [
        ("https://example.org/Class", [("https://example.org/note", 1)])
    ]
