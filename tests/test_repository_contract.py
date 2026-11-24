from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_required_directories_exist(self):
        required = [
            "src/cabes",
            "src/cpcr",
            "src/evaluation",
            "configs",
            "data",
            "scripts",
            "results",
            "docs",
            "tests",
            ".github/workflows",
        ]
        for relative in required:
            self.assertTrue((REPO / relative).is_dir(), relative)

    def test_source_has_no_original_absolute_runtime_import(self):
        source_files = list((REPO / "src").rglob("*.py"))
        source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
        self.assertNotIn("E:" + "\\paperbig", source_text)
        self.assertNotIn("sys.path.insert", source_text)

    def test_public_package_excludes_sensitive_payload_extensions(self):
        forbidden = {".safetensors", ".pt", ".pth", ".parquet", ".h5", ".hdf5"}
        for path in REPO.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), forbidden, str(path))
