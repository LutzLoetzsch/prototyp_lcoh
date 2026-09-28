# prototyp_lcoh

Quelltext zur Masterarbeit „Szenariobasiertes, KI-gestütztes
Entscheidungssystem in der kommunalen Wärmeplanung" (HSF Meißen, 2026).

Prototyp zur wirtschaftlichen Potenzialbewertung von Wärmeversorgungsoptionen:
LCOH-Rechenkern, Approximationsmodell und eine Zugangsschicht, die eine Frage
im Klartext in einen Parametersatz übersetzt.

Das Repositorium dient der Nachvollziehbarkeit. Der Stand, auf dem die in der
Arbeit berichteten Ergebnisse beruhen, ist über das Tag `einreichung`
erreichbar und wird nicht verändert. Tag der Einreichung: 28.09.2026.

## Aufbau

| Verzeichnis | Inhalt |
|---|---|
| `dss/src/dss/` | Rechenmodell: Fachmodell, Annuitätenrechnung, Modellstufen, Erzeugerstränge, Entscheidung, Stichprobenziehung, Approximationsmodell |
| `dss/src/dss/cli_entscheidung.py` | Parametervertrag, Schnittstelle beider Schichten |
| `dss/reports/` | Laufskripte der in der Arbeit berichteten Experimente |
| `dss/daten/records/` | Trainings-, Validierungs- und Testsatz |
| `rag_frontend/` | Zugangsschicht: semantische Auswahl, Extraktion über das Sprachmodell, Auswertung |
| `rag_frontend/wissensbasis/` | Kommunenprofile und Technikkatalog |
| `abbildungen/` | Abbildungen, die aus den Laufskripten hervorgehen |

Die Auswahl umfasst die in Kapitel 5 und im Anhang der Arbeit benannten Module
sowie die Module, die für deren Ausführung erforderlich sind.

## Ausführung

Die Laufskripte unter `dss/reports/` setzen den Suchpfad selbst und werden aus
ihrem Verzeichnis heraus gestartet. Für den direkten Import des Pakets:

    cd dss && PYTHONPATH=src python3 -c "import dss"

Abhängigkeiten stehen in `dss/requirements.txt` und
`rag_frontend/requirements.txt`. Die in der Arbeit verwendeten Versionen sind
im Anhang unter „Laufzeitumgebung" dokumentiert.

Die Zugangsschicht benötigt Zugangsdaten für die extern betriebenen Modelle.
Sie sind nicht Bestandteil des Repositoriums und werden über Umgebungsvariablen
erwartet.

## Nicht enthalten

Das im Werkzeugvergleich eingesetzte excelbasierte Analysewerkzeug unterliegt
einer Nutzungsbeschränkung und ist nicht Bestandteil des Repositoriums. Die
Messwerte beider Versuchsaufbauten liegen unter
`dss/reports/E19_toolvergleich/` als CSV vor.

Der eingefrorene Benchmarkstand der Zugangsschicht und die Wortlaute der
Antworten sind ebenfalls nicht enthalten. Die daraus berichteten Kennzahlen
stehen im Anhang der Arbeit.
