"""Quality testing functions for OWL ontologies."""

import re
from typing import List, Tuple

from apv.quality_criteria import resolve_configured_iri
from apv.sparql_client import SparqlClient


def normalize_iri(iri: str) -> str:
    """Return a validated SPARQL IRI reference."""
    return f"<{resolve_configured_iri(iri)}>"


def _resource_iri(iri: str) -> str:
    """Validate an IRI read from RDF before interpolating it into SPARQL."""
    return normalize_iri(iri)


def _count_annotation_values(
    client: SparqlClient,
    subject_iri: str,
    annotation_iri: str,
    language_tag: str | None = None,
) -> int:
    language_filter = ""
    if language_tag is not None:
        language_filter = f'FILTER(LCASE(LANG(?value)) = "{language_tag.lower()}")'
    query = f"""
        SELECT (COUNT(?value) AS ?count) WHERE {{
            {_resource_iri(subject_iri)} {normalize_iri(annotation_iri)} ?value .
            {language_filter}
        }}
    """
    results = list(client.query(query))
    return int(results[0][0]) if results else 0


def _named_resources(client: SparqlClient, query: str) -> list[str]:
    return list(dict.fromkeys(str(row[0]) for row in client.query(query)))


def _class_iris(client: SparqlClient) -> list[str]:
    return _named_resources(
        client,
        """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?resource WHERE {
            ?resource a owl:Class .
            FILTER(!isBlank(?resource))
        }
        """,
    )


def _relation_iris(client: SparqlClient) -> list[str]:
    return _named_resources(
        client,
        """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?resource WHERE {
            VALUES ?type { owl:ObjectProperty owl:DatatypeProperty owl:AnnotationProperty }
            ?resource a ?type .
            FILTER(!isBlank(?resource))
        }
        """,
    )


def _instance_iris(client: SparqlClient) -> list[str]:
    return _named_resources(
        client,
        """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?resource WHERE {
            ?resource rdf:type ?class .
            ?class a owl:Class .
            FILTER(!isBlank(?resource))
        }
        """,
    )


