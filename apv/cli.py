"""Command-line interface for the APV ontology verification tool."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from apv.quality import check_global_min_language_coverage
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

    # Quality criteria check: global minimum language coverage.
    global_min_language_coverage_violations = check_global_min_language_coverage(client)


    if global_min_language_coverage_violations is not None:
        print("Global minimum language coverage violations found:")
        for violation in sorted(global_min_language_coverage_violations):
            print(f"- {violation}")
    else:
        print("No valid global minimum language coverage violations found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
