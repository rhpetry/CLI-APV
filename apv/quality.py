"""Quality criteria checks for OWL ontologies."""

from typing import Iterable, List, Optional

import language_tags
from rdflib import Namespace, RDF

from apv.sparql_client import SparqlClient


OWL = Namespace("http://www.w3.org/2002/07/owl#")
APV = Namespace("http://inf.ufrgs.br/ontologies/apv#")


def check_global_min_language_coverage(client: SparqlClient) -> Optional[List[str]]:
    """Check if ontology has GlobalMinLanguageCoverage and validate IANA language tags.

    Args:
        client: A SparqlClient instance for querying the ontology.

    Returns:
        A list of valid IANA language tags if all tags are valid, None otherwise.
    """
    query = """
        PREFIX owl: <{owl}>
        PREFIX apv: <{apv}>

        SELECT ?gmlc WHERE {{
            ?o a owl:Ontology ;
                apv:GlobalMinLanguageCoverage ?gmlc .
        }}
    """.format(owl=OWL, apv=APV)

    results = client.query(query)

    # Convert results to list to check if empty
    results_list = list(results)
    if not results_list:
        return None

    # Get the first result
    gmlc_value = str(results_list[0][0])

    # Split by spaces to get individual language tags
    language_tags = gmlc_value.split()

    # Validate each tag against IANA language tags
    for tag in language_tags:
        # language_tags.check() returns the tag if valid, or None if invalid
        print(f"Checking language tag: {tag}")

    # Check if ontology has annotations in all language_tags
    missing_annotations = []
    query = """
        PREFIX owl: <{owl}>
        PREFIX apv: <{apv}>

        SELECT ?individual ?annotation ?dt WHERE {{
            BIND(<https://www.inf.ufrgs.br/ontologies/o3po#Sensor> AS ?individual)
            ?individual ?annotation ?value .
            FILTER (isLiteral(?value))
            FILTER (datatype(?value) = xsd:string || datatype(?value) = rdf:langString)
            BIND(lang(?value) AS ?lang)
            BIND(datatype(?value) AS ?dt)
        }} LIMIT 10
    """.format(owl=OWL, apv=APV, tags=", ".join(language_tags))

    print(query)
    results = client.query(query)
    
    # Convert results to list to check if empty
    results_list = list(results)
    print(len(results_list))
    if not results_list:
        return None
    
    # Get the first result
    for result in results_list:
        print(f"Found result: {result[0]} {result[1]} '{result[2]}'")
    # Return list of missing annotations for each language tag, or empty list if all tags are covered
    return 