def check_class_uri_formation_rule(client: SparqlClient, class_uri_formation_rule: str | None) -> List[str]:
    """Return class URI violations for owl:Class IRIs that do not match the pattern."""
    if not class_uri_formation_rule:
        return []

    try:
        pattern = re.compile(class_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid class URI formation regex: {class_uri_formation_rule} ({err})")

    violations: List[str] = []
    for class_uri in _class_iris(client):
        if not pattern.fullmatch(class_uri):
            violations.append(class_uri)

    return violations


def check_relation_uri_formation_rule(client: SparqlClient, relation_uri_formation_rule: str | None) -> List[str]:
    """Return relation URI violations for owl:ObjectProperty/owl:DatatypeProperty IRIs that do not match the pattern."""
    if not relation_uri_formation_rule:
        return []

    try:
        pattern = re.compile(relation_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid relation URI formation regex: {relation_uri_formation_rule} ({err})")

    violations: List[str] = []
    for relation_uri in _relation_iris(client):
        if not pattern.fullmatch(relation_uri):
            violations.append(relation_uri)

    return violations


def check_instance_uri_formation_rule(client: SparqlClient, instance_uri_formation_rule: str | None) -> List[str]:
    """Return instance URI violations for individual IRIs that do not match the pattern."""
    if not instance_uri_formation_rule:
        return []

    try:
        pattern = re.compile(instance_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid instance URI formation regex: {instance_uri_formation_rule} ({err})")

    violations: List[str] = []
    for instance_uri in _instance_iris(client):
        if not pattern.fullmatch(instance_uri):
            violations.append(instance_uri)

    return violations


def check_global_minimum_language_coverage(
    client: SparqlClient,
    language_tags: list[str],
    class_requirements: list[tuple[str, int]],
    relation_requirements: list[tuple[str, int]],
    instance_requirements: list[tuple[str, int]],
    instance_of_requirements: list[tuple[str, list[tuple[str, int]]]],
) -> list[tuple[str, str]]:
    """Check required languages only for properties governed by APV coverage rules."""
    if not language_tags:
        return []

    targets: set[tuple[str, str]] = set()
    for subject in _class_iris(client):
        targets.update((subject, property_iri) for property_iri, _ in class_requirements)
    for subject in _relation_iris(client):
        targets.update((subject, property_iri) for property_iri, _ in relation_requirements)
    for subject in _instance_iris(client):
        targets.update((subject, property_iri) for property_iri, _ in instance_requirements)
    for class_iri, requirements in instance_of_requirements:
        instances = _named_resources(
            client,
            f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?resource WHERE {{
                ?resource rdf:type {_resource_iri(class_iri)} .
                FILTER(!isBlank(?resource))
            }}
            """,
        )
        for subject in instances:
            targets.update((subject, property_iri) for property_iri, _ in requirements)

    violations: list[tuple[str, str]] = []
    for subject_iri, annotation_iri in sorted(targets):
        for language_tag in language_tags:
            if _count_annotation_values(
                client, subject_iri, annotation_iri, language_tag
            ) == 0:
                violations.append(
                    (
                        subject_iri,
                        f"Annotation {annotation_iri} is missing required language "
                        f"{language_tag}",
                    )
                )
    return violations


def check_class_min_annotation_coverage(client: SparqlClient, language_tags: List[str], class_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return class annotation coverage violations checking exact cardinality per language."""
    if not class_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    for class_uri in _class_iris(client):

        # For each required annotation property, check exact cardinality
        for annotation_prop, required_cardinality in class_annotation_cardinalities:
            if language_tags:
                # Check cardinality per language
                for required_lang in language_tags:
                    count = _count_annotation_values(
                        client, class_uri, annotation_prop, required_lang
                    )

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((class_uri, violation_msg))
            else:
                # Check total cardinality without language filtering
                count = _count_annotation_values(client, class_uri, annotation_prop)

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((class_uri, violation_msg))

    return violations


def check_relation_min_annotation_coverage(client: SparqlClient, language_tags: List[str], relation_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return relation annotation coverage violations checking exact cardinality per language."""
    if not relation_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    for relation_uri in _relation_iris(client):

        for annotation_prop, required_cardinality in relation_annotation_cardinalities:
            if language_tags:
                for required_lang in language_tags:
                    count = _count_annotation_values(
                        client, relation_uri, annotation_prop, required_lang
                    )

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((relation_uri, violation_msg))
            else:
                count = _count_annotation_values(client, relation_uri, annotation_prop)

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((relation_uri, violation_msg))

    return violations


def check_instance_min_annotation_coverage(client: SparqlClient, language_tags: List[str], instance_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return instance annotation coverage violations checking exact cardinality per language."""
    if not instance_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    for instance_uri in _instance_iris(client):

        for annotation_prop, required_cardinality in instance_annotation_cardinalities:
            if language_tags:
                for required_lang in language_tags:
                    count = _count_annotation_values(
                        client, instance_uri, annotation_prop, required_lang
                    )

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((instance_uri, violation_msg))
            else:
                count = _count_annotation_values(client, instance_uri, annotation_prop)

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((instance_uri, violation_msg))

    return violations


def check_min_annotation_length(
    client: SparqlClient,
    min_annotation_lengths: List[Tuple[str, int]],
) -> List[Tuple[str, str]]:
    """Return annotation length violations for values shorter than the configured minimum."""
    if not min_annotation_lengths:
        return []

    violations: List[Tuple[str, str]] = []

    for annotation_property, min_length in min_annotation_lengths:
        normalized_prop = normalize_iri(annotation_property)
        query = f"""
            SELECT ?subject ?value WHERE {{
                ?subject {normalized_prop} ?value .
            }}
        """

        for row in client.query(query):
            subject_uri = str(row[0])
            annotation_value = str(row[1])
            annotation_length = len(annotation_value)

            if annotation_length < min_length:
                violation_msg = (
                    f"Annotation {annotation_property} value '{annotation_value}' "
                    f"has {annotation_length} characters, requires at least {min_length}"
                )
                violations.append((subject_uri, violation_msg))

    return violations


def check_max_annotation_length(
    client: SparqlClient,
    max_annotation_lengths: List[Tuple[str, int]],
) -> List[Tuple[str, str]]:
    """Return annotation length violations for values longer than the configured maximum."""
    if not max_annotation_lengths:
        return []

    violations: List[Tuple[str, str]] = []

    for annotation_property, max_length in max_annotation_lengths:
        normalized_prop = normalize_iri(annotation_property)
        query = f"""
            SELECT ?subject ?value WHERE {{
                ?subject {normalized_prop} ?value .
            }}
        """

        for row in client.query(query):
            subject_uri = str(row[0])
            annotation_value = str(row[1])
            annotation_length = len(annotation_value)

            if annotation_length > max_length:
                violation_msg = (
                    f"Annotation {annotation_property} value '{annotation_value}' "
                    f"has {annotation_length} characters, requires at most {max_length}"
                )
                violations.append((subject_uri, violation_msg))

    return violations


def check_annotation_regular_expression(
    client: SparqlClient,
    annotation_regex_expressions: List[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    """Return annotation value violations for values that do not match the configured regex."""
    if not annotation_regex_expressions:
        return []

    violations: List[Tuple[str, str]] = []

    for annotation_property, regex_pattern in annotation_regex_expressions:
        try:
            pattern = re.compile(regex_pattern)
        except re.error as err:
            raise ValueError(
                f"Invalid annotation regular expression regex: {regex_pattern} ({err})"
            )

        normalized_prop = normalize_iri(annotation_property)
        query = f"""
            SELECT ?subject ?value WHERE {{
                ?subject {normalized_prop} ?value .
            }}
        """

        for row in client.query(query):
            subject_uri = str(row[0])
            annotation_value = str(row[1])

            if not pattern.fullmatch(annotation_value):
                violation_msg = (
                    f"Annotation {annotation_property} value '{annotation_value}' "
                    f"does not match regex '{regex_pattern}'"
                )
                violations.append((subject_uri, violation_msg))

    return violations


def check_instance_of_min_annotation_coverage(
    client: SparqlClient,
    language_tags: List[str],
    instance_coverage_requirements: List[Tuple[str, List[Tuple[str, int]]]],
) -> List[Tuple[str, str]]:
    """Return instance coverage violations for class-scoped mandatory annotations."""
    if not instance_coverage_requirements:
        return []

    violations: List[Tuple[str, str]] = []

    for class_uri, required_annotations in instance_coverage_requirements:
        instance_query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?instance WHERE {{
                ?instance rdf:type {_resource_iri(class_uri)} .
                FILTER(!isBlank(?instance))
            }}
        """

        for row in client.query(instance_query):
            instance_uri = str(row[0])

            for annotation_prop, required_cardinality in required_annotations:
                if language_tags:
                    for required_lang in language_tags:
                        count = _count_annotation_values(
                            client, instance_uri, annotation_prop, required_lang
                        )

                        if count != required_cardinality:
                            violation_msg = (
                                f"Instance of {class_uri} is missing required annotation "
                                f"{annotation_prop} for language {required_lang}: "
                                f"has {count} values, requires exactly {required_cardinality}"
                            )
                            violations.append((instance_uri, violation_msg))
                else:
                    count = _count_annotation_values(
                        client, instance_uri, annotation_prop
                    )

                    if count != required_cardinality:
                        violation_msg = (
                            f"Instance of {class_uri} is missing required annotation "
                            f"{annotation_prop}: has {count} values, requires exactly "
                            f"{required_cardinality}"
                        )
                        violations.append((instance_uri, violation_msg))

    return violations
