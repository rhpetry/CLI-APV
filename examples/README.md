# Ontology examples

This directory contains RDF/OWL ontologies for demonstrations and manual CLI-APV verification.

## Included ontologies

### Apollo Structured Vocabulary

- `apollo_sv.owl`: unchanged Apollo-SV ontology example without APV constraints.
- `apollo_sv-edited.owl`: demonstration copy with canonical APV constraints and intentional violations.

The edited Apollo copy adds the following demonstration rules:

- English language coverage for APV-constrained properties.
- Exactly one English `rdfs:label` and `rdfs:comment` on every class, relation, and instance.
- A minimum length of 5 characters for `rdfs:label` values.
- A length between 5 and 500 characters for Apollo definitions expressed with `obo:IAO_0000115`.
- Whole-string regular expressions on labels, comments, and definitions that allow Unicode letters and numbers, spaces, ordinary punctuation, underscores, and angle brackets while rejecting line breaks and other unlisted special characters.

The underlying Apollo ontology content is otherwise unchanged.

## Running the examples

```bash
uv run main.py --local examples/apollo_sv.owl --text
uv run main.py --local examples/apollo_sv-edited.owl --text
```
