# council-skill

Ein Claude-Skill für schwierige Entscheidungen. Du stellst eine Frage, und ein Rat aus fünf Beratern beantwortet sie, jeder aus seiner eigenen, bewusst einseitigen Sicht. Danach prüft jeder Berater die Antworten der anderen, ohne zu wissen, von wem sie stammen. Zum Schluss liest ein Vorsitzender alles und trifft einen Beschluss mit klaren nächsten Schritten.

## Der Rat

| Rolle | Fragt |
| --- | --- |
| Pessimist | Was kann scheitern, und woran merkt man es früh? |
| First-Principles-Denker | Welche Annahmen stecken in der Frage, und welche davon sind nur geglaubt? |
| Expansionist | Welches Potenzial übersiehst du, wie sähe die größere Version aus? |
| Außenstehender | Wie wirkt das auf jemanden, der nichts über deine Branche weiß? |
| Umsetzer | Was genau passiert am Montagmorgen, wer macht es, wie lange dauert es? |
| Vorsitzender | Was wird entschieden, was wird verworfen, und wann reden wir neu darüber? |

## Ablauf

1. **Briefing.** Claude klärt höchstens drei Punkte: Welche Entscheidung steht an, was ist das Ziel, welche Grenzen gibt es.
2. **Runde 1.** Die fünf Berater antworten unabhängig, alle im selben Format und mit 250 bis 400 Wörtern, damit man sie später nicht an der Form erkennt.
3. **Runde 2.** Das Werkzeug `council.py` entfernt Rollennamen und Fettdruck, mischt die Antworten und gibt jedem Berater die vier anderen als Antwort A bis D, mit eigener Reihenfolge pro Berater. Jeder nennt pro Antwort den stärksten Punkt, den schwächsten Punkt und was fehlt, dazu eine Rangfolge.
4. **Aufdecken.** Das Werkzeug ordnet die Prüfungen den Rollen zu und baut eine Rangtabelle: Platz 1 gibt 3 Punkte, Platz 4 null.
5. **Beschluss.** Der Vorsitzende entscheidet eindeutig, nennt die verworfenen Einwände, Risiken mit Gegenmaßnahmen, die nächsten Schritte für Montagmorgen, diese Woche und 30 Tage, und ein Kriterium, bei dem neu verhandelt wird.

Du bekommst das ganze Protokoll: die fünf Antworten, die aufgedeckten Prüfungen mit Rangtabelle und den Beschluss. Eine komplette Sitzung zur Frage „Soll ich meinen Newsletter kostenpflichtig machen?“ steht in [`beispiel.md`](skills/council-skill/beispiel.md).

## Wie blind ist die Prüfung?

In **Claude Code** laufen die Berater als Subagents. Jeder sieht in Runde 1 nur das Briefing und seinen eigenen Auftrag, in Runde 2 nur sein gemischtes Paket. Die Prüfung ist dort wirklich blind: Kein Prüfer kennt die Zuordnung, und keiner hat die anderen Antworten mitgeschrieben.

In **Claude.ai** schreibt ein einziger Chat alle Rollen nacheinander. Die Rollennamen verschwinden trotzdem, aber dasselbe Modell weiß, was es geschrieben hat. Der Skill sagt das offen. Die Prüfung ist dann inhaltlich blind, nicht unabhängig.

In beiden Fällen gilt: Blind heißt ohne Namen, nicht ohne Inhalt. Eine Antwort voller Risiken erkennt man als die des Pessimisten. Der Sinn der Blind-Prüfung ist, das Argument zu bewerten und nicht die Rolle.

## Installation

Füg das in Claude ein:

```
https://github.com/Ultra-Smashed/council-skill

installiere den Skill
```

Oder als Plugin in Claude Code:

```
/plugin marketplace add Ultra-Smashed/council-skill
/plugin install council-skill@council-skill
```

Oder den Ordner direkt kopieren:

```bash
git clone https://github.com/Ultra-Smashed/council-skill.git
cp -r council-skill/skills/council-skill ~/.claude/skills/
```

Ohne Codeausführung reichen `SKILL.md` und `berater.md` im Chat. Claude mischt die Antworten dann selbst.

Das Werkzeug braucht Python 3.8 oder neuer und keine Pakete. Sitzungen landen in `.council/` im aktuellen Ordner.

## Benutzung

Sag Claude etwa „Ruf den Rat ein: Soll ich mein Angebot von 1.500 auf 2.500 Euro anheben?“ oder „Ratssitzung zu meiner Idee, ein zweites Büro in Hamburg zu eröffnen“. Gib so viel Kontext mit, wie du hast: Zahlen, Fristen, was feststeht. Der Rat erfindet nichts, und was fehlt, wird zur ersten Aufgabe im Beschluss.

Nach der Sitzung kannst du einzelne Berater nachfragen („Frag den Pessimisten, was passiert, wenn der Sponsor abspringt“) oder die Sitzung mit neuen Informationen wiederholen.

Das Werkzeug geht auch allein:

```bash
cd skills/council-skill
python3 council.py neu "Frage" --kontext "Kontext"   # Sitzung anlegen
python3 council.py pruefen .council/<sitzung>         # Format, Länge, Rollen-Hinweise
python3 council.py mischen .council/<sitzung>         # Pakete für die Blind-Prüfung
python3 council.py aufdecken .council/<sitzung>       # Zuordnung und Rangtabelle
python3 council.py protokoll .council/<sitzung>       # protokoll.md bauen
```

## Grenzen

Der Rat ersetzt keine Fachberatung. Bei Recht, Steuern, Medizin oder Geldanlage weist der Vorsitzende darauf hin und nennt, wen du fragen solltest. Fünf Rollen eines Modells sind nicht fünf Menschen mit eigener Erfahrung: Der Rat ordnet und schärft dein Denken, er weiß nicht mehr über deinen Markt als du ihm sagst.

## Lizenz

MIT, siehe [LICENSE](LICENSE). Von [Christopher Thanisch](https://thanisch.co).
