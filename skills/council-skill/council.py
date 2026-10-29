#!/usr/bin/env python3
"""council-skill: Werkzeug für die Ratssitzung.

Legt eine Sitzung an, mischt die fünf Antworten für die Blind-Prüfung, prüft Länge und
Rollen-Hinweise, deckt die Prüfungen wieder auf und baut das Protokoll.

    python3 council.py neu "Soll ich meinen Newsletter kostenpflichtig machen?"
    python3 council.py mischen .council/2026-10-29-newsletter
    python3 council.py pruefen .council/2026-10-29-newsletter
    python3 council.py aufdecken .council/2026-10-29-newsletter
    python3 council.py protokoll .council/2026-10-29-newsletter
"""

import argparse
import datetime
import json
import os
import random
import re
import sys
import unicodedata

ROLLEN = ["pessimist", "first-principles", "expansionist", "aussenstehender", "umsetzer"]
NAMEN = {
    "pessimist": "Pessimist",
    "first-principles": "First-Principles-Denker",
    "expansionist": "Expansionist",
    "aussenstehender": "Außenstehender",
    "umsetzer": "Umsetzer",
    "vorsitz": "Vorsitzender",
}
BUCHSTABEN = ["A", "B", "C", "D"]
PUNKTE = [3, 2, 1, 0]
MIN_WOERTER, MAX_WOERTER = 250, 400
TOLERANZ = 50
UEBERSCHRIFTEN = ["Kernaussage", "Punkte", "Was das für die Entscheidung heißt"]

ROLLEN_HINWEIS = re.compile(
    r"\b(?:pessimist(?:in|en)?|first[ -]?principles?(?:[ -]denker(?:in)?)?|erste[nr]? prinzipien|"
    r"expansionist(?:in|en)?|au(?:ß|ss)enstehende[rn]?|umsetzer(?:in|s)?|vorsitzende[rn]?|"
    r"berater(?:in)? (?:nr\.? ?)?[1-5])\b",
    re.I,
)
VORSTELLUNG = re.compile(
    r"^\s*(?:als|aus sicht (?:des|der|eines|einer)|in meiner rolle als|ich bin (?:der|die|ein|eine))\b[^.:\n]*"
    r"(?:%s)[^.:\n]*[.:,]\s*" % ROLLEN_HINWEIS.pattern[2:-2],
    re.I | re.M,
)
RANG = re.compile(r"^\s*\**Rangfolge\**\s*:\s*\**\s*(.+?)\s*\**\s*$", re.I | re.M)
WORT = re.compile(r"[\wÄÖÜäöüß'-]+")


class CouncilError(Exception):
    pass


def slug(text, laenge=40):
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        text = text.replace(a, b)
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:laenge].rstrip("-") or "sitzung"


def woerter(text):
    return len(WORT.findall(text))


