import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from _load import SKILL, council

ROLLEN = council.ROLLEN


def kennung(rolle):
    return "Kennung-%d" % (ROLLEN.index(rolle) if rolle in ROLLEN else 9)


def antwort(rolle, woerter=300, vorstellung=""):
    fuell = " ".join(["Inhalt"] * (woerter - 30))
    return ("## Kernaussage\n\n%s%s steht hier.\n\n## Punkte\n\n- Erster Punkt mit Text.\n- %s\n"
            "- Dritter Punkt.\n\n## Was das für die Entscheidung heißt\n\nZwei Sätze dazu. Und noch einer.\n"
            % (vorstellung, kennung(rolle), fuell))


def review(order="C, A, D, B"):
    teile = ["### Antwort %s\nStärkster Punkt: gut.\nSchwächster Punkt: schwach.\nWas fehlt: mehr." % b
             for b in "ABCD"]
    return "\n\n".join(teile) + "\n\nRangfolge: %s\nBegründung: Weil.\n" % order


class Sitzung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.ordner = council.neu("Soll ich den Laden öffnen?", os.path.join(self.tmp, ".council"),
                                  seed=42, datum="2026-10-29", kontext="Ein kleiner Laden.")

    def alle_antworten(self, **extra):
        for r in ROLLEN:
            council.schreiben(council.antwort_pfad(self.ordner, r), extra.get(r, antwort(r)))

    def alle_reviews(self, order="C, A, D, B"):
        for r in ROLLEN:
            council.schreiben(os.path.join(self.ordner, "reviews", r + ".md"), review(order))


class Neu(Sitzung):
    def test_ordner_und_dateien(self):
        self.assertTrue(self.ordner.endswith("2026-10-29-soll-ich-den-laden-oeffnen"))
        meta = council.sitzung_laden(self.ordner)
        self.assertEqual(meta["seed"], 42)
        self.assertEqual(meta["rollen"], ROLLEN)
        briefing = council.lesen(os.path.join(self.ordner, "briefing.md"))
        self.assertIn("Soll ich den Laden öffnen?", briefing)
        self.assertIn("Ein kleiner Laden.", briefing)

    def test_zweite_sitzung_gleicher_frage(self):
        zweite = council.neu("Soll ich den Laden öffnen?", os.path.join(self.tmp, ".council"), seed=1,
                             datum="2026-10-29")
        self.assertNotEqual(zweite, self.ordner)
        self.assertTrue(zweite.endswith("-2"))

    def test_leere_frage(self):
        with self.assertRaises(council.CouncilError):
            council.neu("  ", self.tmp)

    def test_slug(self):
        self.assertEqual(council.slug("Größe & Maß: Ja?"), "groesse-mass-ja")
        self.assertEqual(council.slug("???"), "sitzung")


