"""Retrieve and validate APV constraints from OWL ontologies."""

from __future__ import annotations

import re
from collections.abc import Iterable

import language_tags as language_tags_lib

from apv.sparql_client import SparqlClient


CANONICAL_APV_NAMESPACE = "http://www.inf.ufrgs.br/ontologies/APV#"
LEGACY_APV_NAMESPACE = "http://inf.ufrgs.br/ontologies/apv#"

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "apv": CANONICAL_APV_NAMESPACE,
}

_UNSAFE_IRI_CHARACTERS = re.compile(r'[\x00-\x20<>"{}|^`]')


def resolve_configured_iri(
    value: str, prefixes: dict[str, str] | None = None
) -> str:
    """Expand a supported prefixed name or validate an absolute IRI."""
    value = value.strip()
    if not value:
        raise ValueError("Annotation property IRI must not be empty")

    available_prefixes = PREFIXES | (prefixes or {})
    prefix, separator, local_name = value.partition(":")
    if separator and prefix in available_prefixes:
        if not local_name:
            raise ValueError(f"Invalid prefixed IRI: '{value}'")
        value = f"{available_prefixes[prefix]}{local_name}"
    elif separator and "://" not in value:
        raise ValueError(
            f"Unsupported prefixed IRI '{value}'. Use a full IRI or one of: "
            f"{', '.join(available_prefixes)}."
        )
    elif not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
        raise ValueError(
            f"Unsupported prefixed IRI '{value}'. Use a full IRI or one of: "
            f"{', '.join(available_prefixes)}."
        )

    if _UNSAFE_IRI_CHARACTERS.search(value):
        raise ValueError(f"Invalid IRI in APV constraint: '{value}'")
    return value


def _first_value(client: SparqlClient, predicates: Iterable[str]) -> str | None:
    predicate_values = " ".join(
        f"(<{predicate}> {priority})"
        for priority, predicate in enumerate(predicates)
    )
    query = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?value WHERE {{
            ?ontology a owl:Ontology ;
                      ?predicate ?value .
            VALUES (?predicate ?priority) {{ {predicate_values} }}
        }}
        ORDER BY ?priority
        LIMIT 1
    """
    results = list(client.query(query))
    return str(results[0][0]).strip() if results else None


def _ontology_predicates(local_name: str, *legacy_names: str) -> list[str]:
    predicates = [f"{CANONICAL_APV_NAMESPACE}{local_name}"]
    predicates.extend(f"{LEGACY_APV_NAMESPACE}{name}" for name in (legacy_names or (local_name,)))
    return predicates


def retrieve_language_tags(client: SparqlClient) -> list[str]:
    """Retrieve the required IANA language tags."""
    raw = _first_value(
        client,
        _ontology_predicates(
            "GlobalMinimumLanguageCoverage", "GlobalMinLanguageCoverage"
        ),
    ) or ""
    tags = raw.split()
    for tag in tags:
        if not language_tags_lib.tags.check(tag):
            raise ValueError(
                "Invalid language tag in GlobalMinimumLanguageCoverage: "
                f"'{tag}'"
            )
    return tags


def _retrieve_regex_rule(client: SparqlClient, local_name: str) -> str | None:
    value = _first_value(client, _ontology_predicates(local_name))
    if value is None or not value:
        return None
    try:
        re.compile(value)
    except re.error as error:
        raise ValueError(
            f"Invalid regex pattern for {local_name}: '{value}' - {error}"
        ) from error
    return value


def retrieve_class_uri_formation_rule(client: SparqlClient) -> str | None:
    return _retrieve_regex_rule(client, "ClassURIFormationRule")


def retrieve_relation_uri_formation_rule(client: SparqlClient) -> str | None:
    return _retrieve_regex_rule(client, "RelationURIFormationRule")


def retrieve_instance_uri_formation_rule(client: SparqlClient) -> str | None:
    return _retrieve_regex_rule(client, "InstanceURIFormationRule")


def parse_annotation_coverage(
    raw: str, label: str, prefixes: dict[str, str] | None = None
) -> list[tuple[str, int]]:
    """Parse whitespace-separated ``[cardinality^]property`` tokens."""
    requirements: list[tuple[str, int]] = []
    for token in raw.split():
        cardinality_text, separator, property_name = token.partition("^")
        if separator:
            if not cardinality_text.isdigit() or not property_name:
                raise ValueError(f"Invalid format for {label}: '{token}'")
            cardinality = int(cardinality_text)
            if cardinality <= 0:
                raise ValueError(f"Cardinality must be positive for {label}: '{token}'")
        else:
            property_name = cardinality_text
            cardinality = 1
        try:
            property_iri = resolve_configured_iri(property_name, prefixes)
        except ValueError as error:
            raise ValueError(f"Invalid format for {label}: '{token}' ({error})") from error
        requirements.append((property_iri, cardinality))
    return requirements


def _retrieve_coverage(client: SparqlClient, local_name: str) -> list[tuple[str, int]]:
    raw = _first_value(client, _ontology_predicates(local_name)) or ""
    return parse_annotation_coverage(raw, local_name, _client_prefixes(client))


def _client_prefixes(client: SparqlClient) -> dict[str, str]:
    if client.local_graph is None:
        return {}
    return {
        prefix: str(namespace)
        for prefix, namespace in client.local_graph.namespaces()
        if prefix
    }


def retrieve_class_annotation_coverage(client: SparqlClient) -> list[tuple[str, int]]:
    return _retrieve_coverage(client, "ClassMinAnnotationCoverage")


def retrieve_relation_annotation_coverage(client: SparqlClient) -> list[tuple[str, int]]:
    return _retrieve_coverage(client, "RelationMinAnnotationCoverage")


def retrieve_instance_annotation_coverage(client: SparqlClient) -> list[tuple[str, int]]:
    return _retrieve_coverage(client, "InstanceMinAnnotationCoverage")


def _property_constraint_rows(
    client: SparqlClient, local_name: str
) -> list[tuple[str, str]]:
    predicate_order = _ontology_predicates(local_name)
    predicates = " ".join(f"<{predicate}>" for predicate in predicate_order)
    query = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?property ?predicate ?value WHERE {{
            ?property a owl:AnnotationProperty ;
                      ?predicate ?value .
            VALUES ?predicate {{ {predicates} }}
        }}
    """
    priority = {predicate: index for index, predicate in enumerate(predicate_order)}
    selected: dict[str, tuple[int, str]] = {}
    for row in client.query(query):
        property_iri = str(row[0]).strip()
        predicate = str(row[1]).strip()
        value = str(row[2]).strip()
        candidate = (priority[predicate], value)
        if property_iri not in selected or candidate[0] < selected[property_iri][0]:
            selected[property_iri] = candidate
    return [(property_iri, value) for property_iri, (_, value) in selected.items()]


