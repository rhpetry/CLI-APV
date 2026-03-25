"""Quality testing functions for OWL ontologies."""

import re
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Namespace

from apv.sparql_client import SparqlClient


OWL = Namespace("http://www.w3.org/2002/07/owl#")
APV = Namespace("http://inf.ufrgs.br/ontologies/apv#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


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

