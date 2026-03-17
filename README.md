# APV - OWL Ontology Verification CLI

A small CLI tool to verify OWL ontologies (RDF graphs) by executing SPARQL queries against a local RDF file or a remote SPARQL endpoint.

## Features

- Load an RDF file locally (`--local, -l`).
- Connect to a SPARQL endpoint remotely (`--remote, -r`) with optional credentials.
- Run quality criteria checks (e.g., list distinct annotation properties used in the ontology).

## Quickstart

Run locally against an RDF file:

```bash
uv run main.py --local data/o3po.ttl
```

Run against a remote SPARQL endpoint:

```bash
uv run main.py --remote <SPARQL-server>
```