def lesen(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def schreiben(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def sitzung_laden(ordner):
    path = os.path.join(ordner, "sitzung.json")
    if not os.path.isfile(path):
        raise CouncilError("keine Sitzung in %s (sitzung.json fehlt)" % ordner)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def antwort_pfad(ordner, rolle):
    return os.path.join(ordner, "antworten", rolle + ".md")


def antworten_laden(ordner):
    fehlt = [r for r in ROLLEN if not os.path.isfile(antwort_pfad(ordner, r))]
    if fehlt:
        raise CouncilError("Antworten fehlen: %s" % ", ".join(fehlt))
    return dict((r, lesen(antwort_pfad(ordner, r))) for r in ROLLEN)


def neu(frage, basis=".council", seed=None, datum=None, kontext=""):
    if not frage.strip():
        raise CouncilError("die Frage ist leer")
    datum = datum or datetime.date.today().isoformat()
    ordner = os.path.join(basis, "%s-%s" % (datum, slug(frage)))
    n = 2
    while os.path.exists(ordner):
        ordner = os.path.join(basis, "%s-%s-%d" % (datum, slug(frage), n))
        n += 1
    seed = random.SystemRandom().randint(1, 10 ** 6) if seed is None else seed
    os.makedirs(os.path.join(ordner, "antworten"))
    os.makedirs(os.path.join(ordner, "reviews"))
    meta = {"frage": frage.strip(), "datum": datum, "seed": seed, "rollen": ROLLEN}
    schreiben(os.path.join(ordner, "sitzung.json"), json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    briefing = "# Briefing\n\n## Frage\n\n%s\n\n## Kontext\n\n%s\n\n## Annahmen\n\n- \n" % (
        frage.strip(), kontext.strip() or "(vom Nutzer ergänzen)")
    schreiben(os.path.join(ordner, "briefing.md"), briefing)
    return ordner


def anonymisieren(text):
    out = VORSTELLUNG.sub("", text)
    out = re.sub(r"\*\*(.+?)\*\*", r"\1", out)
    out = re.sub(r"^#{1,6}\s*(?:%s)\s*$\n?" % ROLLEN_HINWEIS.pattern[2:-2], "", out, flags=re.I | re.M)
    out = ROLLEN_HINWEIS.sub("[Rolle]", out)
    return out.strip() + "\n"


def tiefer(text, mindestens=None):
    """Überschriften eine Ebene tiefer setzen, mit mindestens: so weit, dass keine flacher ist."""
    text = text.strip()
    ebenen = [len(m.group(1)) for m in re.finditer(r"^(#{1,6}) ", text, re.M)]
    schritt = 1 if mindestens is None else max(0, mindestens - min(ebenen)) if ebenen else 0
    return re.sub(r"^(#{1,6}) ", lambda m: "#" * min(6, len(m.group(1)) + schritt) + " ", text, flags=re.M)


def mischen(ordner):
    meta = sitzung_laden(ordner)
    antworten = antworten_laden(ordner)
    briefing = lesen(os.path.join(ordner, "briefing.md")) if os.path.isfile(os.path.join(ordner, "briefing.md")) else ""
    rng = random.Random(meta["seed"])
    zuordnung = {}
    for pruefer in ROLLEN:
        andere = [r for r in ROLLEN if r != pruefer]
        rng.shuffle(andere)
        zuordnung[pruefer] = dict(zip(BUCHSTABEN, andere))
        teile = [briefing.strip(), "# Vier anonyme Antworten", ""]
        for b in BUCHSTABEN:
            teile.append("## Antwort %s\n\n%s" % (b, tiefer(anonymisieren(antworten[zuordnung[pruefer][b]]))))
        schreiben(os.path.join(ordner, "pakete", pruefer + ".md"), "\n\n".join(teile).strip() + "\n")
    schreiben(os.path.join(ordner, "zuordnung.json"), json.dumps(zuordnung, ensure_ascii=False, indent=2) + "\n")
    return zuordnung


def rangfolge(text):
    m = RANG.search(text)
    if not m:
        return None
    letters = re.findall(r"\b([A-D])\b", m.group(1).upper())
    if sorted(letters) != BUCHSTABEN:
        return None
    return letters


def pruefen(ordner):
    sitzung_laden(ordner)
    meldungen = []
    for r in ROLLEN:
        path = antwort_pfad(ordner, r)
        if not os.path.isfile(path):
            meldungen.append("%s: Antwort fehlt (%s)" % (NAMEN[r], os.path.relpath(path, ordner)))
            continue
        text = lesen(path)
        n = woerter(text)
        if n < MIN_WOERTER - TOLERANZ or n > MAX_WOERTER + TOLERANZ:
            meldungen.append("%s: %d Wörter, erlaubt sind %d bis %d" % (NAMEN[r], n, MIN_WOERTER, MAX_WOERTER))
        if re.search(r"^\s*[-*]\s+\*\*", text, re.M):
            meldungen.append("%s: Listenpunkte mit Fettdruck (die anderen sehen das)" % NAMEN[r])
        for h in UEBERSCHRIFTEN:
            if not re.search(r"^##\s+%s\s*$" % re.escape(h), text, re.M):
                meldungen.append("%s: Überschrift „%s“ fehlt" % (NAMEN[r], h))
        treffer = sorted(set(m.group(0) for m in ROLLEN_HINWEIS.finditer(text)))
        if treffer:
            meldungen.append("%s: verrät eine Rolle („%s“)" % (NAMEN[r], "“, „".join(treffer)))
    for r in ROLLEN:
        path = os.path.join(ordner, "reviews", r + ".md")
        if not os.path.isfile(path):
            continue
        text = lesen(path)
        if rangfolge(text) is None:
            meldungen.append("%s: Prüfung ohne gültige Rangfolge (A, B, C, D je einmal)" % NAMEN[r])
        for b in BUCHSTABEN:
            if not re.search(r"^#{2,4}\s*Antwort %s\b" % b, text, re.M):
                meldungen.append("%s: Prüfung von Antwort %s fehlt" % (NAMEN[r], b))
    return meldungen


def aufdecken(ordner):
    path = os.path.join(ordner, "zuordnung.json")
    if not os.path.isfile(path):
        raise CouncilError("noch nicht gemischt (zuordnung.json fehlt)")
    with open(path, encoding="utf-8") as fh:
        zuordnung = json.load(fh)
    fehlt = [r for r in ROLLEN if not os.path.isfile(os.path.join(ordner, "reviews", r + ".md"))]
    if fehlt:
        raise CouncilError("Prüfungen fehlen: %s" % ", ".join(fehlt))
    punkte = dict((r, 0) for r in ROLLEN)
    erste = dict((r, 0) for r in ROLLEN)
    teile = ["# Blind-Prüfungen, aufgedeckt"]
    for pruefer in ROLLEN:
        text = lesen(os.path.join(ordner, "reviews", pruefer + ".md"))
        mapping = zuordnung[pruefer]
        offen = re.sub(r"\bAntwort ([A-D])\b",
                       lambda m: "Antwort %s (%s)" % (m.group(1), NAMEN[mapping[m.group(1)]]), text)
        order = rangfolge(text)
        if order is None:
            raise CouncilError("%s: keine gültige Rangfolge" % NAMEN[pruefer])
        offen = RANG.sub(lambda m: "Rangfolge: " + ", ".join(
            "%s (%s)" % (b, NAMEN[mapping[b]]) for b in order), offen, count=1)
        teile.append("## Prüfung durch: %s\n\n%s" % (NAMEN[pruefer], tiefer(offen, 3)))
        for i, b in enumerate(order):
            punkte[mapping[b]] += PUNKTE[i]
            if i == 0:
                erste[mapping[b]] += 1
    tabelle = sorted(ROLLEN, key=lambda r: (-punkte[r], ROLLEN.index(r)))
    zeilen = ["| Rolle | Punkte | Platz 1 |", "| --- | --- | --- |"]
    for r in tabelle:
        zeilen.append("| %s | %d von %d | %d× |" % (NAMEN[r], punkte[r], PUNKTE[0] * 4, erste[r]))
    rang = "\n".join(zeilen)
    teile.insert(1, "## Rangtabelle\n\nJede Rolle wurde von den vier anderen blind bewertet. Platz 1 gibt 3 Punkte, "
                    "Platz 4 null.\n\n" + rang)
    schreiben(os.path.join(ordner, "aufgedeckt.md"), "\n\n".join(teile) + "\n")
    return {"punkte": punkte, "platz1": erste, "reihenfolge": tabelle, "tabelle": rang}


def protokoll(ordner):
    meta = sitzung_laden(ordner)
    antworten = antworten_laden(ordner)
    auf = os.path.join(ordner, "aufgedeckt.md")
    if not os.path.isfile(auf):
        aufdecken(ordner)
    beschluss_pfad = os.path.join(ordner, "beschluss.md")
    if not os.path.isfile(beschluss_pfad):
        raise CouncilError("beschluss.md fehlt, der Vorsitzende hat noch nicht entschieden")

    teile = ["# Ratssitzung: %s" % meta["frage"], "Datum: %s" % meta["datum"]]
    if os.path.isfile(os.path.join(ordner, "briefing.md")):
        teile.append(tiefer(lesen(os.path.join(ordner, "briefing.md"))))
    teile.append("## Runde 1: Die fünf Antworten")
    for r in ROLLEN:
        teile.append("### %s\n\n%s" % (NAMEN[r], tiefer(tiefer(antworten[r]))))
    teile.append("## Runde 2: Blind-Prüfung")
    teile.append(tiefer(re.sub(r"\A# .*\n", "", lesen(auf))))
    teile.append("## Beschluss des Vorsitzenden")
    teile.append(tiefer(lesen(beschluss_pfad)))
    text = "\n\n".join(teile) + "\n"
    schreiben(os.path.join(ordner, "protokoll.md"), text)
    return text


def main(argv=None):
    p = argparse.ArgumentParser(description="Werkzeug für die Ratssitzung des council-skill.")
    sub = p.add_subparsers(dest="befehl")
    a = sub.add_parser("neu", help="Sitzung anlegen")
    a.add_argument("frage")
    a.add_argument("--kontext", default="")
    a.add_argument("--ordner", default=".council")
    a.add_argument("--seed", type=int)
    for name, hilfe in (("mischen", "Prüfpakete für die Blind-Prüfung bauen"),
                        ("pruefen", "Antworten und Prüfungen auf Format, Länge und Rollen-Hinweise prüfen"),
                        ("aufdecken", "Prüfungen den Rollen zuordnen, Rangtabelle bauen"),
                        ("protokoll", "Protokoll aus allen Teilen bauen")):
        s = sub.add_parser(name, help=hilfe)
        s.add_argument("sitzung")
        if name == "pruefen":
            s.add_argument("--strikt", action="store_true", help="Exit-Code 1 bei Meldungen")
    args = p.parse_args(argv)
    try:
        if args.befehl == "neu":
            ordner = neu(args.frage, args.ordner, args.seed, kontext=args.kontext)
            print(ordner)
        elif args.befehl == "mischen":
            mischen(args.sitzung)
            print("Prüfpakete in %s" % os.path.join(args.sitzung, "pakete"))
            meldungen = pruefen(args.sitzung)
            for m in meldungen:
                print("Hinweis: " + m)
        elif args.befehl == "pruefen":
            meldungen = pruefen(args.sitzung)
            for m in meldungen:
                print(m)
            if not meldungen:
                print("Alles in Ordnung.")
            return 1 if args.strikt and meldungen else 0
        elif args.befehl == "aufdecken":
            print(aufdecken(args.sitzung)["tabelle"])
        elif args.befehl == "protokoll":
            protokoll(args.sitzung)
            print(os.path.join(args.sitzung, "protokoll.md"))
        else:
            p.print_help()
            return 2
        return 0
    except CouncilError as e:
        print("council.py: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
