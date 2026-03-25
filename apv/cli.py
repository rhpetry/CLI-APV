"""Command-line interface for the APV ontology verification tool."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, List

from apv.quality_criteria import retrieve_language_tags, retrieve_class_annotation_coverage, retrieve_class_uri_formation_rule, retrieve_relation_uri_formation_rule, retrieve_instance_uri_formation_rule, retrieve_relation_annotation_coverage, retrieve_instance_annotation_coverage, retrieve_min_annotation_length, retrieve_max_annotation_length, retrieve_annotation_regular_expression, retrieve_instance_of_annotation_coverage
from apv.quality_testing import check_class_uri_formation_rule, check_relation_uri_formation_rule, check_instance_uri_formation_rule, check_class_min_annotation_coverage, check_relation_min_annotation_coverage, check_instance_min_annotation_coverage
from apv.sparql_client import SparqlClient


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apv",
        description=(
            "Verify OWL ontologies (RDF) by running SPARQL quality checks "
            "against a local file or a remote SPARQL endpoint."
        ),
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "-l",
        "--local",
        dest="local_file",
        help="Path to a local RDF file (e.g., .ttl, .rdf, .nt).",
    )
    source.add_argument(
        "-r",
        "--remote",
        dest="remote_endpoint",
        help="URL of a SPARQL endpoint to query.",
    )

    parser.add_argument(
        "--user",
        help="Username for the SPARQL endpoint (optional).",
    )
    parser.add_argument(
        "--password",
        help="Password for the SPARQL endpoint (optional).",
    )

    parser.add_argument(
        "--format",
        default="ttl",
        help="RDF serialization format when loading a local file (default: ttl).",
    )

    return parser


def _load_client(args: argparse.Namespace) -> SparqlClient:
    if args.local_file:
        return SparqlClient.from_local_file(args.local_file, format=args.format)

    return SparqlClient.from_remote_endpoint(
        args.remote_endpoint, user=args.user, password=args.password
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    client = _load_client(args)

    # Retrieve annotation quality parameters from the ontology
    # - ClassURIFormationRule
    class_uri_formation_rule = retrieve_class_uri_formation_rule(client)
    if class_uri_formation_rule:
        print("apv:ClassURIFormationRule requires the following URI pattern for Classes:")
        print("- ", class_uri_formation_rule)

        class_uri_violations = check_class_uri_formation_rule(client, class_uri_formation_rule)
        if class_uri_violations:
            print("Class URI formation violations found:")
            for v in class_uri_violations:
                print("- ", v)
        else:
            print("No ClassURIFormationRule violations found.")
    else:
        print("No ClassURIFormationRule statement found in ontology. Skipping class URI formation rule checks.")

    # - RelationURIFormationRule
    relation_uri_formation_rule = retrieve_relation_uri_formation_rule(client)
    if relation_uri_formation_rule:
        print("apv:RelationURIFormationRule requires the following URI pattern for Relations:")
        print("- ", relation_uri_formation_rule)

        relation_uri_violations = check_relation_uri_formation_rule(client, relation_uri_formation_rule)
        if relation_uri_violations:
            print("Relation URI formation violations found:")
            for v in relation_uri_violations:
                print("- ", v)
        else:
            print("No RelationURIFormationRule violations found.")
    else:
        print("No RelationURIFormationRule statement found in ontology. Skipping relation URI formation rule checks.")

    # - InstanceURIFormationRule
    instance_uri_formation_rule = retrieve_instance_uri_formation_rule(client)
    if instance_uri_formation_rule:
        print("apv:InstanceURIFormationRule requires the following URI pattern for Instances:")
        print("- ", instance_uri_formation_rule)

        instance_uri_violations = check_instance_uri_formation_rule(client, instance_uri_formation_rule)
        if instance_uri_violations:
            print("Instance URI formation violations found:")
            for v in instance_uri_violations:
                print("- ", v)
        else:
            print("No InstanceURIFormationRule violations found.")
    else:
        print("No InstanceURIFormationRule statement found in ontology. Skipping instance URI formation rule checks.")

    # - GlobalMinLanguageCoverage
    language_tags = retrieve_language_tags(client)
    if language_tags:
        print("apv:GlobalMinLanguageCoverage requires the following language tags:")
        for language_tag in language_tags:
            print("- ", language_tag)
    else:
        print("No GlobalMinLanguageCoverage statement found in ontology. Skipping language coverage checks.")

    # - ClassMinAnnotationCoverage
    class_annotation_cardinalities = retrieve_class_annotation_coverage(client)
    if class_annotation_cardinalities:
        print("apv:ClassMinAnnotationCoverage requires the following annotations:")
        for a, c in class_annotation_cardinalities:
            print("- ", c, a)
    else:
        print("No ClassMinAnnotationCoverage statement found in ontology. Skipping class annotation coverage checks.")

    # - RelationMinAnnotationCoverage
    relation_annotation_cardinalities = retrieve_relation_annotation_coverage(client)
    if relation_annotation_cardinalities:
        print("apv:RelationMinAnnotationCoverage requires the following annotations:")
        for a, c in relation_annotation_cardinalities:
            print("- ", c, a)
    else:
        print("No RelationMinAnnotationCoverage statement found in ontology. Skipping relation annotation coverage checks.")

    # - InstanceMinAnnotationCoverage
    instance_annotation_cardinalities = retrieve_instance_annotation_coverage(client)
    if instance_annotation_cardinalities:
        print("apv:InstanceMinAnnotationCoverage requires the following annotations:")
        for a, c in instance_annotation_cardinalities:
            print("- ", c, a)
    else:
        print("No InstanceMinAnnotationCoverage statement found in ontology. Skipping instance annotation coverage checks.")

    # - MinAnnotationLength
    min_annotation_lengths = retrieve_min_annotation_length(client)
    if min_annotation_lengths:
        print("apv:MinAnnotationLength constraints:")
        for annotation_property, min_length in min_annotation_lengths:
            print("- ", annotation_property, ": minimum", min_length, "characters")
    else:
        print("No MinAnnotationLength constraints found in ontology. Skipping minimum annotation length checks.")

    # - MaxAnnotationLength
    max_annotation_lengths = retrieve_max_annotation_length(client)
    if max_annotation_lengths:
        print("apv:MaxAnnotationLength constraints:")
        for annotation_property, max_length in max_annotation_lengths:
            print("- ", annotation_property, ": maximum", max_length, "characters")
    else:
        print("No MaxAnnotationLength constraints found in ontology. Skipping maximum annotation length checks.")

    # - AnnotationRegularExpression
    annotation_regex_expressions = retrieve_annotation_regular_expression(client)
    if annotation_regex_expressions:
        print("apv:AnnotationRegularExpression constraints:")
        for annotation_property, regex_pattern in annotation_regex_expressions:
            print("- ", annotation_property, ": regex", regex_pattern)
    else:
        print("No AnnotationRegularExpression constraints found in ontology. Skipping annotation regular expression checks.")

    # - InstanceOfMinAnnotationCoverage
    instance_coverage_requirements = retrieve_instance_of_annotation_coverage(client)
    if instance_coverage_requirements:
        print("apv:InstanceOfMinAnnotationCoverage constraints:")
        for class_uri, annotations in instance_coverage_requirements:
            print("- ", class_uri, ": instances require")
            for annotation_iri, cardinality in annotations:
                print("   - ", cardinality, annotation_iri)
    else:
        print("No InstanceOfMinAnnotationCoverage constraints found in ontology. Skipping instance annotation coverage checks.")

    # Perform quality checks:
    # - ClassURIFormationRule
    class_uri_formation_rule_violations = check_class_uri_formation_rule(client, class_uri_formation_rule)
    if class_uri_formation_rule_violations:
        print("Class URI formation violations found:")
        for v in class_uri_formation_rule_violations:
            print("- ", v)
    else:
        print("No ClassURIFormationRule violations found.")

    # - RelationURIFormationRule
    relation_uri_formation_rule_violations = check_relation_uri_formation_rule(client, relation_uri_formation_rule)
    if relation_uri_formation_rule_violations:
        print("Relation URI formation violations found:")
        for v in relation_uri_formation_rule_violations:
            print("- ", v)
    else:
        print("No RelationURIFormationRule violations found.")

    # - InstanceURIFormationRule
    instance_uri_formation_rule_violations = check_instance_uri_formation_rule(client, instance_uri_formation_rule)
    if instance_uri_formation_rule_violations:
        print("Instance URI formation violations found:")
        for v in instance_uri_formation_rule_violations:
            print("- ", v)
    else:
        print("No InstanceURIFormationRule violations found.")

    # - GlobalMinLanguageCoverage
    # - ClassMinAnnotationCoverage
    class_annotation_violations = check_class_min_annotation_coverage(client, language_tags, class_annotation_cardinalities)
    if class_annotation_violations:
        print("Class annotation coverage violations found:")
        for class_uri, violation_msg in class_annotation_violations:
            print("- ", class_uri, ":", violation_msg)
    else:
        print("No ClassMinAnnotationCoverage violations found.")

    # - RelationMinAnnotationCoverage
    relation_annotation_violations = check_relation_min_annotation_coverage(client, language_tags, relation_annotation_cardinalities)
    if relation_annotation_violations:
        print("Relation annotation coverage violations found:")
        for relation_uri, violation_msg in relation_annotation_violations:
            print("- ", relation_uri, ":", violation_msg)
    else:
        print("No RelationMinAnnotationCoverage violations found.")

    # - InstanceMinAnnotationCoverage
    instance_annotation_violations = check_instance_min_annotation_coverage(client, language_tags, instance_annotation_cardinalities)
    if instance_annotation_violations:
        print("Instance annotation coverage violations found:")
        for instance_uri, violation_msg in instance_annotation_violations:
            print("- ", instance_uri, ":", violation_msg)
    else:
        print("No InstanceMinAnnotationCoverage violations found.")

    # - MinAnnotationLength
    # - MaxAnnotationLength
    # - AnnotationRegularExpression
    # - InstanceOfMinAnnotationCoverage
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
