from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def write_turtle(tmp_path: Path):
    def _write(content: str) -> Path:
        path = tmp_path / "ontology.ttl"
        path.write_text(content, encoding="utf-8")
        return path

    return _write

