# CLI-APV

CLI-APV validates annotation-quality constraints embedded in OWL ontologies. It can evaluate a local RDF file or query a remote SPARQL endpoint and produce either a human-readable report or structured JSON.

Annotation Property Verificator (APV) consists of three related projects:

- [OWL-APV](https://github.com/rhpetry/OWL-APV) defines the canonical APV vocabulary.
- [Web-APV](https://github.com/rhpetry/Web-APV) provides browser-based validation.
- CLI-APV provides command-line validation for local and automated workflows.

CLI-APV uses the canonical APV namespace `http://www.inf.ufrgs.br/ontologies/APV#`. For compatibility with ontologies created by earlier versions of the applications, it can also read the legacy namespace `http://inf.ufrgs.br/ontologies/apv#`; reports and documentation use canonical OWL-APV terminology.

## Features

- Local validation of Turtle, RDF/XML, N-Triples, and other formats supported by RDFLib.
- Remote validation through a SPARQL 1.1 endpoint.
- Optional basic credentials for remote endpoints.
- Exact annotation-cardinality checks, including per-language cardinality.
- Whole-value regular-expression validation.
- Human-readable and JSON reports.
- Distinct exit codes for clean results, violations, and execution errors.

## Supported constraints

| Applied to | APV constraint | Validation behavior |
| --- | --- | --- |
| `owl:Ontology` | `apv:ClassURIFormationRule` | Every named `owl:Class` IRI must match the complete regular expression. |
| `owl:Ontology` | `apv:RelationURIFormationRule` | Every named object, datatype, and annotation property IRI must match the complete regular expression, matching Web-APV's relation scope. |
| `owl:Ontology` | `apv:InstanceURIFormationRule` | Every named, directly typed instance IRI must match the complete regular expression. |
| `owl:Ontology` | `apv:GlobalMinimumLanguageCoverage` | Required languages are checked on annotation properties governed by an APV annotation-coverage constraint. |
| `owl:Ontology` | `apv:ClassMinAnnotationCoverage` | Every named class must have exactly the configured number of values for each property and required language. |
| `owl:Ontology` | `apv:RelationMinAnnotationCoverage` | Every relation in Web-APV's relation scope must have exactly the configured number of values for each property and required language. |
| `owl:Ontology` | `apv:InstanceMinAnnotationCoverage` | Every named, directly typed instance must have exactly the configured number of values for each property and required language. |
| `owl:AnnotationProperty` | `apv:MinAnnotationLength` | Every value of the annotated property must contain at least the configured number of characters. |
| `owl:AnnotationProperty` | `apv:MaxAnnotationLength` | Every value of the annotated property must contain at most the configured number of characters. |
| `owl:AnnotationProperty` | `apv:AnnotationRegularExpression` | Every value of the annotated property must match the complete regular expression. |
| `owl:Class` | `apv:InstanceOfMinAnnotationCoverage` | Direct instances of the class must have exactly the configured number of values for each property and required language. |

## Requirements

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)

Dependencies are declared in `pyproject.toml` and reproducibly locked in `uv.lock`.

## Installation

Clone the repository and synchronize its environment:

```bash
git clone https://github.com/rhpetry/CLI-APV.git
cd CLI-APV
uv sync
```

## Usage

Text output is the default:

```bash
uv run main.py --local examples/apollo_sv.owl
uv run main.py --local examples/apollo_sv-edited.owl --text
```

Use `--format` when the serialization cannot be inferred reliably from the filename:

```bash
uv run main.py --local ontology.data --format turtle
```

Request structured JSON with:

```bash
uv run main.py --local examples/apollo_sv-edited.owl --json
```

Validate a remote SPARQL endpoint with:

```bash
uv run main.py --remote https://example.org/sparql
```

Endpoints using basic authentication can be queried with:

```bash
uv run main.py \
  --remote https://example.org/sparql \
  --user USERNAME \
  --password PASSWORD
```

Command-line passwords may be visible to other local processes or retained in shell history. Use credentials only on a trusted system, restrict shell-history exposure, and use an HTTPS endpoint.

Run `uv run main.py --help` for the complete command reference.

## Declaring constraints

The following valid Turtle example uses the canonical vocabulary:

```turtle
@prefix apv:  <http://www.inf.ufrgs.br/ontologies/APV#> .
@prefix ex:   <https://example.org/ontology#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

<https://example.org/ontology>
    a owl:Ontology ;
    apv:GlobalMinimumLanguageCoverage "en pt-BR" ;
    apv:ClassURIFormationRule
        "https://example\\.org/ontology#Class_[0-9]{5}" ;
    apv:RelationURIFormationRule
        "https://example\\.org/ontology#Relation_[0-9]{5}" ;
    apv:InstanceURIFormationRule
        "https://example\\.org/ontology#Instance_[0-9]{5}" ;
    apv:ClassMinAnnotationCoverage
        "rdfs:label skos:definition 2^skos:example" ;
    apv:RelationMinAnnotationCoverage "rdfs:label" ;
    apv:InstanceMinAnnotationCoverage "rdfs:label" .

rdfs:label
    a owl:AnnotationProperty ;
    apv:MinAnnotationLength 2 ;
    apv:MaxAnnotationLength 100 ;
    apv:AnnotationRegularExpression ".+" .

ex:Class_00001
    a owl:Class ;
    apv:InstanceOfMinAnnotationCoverage "rdfs:label" .
```

Coverage values are whitespace-separated property identifiers. Prefix a property with `N^` to require exactly `N` values; a property without a number defaults to exactly one. When global language coverage is configured, the cardinality is evaluated separately for every required language.

Local files may use prefixes declared in their RDF serialization. For remote validation, use full annotation-property IRIs in APV coverage values because namespace-prefix declarations are not represented in a SPARQL graph.

Language tags are validated as IANA tags and compared case-insensitively. URI and annotation regular expressions must match the whole value; add `.*` explicitly if surrounding content is permitted. Regular expressions use Python's `re` syntax.

## Output

Text reports list the discovered constraints followed by the result of every validation pass.

JSON reports preserve the following structure:

```json
{
  "constraints": {
    "class_uri_formation_rule": null,
    "language_coverage": ["en", "pt-BR"]
  },
  "violations": [
    {
      "check": "InstanceURIFormationRule",
      "parameter": "https://example\\.org/ontology#Instance_[0-9]{5}",
      "violations": ["https://example.org/ontology#invalid-instance"]
    }
  ]
}
```

The actual `constraints` object contains entries for all supported constraints, and `violations` contains one result object per check. The `parameter` field is retained for compatibility with the current output contract.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Validation completed and no violations were found. |
| `1` | Validation completed and one or more violations were found. |
| `2` | Arguments, RDF input, APV declarations, endpoint access, or validation execution failed. |

## Development

Install development dependencies and run the test suite:

```bash
uv sync --group dev
uv run --group dev pytest
```

Useful manual checks are:

```bash
uv run main.py --local examples/apollo_sv.owl --text
uv run main.py --local examples/apollo_sv-edited.owl --json
```

## Current limitations

- Validation uses asserted triples only. It does not perform OWL reasoning, traverse subclasses for class-scoped requirements, or load an ontology's import closure automatically.
- Remote validation may issue many SPARQL requests because coverage checks operate per resource, property, and language.
- Remote APV coverage declarations should use complete annotation-property IRIs instead of serialization-specific prefixes.
- Basic authentication credentials are accepted as command-line arguments and require appropriate local handling.
- Python regular-expression syntax is not identical to JavaScript regular-expression syntax used by Web-APV.

## License

No license has been published for this repository. Until a license is added, no permission to copy, modify, or redistribute the project should be assumed.
