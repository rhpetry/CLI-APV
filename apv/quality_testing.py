"""Quality testing functions for OWL ontologies."""

import re
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Namespace

from apv.sparql_client import SparqlClient


OWL = Namespace("http://www.w3.org/2002/07/owl#")
APV = Namespace("http://inf.ufrgs.br/ontologies/apv#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def normalize_iri(iri: str) -> str:
    """Normalize an IRI for SPARQL: wrap full URIs with <>, keep prefixes as-is."""
    if not iri:
        return iri
    
    # Full URI form (contains ://) - wrap with < >
    if "://" in iri:
        return f"<{iri}>"
    
    # Prefix form (e.g., rdfs:label) - return as-is for SPARQL PREFIX resolution
    return iri


def check_class_uri_formation_rule(client: SparqlClient, class_uri_formation_rule: str) -> List[str]:
    """Return class URI violations for owl:Class IRIs that do not match the pattern."""
    if not class_uri_formation_rule:
        return []

    try:
        pattern = re.compile(class_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid class URI formation regex: {class_uri_formation_rule} ({err})")

    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?class WHERE {
            ?class a owl:Class .
            filter(!isBlank(?class))
        }
    """
    violations: List[str] = []
    for row in client.query(query):
        class_uri = str(row[0])
        if not pattern.fullmatch(class_uri):
            violations.append(class_uri)

    return violations


def check_relation_uri_formation_rule(client: SparqlClient, relation_uri_formation_rule: str) -> List[str]:
    """Return relation URI violations for owl:ObjectProperty/owl:DatatypeProperty IRIs that do not match the pattern."""
    if not relation_uri_formation_rule:
        return []

    try:
        pattern = re.compile(relation_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid relation URI formation regex: {relation_uri_formation_rule} ({err})")

    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?relation WHERE {
            VALUES ?type { owl:ObjectProperty owl:DatatypeProperty owl:AnnotationProperty}
            ?relation a ?type .
            FILTER(!isBlank(?relation))
        }
    """
    violations: List[str] = []
    for row in client.query(query):
        relation_uri = str(row[0])
        if not pattern.fullmatch(relation_uri):
            violations.append(relation_uri)

    return violations


def check_instance_uri_formation_rule(client: SparqlClient, instance_uri_formation_rule: str) -> List[str]:
    """Return instance URI violations for individual IRIs that do not match the pattern."""
    if not instance_uri_formation_rule:
        return []

    try:
        pattern = re.compile(instance_uri_formation_rule)
    except re.error as err:
        raise ValueError(f"Invalid instance URI formation regex: {instance_uri_formation_rule} ({err})")

    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?instance WHERE {
            ?class rdf:type owl:Class .
            ?instance rdf:type ?class .
            FILTER(!isBlank(?instance))
        }
    """
    violations: List[str] = []
    for row in client.query(query):
        instance_uri = str(row[0])
        if not pattern.fullmatch(instance_uri):
            violations.append(instance_uri)

    return violations


def check_class_min_annotation_coverage(client: SparqlClient, language_tags: List[str], class_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return class annotation coverage violations checking exact cardinality per language."""
    if not class_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    # Get all classes
    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?class WHERE {
            ?class a owl:Class .
            FILTER(!isBlank(?class))
        }
    """

    for row in client.query(query):
        class_uri = str(row[0])

        # For each required annotation property, check exact cardinality
        for annotation_prop, required_cardinality in class_annotation_cardinalities:
            # Normalize the annotation property IRI
            normalized_prop = normalize_iri(annotation_prop)
            
            if language_tags:
                # Check cardinality per language
                for required_lang in language_tags:
                    lang_query = f"""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        SELECT (COUNT(?value) as ?count) WHERE {{
                            <{class_uri}> {normalized_prop} ?value .
                            FILTER(lang(?value) = "{required_lang}")
                        }}
                    """
                    
                    count_result = list(client.query(lang_query))
                    count = int(count_result[0][0]) if count_result else 0

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((class_uri, violation_msg))
            else:
                # Check total cardinality without language filtering
                check_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    SELECT (COUNT(?value) as ?count) WHERE {{
                        <{class_uri}> {normalized_prop} ?value .
                    }}
                """
                
                count_result = list(client.query(check_query))
                count = int(count_result[0][0]) if count_result else 0

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((class_uri, violation_msg))

    return violations


def check_relation_min_annotation_coverage(client: SparqlClient, language_tags: List[str], relation_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return relation annotation coverage violations checking exact cardinality per language."""
    if not relation_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    # Get all relation properties (ObjectProperty, DatatypeProperty, AnnotationProperty)
    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?relation WHERE {
            VALUES ?type { owl:ObjectProperty owl:DatatypeProperty owl:AnnotationProperty }
            ?relation a ?type .
            FILTER(!isBlank(?relation))
        }
    """

    for row in client.query(query):
        relation_uri = str(row[0])

        for annotation_prop, required_cardinality in relation_annotation_cardinalities:
            normalized_prop = normalize_iri(annotation_prop)

            if language_tags:
                for required_lang in language_tags:
                    lang_query = f"""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        SELECT (COUNT(?value) as ?count) WHERE {{
                            <{relation_uri}> {normalized_prop} ?value .
                            FILTER(lang(?value) = \"{required_lang}\")
                        }}
                    """

                    count_result = list(client.query(lang_query))
                    count = int(count_result[0][0]) if count_result else 0

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((relation_uri, violation_msg))
            else:
                check_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    SELECT (COUNT(?value) as ?count) WHERE {{
                        <{relation_uri}> {normalized_prop} ?value .
                    }}
                """

                count_result = list(client.query(check_query))
                count = int(count_result[0][0]) if count_result else 0

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((relation_uri, violation_msg))

    return violations


def check_instance_min_annotation_coverage(client: SparqlClient, language_tags: List[str], instance_annotation_cardinalities: List[Tuple[str, int]]) -> List[Tuple[str, str]]:
    """Return instance annotation coverage violations checking exact cardinality per language."""
    if not instance_annotation_cardinalities:
        return []

    violations: List[Tuple[str, str]] = []

    # Get all instances
    query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?instance WHERE {
            ?instance rdf:type ?class .
            ?class a owl:Class .
            FILTER(!isBlank(?instance))
        }
    """

    for row in client.query(query):
        instance_uri = str(row[0])

        for annotation_prop, required_cardinality in instance_annotation_cardinalities:
            normalized_prop = normalize_iri(annotation_prop)

            if language_tags:
                for required_lang in language_tags:
                    lang_query = f"""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        SELECT (COUNT(?value) as ?count) WHERE {{
                            <{instance_uri}> {normalized_prop} ?value .
                            FILTER(lang(?value) = \"{required_lang}\")
                        }}
                    """

                    count_result = list(client.query(lang_query))
                    count = int(count_result[0][0]) if count_result else 0

                    if count != required_cardinality:
                        violation_msg = f"Annotation {annotation_prop} with language {required_lang} has {count} values, requires exactly {required_cardinality}"
                        violations.append((instance_uri, violation_msg))
            else:
                check_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    SELECT (COUNT(?value) as ?count) WHERE {{
                        <{instance_uri}> {normalized_prop} ?value .
                    }}
                """

                count_result = list(client.query(check_query))
                count = int(count_result[0][0]) if count_result else 0

                if count != required_cardinality:
                    violation_msg = f"Annotation {annotation_prop} has {count} values, requires exactly {required_cardinality}"
                    violations.append((instance_uri, violation_msg))

    return violations

