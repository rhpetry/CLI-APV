# Ontology Data

This folder contains RDF/OWL ontologies used for testing and demonstration purposes.

Each ontology is stored in its own file (e.g., `o3po.ttl`). The following list describes the ontologies included in this folder.

## Included Ontologies

### 1) O3PO — Offshore Petroleum Production Plant Ontology

- **File:** `o3po.ttl`
- **Description:** A domain ontology that formally represents knowledge about **offshore oil and gas production systems**.
- **Key features:**
  - **BFO-aligned** (Basic Formal Ontology) for interoperability with other foundational ontologies.
  - **Bilingual**, with labels/annotations in multiple languages.
  - Designed to support **semantic data integration, interoperability, and reasoning** over industrial asset information.
- **Source:**
  - Santos, N. O., Rodrigues, F. H., Schmidt, D., Romeu, R. K., Nascimento, G., & Abel, M. (2024).
    *O3PO: A domain ontology for offshore petroleum production plants.* Expert Systems with Applications, 238 (Part F), 122104.
  - DOI: https://doi.org/10.1016/j.eswa.2023.122104

## How to Use

Use these files as input to the APV CLI tool to validate ontology quality through local SPARQL queries:

```bash
python main.py --local data/o3po.ttl
```

(Or run via `uv` as shown in the project README.)
