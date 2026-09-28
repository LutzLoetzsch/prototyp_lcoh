from openai import OpenAI

import fachwissen
from config import LLM

kontext = next(t["text"] for t in fachwissen.lade_technikkatalog()
               if t["block"] == "grosswaermepumpe")

frage = ("Welche Jahresarbeitszahl ist für eine Großwärmepumpe mit "
         "Klärwasser als Wärmequelle anzusetzen? Antworte in höchstens "
         "drei Sätzen und nenne Wert, Tabelle und Stützjahr.")

client = OpenAI(base_url=LLM["base_url"], api_key="ollama")

ergebnisse = []
for titel, inhalt in (("ANTWORT OHNE ANBINDUNG", None),
                      ("ANTWORT MIT ANBINDUNG", kontext)):
    nachricht = (f"Kontext (belegte Quellen):\n{inhalt}\n\n{frage}"
                 if inhalt else frage)
    antwort = client.chat.completions.create(
        model=LLM["model"],
        temperature=LLM.get("temperature", 0.0),
        messages=[{"role": "user", "content": nachricht}],
    )
    ergebnisse.append(f"{titel}\n{antwort.choices[0].message.content}")

print("\n\n".join(ergebnisse))
