import ast
import json
import os
import re
import unittest

from _load import ROOT, SKILL, council


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


class Repo(unittest.TestCase):
    def test_layout(self):
        for rel in ("README.md", "LICENSE", ".gitignore", ".claude-plugin/plugin.json",
                    ".claude-plugin/marketplace.json", "skills/council-skill/SKILL.md",
                    "skills/council-skill/berater.md", "skills/council-skill/council.py",
                    "skills/council-skill/beispiel.md"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        self.assertEqual(os.listdir(os.path.join(ROOT, "skills")), ["council-skill"])
        self.assertIn(".council/", read(ROOT, ".gitignore"))

    def test_frontmatter(self):
        m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---\n", read(SKILL, "SKILL.md"))
        self.assertTrue(m)
        self.assertEqual(m.group(1), "council-skill")
        self.assertLess(len(m.group(2)), 1024)
        for phrase in ("Ratssitzung", "Council", "Pessimist", "Umsetzer", "Vorsitzender"):
            self.assertIn(phrase, m.group(2))

    def test_sechs_rollen_in_berater_md(self):
        text = read(SKILL, "berater.md")
        for rolle in council.ROLLEN + ["vorsitz"]:
            self.assertTrue(re.search(r"^## .+\(`%s`\)$" % re.escape(rolle), text, re.M), rolle)
            self.assertIn(council.NAMEN[rolle].split("-")[0], text)
        for h in council.UEBERSCHRIFTEN:
            self.assertIn("## " + h, text)

    def test_skill_nennt_alle_befehle(self):
        text = read(SKILL, "SKILL.md")
        for befehl in ("neu", "pruefen", "mischen", "aufdecken", "protokoll"):
            self.assertIn("council.py %s" % befehl, text)

    def test_beispiel_vollstaendig(self):
        text = read(SKILL, "beispiel.md")
        for name in ("Pessimist", "First-Principles-Denker", "Expansionist", "Außenstehender", "Umsetzer"):
            self.assertIn("#### %s" % name, text)
            self.assertIn("Prüfung durch: %s" % name, text)
        for abschnitt in ("Beschluss", "Begründung", "Verworfene Einwände", "Risiken und Gegenmaßnahmen",
                          "Nächste Schritte", "Neu verhandeln, wenn"):
            self.assertIn(abschnitt, text)
        self.assertIn("| Rolle | Punkte | Platz 1 |", text)

    def test_kein_gedankenstrich_in_doku(self):
        for rel in ("README.md", "skills/council-skill/SKILL.md", "skills/council-skill/berater.md",
                    "skills/council-skill/beispiel.md"):
            text = read(ROOT, rel)
            self.assertNotIn("\u2014", text, rel)
            self.assertNotIn(" \u2013 ", text, rel)

    def test_readme(self):
        text = read(ROOT, "README.md")
        self.assertIn("github.com/Ultra-Smashed/council-skill", text)
        self.assertIn("thanisch.co", text)

    def test_plugin_json(self):
        plugin = json.loads(read(ROOT, ".claude-plugin", "plugin.json"))
        market = json.loads(read(ROOT, ".claude-plugin", "marketplace.json"))
        self.assertEqual(plugin["name"], "council-skill")
        self.assertEqual(market["plugins"][0]["name"], "council-skill")

    def test_python38_syntax(self):
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(base, f)
                    ast.parse(read(path), path, feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