class Mischen(Sitzung):
    def test_fehlende_antworten(self):
        with self.assertRaises(council.CouncilError):
            council.mischen(self.ordner)

    def test_kein_paket_mit_eigener_antwort(self):
        self.alle_antworten()
        zuordnung = council.mischen(self.ordner)
        for r in ROLLEN:
            paket = council.lesen(os.path.join(self.ordner, "pakete", r + ".md"))
            self.assertNotIn(kennung(r), paket)
            for andere in ROLLEN:
                if andere != r:
                    self.assertIn(kennung(andere), paket)
            self.assertEqual(sorted(zuordnung[r]), ["A", "B", "C", "D"])
            self.assertNotIn(r, zuordnung[r].values())
            self.assertIn("Soll ich den Laden öffnen?", paket)

    def test_buchstaben_passen_zur_zuordnung(self):
        self.alle_antworten()
        zuordnung = council.mischen(self.ordner)
        paket = council.lesen(os.path.join(self.ordner, "pakete", "umsetzer.md"))
        for b, rolle in zuordnung["umsetzer"].items():
            abschnitt = paket.split("## Antwort %s" % b, 1)[1].split("## Antwort ", 1)[0]
            self.assertIn(kennung(rolle), abschnitt)

    def test_deterministisch_mit_seed(self):
        self.alle_antworten()
        a = council.mischen(self.ordner)
        b = council.mischen(self.ordner)
        self.assertEqual(a, b)

    def test_pakete_unterscheiden_sich(self):
        self.alle_antworten()
        zuordnung = council.mischen(self.ordner)
        reihen = set(tuple(zuordnung[r][b] for b in "ABCD") for r in ROLLEN)
        self.assertGreater(len(reihen), 1)

    def test_rollenhinweise_entfernt(self):
        self.alle_antworten(pessimist=antwort("x", vorstellung="Als Pessimist sehe ich das so: "),
                            umsetzer=antwort("y", vorstellung="Aus Sicht des Umsetzers ist klar: "),
                            expansionist="# Expansionist\n\n" + antwort("z"))
        council.mischen(self.ordner)
        for r in ROLLEN:
            paket = council.lesen(os.path.join(self.ordner, "pakete", r + ".md"))
            for wort in ("Pessimist", "Umsetzer", "Expansionist", "Als ", "Aus Sicht"):
                self.assertNotIn(wort, paket, "%s in Paket %s" % (wort, r))

    def test_fettdruck_entfernt(self):
        text = antwort("pessimist").replace("- Erster Punkt", "- **Erster Punkt**")
        self.alle_antworten(pessimist=text)
        council.mischen(self.ordner)
        paket = council.lesen(os.path.join(self.ordner, "pakete", "umsetzer.md"))
        self.assertNotIn("**", paket)

    def test_ueberschriften_tiefer(self):
        self.alle_antworten()
        council.mischen(self.ordner)
        paket = council.lesen(os.path.join(self.ordner, "pakete", "umsetzer.md"))
        self.assertIn("### Kernaussage", paket)
        self.assertNotIn("\n## Kernaussage", paket)


class Pruefen(Sitzung):
    def test_alles_gut(self):
        self.alle_antworten()
        self.assertEqual(council.pruefen(self.ordner), [])

    def test_fehlende_antwort(self):
        self.assertEqual(len(council.pruefen(self.ordner)), 5)

    def test_laenge(self):
        self.alle_antworten(umsetzer=antwort("u", woerter=120), pessimist=antwort("p", woerter=600))
        meldungen = council.pruefen(self.ordner)
        self.assertEqual(len([m for m in meldungen if "Wörter" in m]), 2)

    def test_ueberschrift_fehlt(self):
        self.alle_antworten(expansionist=antwort("e").replace("## Punkte", "## Ideen"))
        self.assertTrue(any("Punkte" in m for m in council.pruefen(self.ordner)))

    def test_rolle_verraten(self):
        self.alle_antworten(aussenstehender=antwort("a", vorstellung="Als Außenstehender frage ich: "))
        self.assertTrue(any("verrät" in m for m in council.pruefen(self.ordner)))

    def test_fettdruck(self):
        self.alle_antworten(pessimist=antwort("p").replace("- Erster", "- **Erster** Punkt"))
        self.assertTrue(any("Fettdruck" in m for m in council.pruefen(self.ordner)))

    def test_review_ohne_rangfolge(self):
        self.alle_antworten()
        council.schreiben(os.path.join(self.ordner, "reviews", "pessimist.md"), review("A, A, B, C"))
        self.assertTrue(any("Rangfolge" in m for m in council.pruefen(self.ordner)))

    def test_rangfolge_lesen(self):
        self.assertEqual(council.rangfolge("x\n**Rangfolge:** D, C, B, A\n"), ["D", "C", "B", "A"])
        self.assertEqual(council.rangfolge("Rangfolge: C > A > D > B"), ["C", "A", "D", "B"])
        self.assertIsNone(council.rangfolge("Rangfolge: A, B, C"))
        self.assertIsNone(council.rangfolge("keine"))


