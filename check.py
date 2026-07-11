import json, os, re, sys, urllib.parse, urllib.request

SEITE_URL = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"
KAUF_LINK = SEITE_URL
GESUCHTE_GROESSE = "M"
STATUS_DATEI = "status.txt"

def sende_telegram(text):
    token   = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    daten   = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(url, data=daten, timeout=30)

# --- 1. Roh-HTML der Seite laden ---
try:
    anfrage = urllib.request.Request(SEITE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        html = antwort.read().decode("utf-8", errors="ignore")
except Exception as fehler:
    print(f"Seite laden fehlgeschlagen: {fehler}")
    sys.exit(0)

print(f"HTML geladen, Laenge: {len(html)} Zeichen")

# --- 2. DIAGNOSE: stehen ueberhaupt Varianten-Daten drin? ---
print(f"Vorkommen von '\"available\"': {html.count(chr(34)+'available'+chr(34))}")
print(f"Vorkommen von '\"option1\"': {html.count(chr(34)+'option1'+chr(34))}")

# --- 3. Versuch: M-Variante samt Verfuegbarkeit aus eingebettetem JSON lesen ---
# Sucht Variantenobjekte, in denen die Groesse (option1/title) und available zusammen stehen.
verfuegbar_m = None
muster = re.compile(
    r'\{[^{}]*?"(?:option1|title)"\s*:\s*"' + re.escape(GESUCHTE_GROESSE) +
    r'"[^{}]*?"available"\s*:\s*(true|false)[^{}]*?\}'
)
treffer = muster.search(html)
if treffer is None:
    # zweite Reihenfolge: available kommt vor option1/title
    muster2 = re.compile(
        r'\{[^{}]*?"available"\s*:\s*(true|false)[^{}]*?"(?:option1|title)"\s*:\s*"' +
        re.escape(GESUCHTE_GROESSE) + r'"[^{}]*?\}'
    )
    treffer = muster2.search(html)

if treffer:
    verfuegbar_m = (treffer.group(1) == "true")
    print(f"M-Variante gefunden. available = {verfuegbar_m}")
else:
    print("KEIN Varianten-Objekt fuer M im HTML gefunden.")
    print("=> Daten sind vermutlich rein per JavaScript -> Selbstbau nicht moeglich.")
    sys.exit(0)

# --- Ab hier die bekannte Logik (Report / Monitor) ---
modus = os.environ.get("MODUS", "monitor")

if modus == "report":
    zustand = "verfuegbar" if verfuegbar_m else "ausverkauft"
    nachricht = f"Morgen-Report: Groesse {GESUCHTE_GROESSE} ist {zustand}."
    if verfuegbar_m:
        nachricht += f"\nJetzt bestellen: {KAUF_LINK}"
    print(nachricht)
    try:
        sende_telegram(nachricht)
    except Exception as fehler:
        print(f"Telegram fehlgeschlagen: {fehler}")
    sys.exit(0)

jetzt = "verfuegbar" if verfuegbar_m else "ausverkauft"

try:
    with open(STATUS_DATEI) as f:
        vorher = f.read().strip()
except FileNotFoundError:
    vorher = "unbekannt"

print(f"vorher: {vorher} | jetzt: {jetzt}")

if jetzt == vorher:
    print("Keine Aenderung.")
    sys.exit(0)

nachricht = None
if jetzt == "verfuegbar":
    nachricht = f"Groesse {GESUCHTE_GROESSE} ist JETZT VERFUEGBAR!\n{KAUF_LINK}"
elif jetzt == "ausverkauft" and vorher == "verfuegbar":
    nachricht = f"Groesse {GESUCHTE_GROESSE} ist wieder ausverkauft."

if nachricht:
    print(nachricht)
    try:
        sende_telegram(nachricht)
    except Exception as fehler:
        print(f"Telegram fehlgeschlagen: {fehler}")
        sys.exit(1)

with open(STATUS_DATEI, "w") as f:
    f.write(jetzt)
