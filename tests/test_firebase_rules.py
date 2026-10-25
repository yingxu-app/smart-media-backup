import json
import unittest
from pathlib import Path


class FirebaseRulesTests(unittest.TestCase):
    def test_database_rules_deny_public_access_and_scope_each_account_to_its_uid(self):
        root = Path(__file__).resolve().parents[1]
        rules = json.loads((root / "firebase" / "database.rules.json").read_text(encoding="utf-8"))
        self.assertIs(rules["rules"][".read"], False)
        self.assertIs(rules["rules"][".write"], False)
        user = rules["rules"]["users"]["$uid"]
        self.assertEqual(user[".read"], "auth != null && auth.uid === $uid")
        self.assertEqual(user[".write"], "auth != null && auth.uid === $uid")
        config = json.loads((root / "firebase.json").read_text(encoding="utf-8"))
        self.assertEqual(config["database"]["rules"], "firebase/database.rules.json")


if __name__ == "__main__":
    unittest.main()