class Aufdecken(Sitzung):
    def test_zuordnung_und_punkte(self):
        self.alle_antworten()
        zuordnung = council.mischen(self.ordner)
        self.alle_reviews("C, A, D, B")
        res = council.aufdecken(self.ordner)
        erwartet = dict((r, 0) for r in ROLLEN)
        for pruefer in ROLLEN:
            for i, b in enumerate("CADB"):
                erwartet[zuordnung[pruefer][b]] += council.PUNKTE[i]
        self.assertEqual(res["punkte"], erwartet)
        self.assertEqual(sum(res["punkte"].values()), 5 * 6)
        text = council.lesen(os.path.join(self.ordner, "aufgedeckt.md"))
        for pruefer in ROLLEN:
            for b, rolle in zuordnung[pruefer].items():
                self.assertIn("Antwort %s (%s)" % (b, council.NAMEN[rolle]), text)
        self.assertIn("| Rolle | Punkte | Platz 1 |", text)

    def test_ohne_mischen(self):
        with self.assertRaises(council.CouncilError):
            council.aufdecken(self.ordner)

    def test_fehlende_reviews(self):
        self.alle_antworten()
        council.mischen(self.ordner)
        with self.assertRaises(council.CouncilError):
            council.aufdecken(self.ordner)


class Protokoll(Sitzung):
    def test_ohne_beschluss(self):
        self.alle_antworten()
        council.mischen(self.ordner)
        self.alle_reviews()
        with self.assertRaises(council.CouncilError):
            council.protokoll(self.ordner)

    def test_vollstaendig(self):
        self.alle_antworten()
        council.mischen(self.ordner)
        self.alle_reviews()
        council.schreiben(os.path.join(self.ordner, "beschluss.md"), "## Beschluss\n\nJa.\n")
        text = council.protokoll(self.ordner)
        self.assertTrue(text.startswith("# Ratssitzung: Soll ich den Laden öffnen?"))
        for name in ("Pessimist", "First-Principles-Denker", "Expansionist", "Außenstehender", "Umsetzer"):
            self.assertIn("### %s" % name, text)
        self.assertIn("### Beschluss", text)
        self.assertEqual(len(re.findall(r"^# ", text, re.M)), 1)
        self.assertTrue(os.path.isfile(os.path.join(self.ordner, "protokoll.md")))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = council.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_ganzer_ablauf(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        code, out, _ = self.run_cli("neu", "Frage?", "--ordner", os.path.join(tmp, "c"), "--seed", "3")
        self.assertEqual(code, 0)
        ordner = out.strip()
        for r in ROLLEN:
            council.schreiben(council.antwort_pfad(ordner, r), antwort(r))
        self.assertEqual(self.run_cli("pruefen", ordner, "--strikt")[0], 0)
        self.assertEqual(self.run_cli("mischen", ordner)[0], 0)
        for r in ROLLEN:
            council.schreiben(os.path.join(ordner, "reviews", r + ".md"), review())
        code, out, _ = self.run_cli("aufdecken", ordner)
        self.assertIn("| Rolle |", out)
        self.assertEqual(self.run_cli("protokoll", ordner)[0], 2)
        council.schreiben(os.path.join(ordner, "beschluss.md"), "## Beschluss\n\nNein.\n")
        code, out, _ = self.run_cli("protokoll", ordner)
        self.assertEqual(code, 0)
        self.assertTrue(out.strip().endswith("protokoll.md"))

    def test_strikt_meldet(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        ordner = council.neu("Frage?", tmp, seed=1)
        self.assertEqual(self.run_cli("pruefen", ordner, "--strikt")[0], 1)

    def test_keine_sitzung(self):
        code, _, err = self.run_cli("mischen", "/gibt/es/nicht")
        self.assertEqual(code, 2)
        self.assertIn("sitzung.json", err)

    def test_als_skript(self):
        p = subprocess.run([sys.executable, os.path.join(SKILL, "council.py"), "--help"], stdout=subprocess.PIPE)
        self.assertEqual(p.returncode, 0)
        self.assertIn(b"mischen", p.stdout)


if __name__ == "__main__":
    unittest.main()