def _retrieve_annotation_lengths(
    client: SparqlClient, local_name: str
) -> list[tuple[str, int]]:
    requirements: list[tuple[str, int]] = []
    for property_iri, raw_length in _property_constraint_rows(client, local_name):
        if not raw_length:
            continue
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ValueError(
                f"Invalid length for {local_name} on {property_iri}: '{raw_length}'"
            ) from error
        if length <= 0:
            raise ValueError(
                f"Length must be positive for {local_name} on {property_iri}: "
                f"'{raw_length}'"
            )
        requirements.append((resolve_configured_iri(property_iri), length))
    return requirements


def retrieve_min_annotation_length(client: SparqlClient) -> list[tuple[str, int]]:
    return _retrieve_annotation_lengths(client, "MinAnnotationLength")


def retrieve_max_annotation_length(client: SparqlClient) -> list[tuple[str, int]]:
    return _retrieve_annotation_lengths(client, "MaxAnnotationLength")


def retrieve_annotation_regular_expression(
    client: SparqlClient,
) -> list[tuple[str, str]]:
    requirements: list[tuple[str, str]] = []
    for property_iri, pattern in _property_constraint_rows(
        client, "AnnotationRegularExpression"
    ):
        if not pattern:
            continue
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(
                "Invalid regex pattern for AnnotationRegularExpression on "
                f"{property_iri}: '{pattern}' - {error}"
            ) from error
        requirements.append((resolve_configured_iri(property_iri), pattern))
    return requirements


def retrieve_instance_of_annotation_coverage(
    client: SparqlClient,
) -> list[tuple[str, list[tuple[str, int]]]]:
    predicate_order = _ontology_predicates("InstanceOfMinAnnotationCoverage")
    predicates = " ".join(f"<{predicate}>" for predicate in predicate_order)
    query = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?class ?predicate ?value WHERE {{
            ?class a owl:Class ;
                   ?predicate ?value .
            VALUES ?predicate {{ {predicates} }}
        }}
    """
    priority = {predicate: index for index, predicate in enumerate(predicate_order)}
    selected: dict[str, tuple[int, str]] = {}
    for row in client.query(query):
        class_iri = resolve_configured_iri(str(row[0]).strip())
        predicate = str(row[1]).strip()
        value = str(row[2]).strip()
        candidate = (priority[predicate], value)
        if class_iri not in selected or candidate[0] < selected[class_iri][0]:
            selected[class_iri] = candidate

    requirements = []
    for class_iri, (_, raw_coverage) in selected.items():
        coverage = parse_annotation_coverage(
            raw_coverage,
            f"InstanceOfMinAnnotationCoverage on {class_iri}",
            _client_prefixes(client),
        )
        requirements.append((class_iri, coverage))
    return requirements
