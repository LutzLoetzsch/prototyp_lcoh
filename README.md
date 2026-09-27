# prototyp_lcoh

Quelltext zur Masterarbeit *&lt;Titel&gt;* (&lt;Hochschule&gt;, &lt;Jahr&gt;).

Prototyp zur wirtschaftlichen Potenzialbewertung von Wärmeversorgungsoptionen:
LCOH-Rechenkern, Approximationsmodell und eine Zugangsschicht, die eine Frage
im Klartext in einen Parametersatz übersetzt.

Das Repositorium dient der Nachvollziehbarkeit. Der Stand, auf dem die in der
Arbeit berichteten Ergebnisse beruhen, ist über das Tag `einreichung`
erreichbar und wird nicht verändert. Tag der Einreichung: 28.09.2026.

## Aufbau

| Verzeichnis | Inhalt |
| --- | --- |
| `rechenmodell/` | LCOH-Rechenkern und Approximationsmodell |
| `cli_entscheidung.py` | Parametervertrag, Schnittstelle beider Schichten |
| `zugangsschicht/` | semantische Auswahl, Extraktion über das Sprachmodell |

Die Gliederung entspricht der Projektstruktur im Anhang der Arbeit.

## Laufzeitumgebung

Python 3.12.3, getrennte virtuelle Umgebungen je Schicht, weil sich die
Paketstände unterscheiden. Versionen siehe `rechenmodell/requirements.txt`
und `zugangsschicht/requirements.txt`.

## Daten

Enthalten ist ausschließlich eigener Quelltext. Technikkatalog und
Kommunenprofile sind nicht Teil des Repositoriums; ihre Herkunft weist die
Arbeit nach.

## Lizenz

&lt;noch festzulegen&gt;
