"""Quality criteria checks for OWL ontologies."""

from __future__ import annotations

from typing import Iterable, List

from rdflib import Namespace, RDF

from apv.sparql_client import SparqlClient


OWL = Namespace("http://www.w3.org/2002/07/owl#")


def get_distinct_annotation_properties(client: SparqlClient) -> List[str]:
    """Return all distinct annotation properties used in the ontology.

    This function runs a SPARQL query that finds all properties used in triples
    that are also declared as `owl:AnnotationProperty`.
    """

    query = """
        PREFIX rdf: <{rdf}>
        PREFIX owl: <{owl}>

        SELECT DISTINCT ?p WHERE {{
            ?s ?p ?o .
            ?p rdf:type owl:AnnotationProperty .
        }}
    """.format(rdf=RDF, owl=OWL)

    results = client.query(query)

    return [str(row[0]) for row in results]


def run_annotation_type_check(client: SparqlClient) -> List[str]:
    """Run the annotation property quality check and return the distinct list."""
    return get_distinct_annotation_properties(client)
