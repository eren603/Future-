"""Every evidence reference in the repair contract must resolve on disk.

A contract that names a test which does not exist is worse than no contract: it reads
like verification. The Madde 11 audit found exactly that, so the check is mechanical now.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "repair_contract.json").read_text(encoding="utf-8"))


class RepairContractTests(unittest.TestCase):
    def test_every_evidence_reference_resolves(self):
        for requirement in CONTRACT["requirements"]:
            for evidence in requirement["evidence"]:
                with self.subTest(requirement=requirement["id"], evidence=evidence):
                    if "::" in evidence:
                        path, name = evidence.split("::")
                        target = ROOT / path
                        self.assertTrue(target.exists(), path)
                        self.assertRegex(target.read_text(encoding="utf-8"),
                                         r"def %s\(" % re.escape(name))
                    else:
                        self.assertTrue((ROOT / evidence).exists(), evidence)

    def test_no_verified_requirement_is_evidence_free(self):
        for requirement in CONTRACT["requirements"]:
            with self.subTest(requirement=requirement["id"]):
                if requirement["status"] == "VERIFIED":
                    self.assertTrue(requirement["evidence"])

    def test_contract_declares_no_derived_status(self):
        # Task 11: a status that no host derived must not sit in a file as if it were one.
        self.assertNotIn("task_status", CONTRACT)
        self.assertEqual(CONTRACT["version"], "1.4")
        self.assertFalse(CONTRACT["production_approval"])
        self.assertEqual(CONTRACT["model_eval"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
