import json, os, sys, urllib.parse, urllib.request

PRODUKT_JSON = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance.json"
KAUF_LINK    = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"
GESUCHTE_GROESSE = "M"
STATUS_DATEI = "status.txt"

def groesse(v):
    return (v.get("option1") or v.get("title") or "").strip().upper()

def sende_telegram(text):
    token   = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    daten   = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(url, data=daten, timeout=30)

modus = os.environ.get("MODUS", "monitor")

# --- Daten abrufen ---
try:
    anfrage = urllib.request.Request(PRODUKT_JSON, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        varianten = json.loads(antwort.read())["product"]["variants"]
except Exception as fehler:
    print(f"Abruf fehlgeschlagen: {fehler}")
    sys.exit(0)

treffer = next((v for v in varianten if groesse(v) == GESUCHTE_GROESSE.upper()), None)
if treffer is None:
    print(f"Keine Variante '{GESUCHTE_GROESSE}' gefunden.")
    sys.exit(0)

# --- Modus: taeglicher Morgen-Report (immer melden) ---
if modus == "report":
    zustand = "verfuegbar" if treffer["available"] else "ausverkauft"
    nachricht = f"Morgen-Report: Groesse {GESUCHTE_GROESSE} ist {zustand}."
    if treffer["available"]:
        nachricht += f"\nJetzt bestellen: {KAUF_LINK}"
    print(nachricht)
    try:
        sende_telegram(nachricht)
    except Exception as fehler:
        print(f"Telegram fehlgeschlagen: {fehler}")
    sys.exit(0)

# --- Modus: Monitor (nur bei Zustandswechsel melden) ---
jetzt = "verfuegbar" if treffer["available"] else "ausverkauft"

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
