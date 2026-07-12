import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

SEITE_URL = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"
KAUF_LINK = SEITE_URL
GESUCHTE_GROESSE = "M"
STATUS_DATEI = "status.txt"
REPORT_DATEI = "report_datum.txt"
REPORT_AB_STUNDE = 7          # Report beim ersten Lauf ab 7 Uhr deutscher Zeit

def sende_telegram(text):
    token   = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    daten   = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    urllib.request.urlopen(url, data=daten, timeout=30)

# --- 1. HTML laden ---
try:
    anfrage = urllib.request.Request(SEITE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        html = antwort.read().decode("utf-8", errors="ignore")
except Exception as fehler:
    print(f"Seite laden fehlgeschlagen: {fehler}")
    sys.exit(0)

# --- 2. Nuxt-Datenpaket holen ---
bloecke = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
payload = None
for b in bloecke:
    b = b.strip()
    if b.startswith('[') and '"available"' in b and 'selectedOptions' in b:
        payload = b
        break

if payload is None:
    print("Nuxt-Datenpaket nicht gefunden -> evtl. Seitenaufbau geaendert.")
    sys.exit(0)

try:
    arr = json.loads(payload)
except Exception as fehler:
    print(f"Datenpaket nicht lesbar: {fehler}")
    sys.exit(0)

# --- 3. Verweise aufloesen und Groessen bestimmen ---
def wert(idx):
    if isinstance(idx, int) and 0 <= idx < len(arr):
        return arr[idx]
    return idx

def ist_variante(o):
    return isinstance(o, dict) and "available" in o and "sku" in o and "selectedOptions" in o

groessen = {}
for o in arr:
    if not ist_variante(o):
        continue
    verf = wert(o["available"])
    groesse = None
    so = wert(o["selectedOptions"])
    if isinstance(so, list) and so:
        erste = wert(so[0])
        if isinstance(erste, dict) and "value" in erste:
            groesse = wert(erste["value"])
    if not isinstance(groesse, str):
        groesse = wert(o.get("title"))
    if isinstance(groesse, str) and isinstance(verf, bool):
        groessen[groesse] = verf

print("Gefundene Groessen und Verfuegbarkeit:", groessen)

if GESUCHTE_GROESSE not in groessen:
    print(f"Groesse {GESUCHTE_GROESSE} nicht in den Daten gefunden.")
    sys.exit(0)

verfuegbar_m = groessen[GESUCHTE_GROESSE]

# --- 4. Taeglicher Report: erster Lauf ab 7 Uhr deutscher Zeit ---
jetzt_de = datetime.now(ZoneInfo("Europe/Berlin"))
heute = jetzt_de.strftime("%Y-%m-%d")

if jetzt_de.hour >= REPORT_AB_STUNDE:
    try:
        with open(REPORT_DATEI) as f:
            letzter_report = f.read().strip()
    except FileNotFoundError:
        letzter_report = ""
    if letzter_report != heute:
        zustand = "verfuegbar" if verfuegbar_m else "ausverkauft"
        nachricht = f"Morgen-Report ({jetzt_de.strftime('%H:%M')}): Groesse {GESUCHTE_GROESSE} ist {zustand}."
        if verfuegbar_m:
            nachricht += f"\nJetzt bestellen: {KAUF_LINK}"
        print("Report faellig ->", nachricht)
        try:
            sende_telegram(nachricht)
            with open(REPORT_DATEI, "w") as f:
                f.write(heute)   # erst nach Erfolg merken
        except Exception as fehler:
            print(f"Report-Telegram fehlgeschlagen: {fehler}")
    else:
        print("Report heute bereits gesendet.")
else:
    print(f"Vor {REPORT_AB_STUNDE} Uhr (jetzt {jetzt_de.strftime('%H:%M')}) - kein Report.")

# --- 5. Monitor: nur bei Zustandswechsel melden ---
jetzt = "verfuegbar" if verfuegbar_m else "ausverkauft"

try:
    with open(STATUS_DATEI) as f:
        vorher = f.read().strip()
except FileNotFoundError:
    vorher = "unbekannt"

print(f"Monitor: vorher={vorher} | jetzt={jetzt}")

if jetzt != vorher:
    nachricht = None
    if jetzt == "verfuegbar":
        nachricht = f"Groesse {GESUCHTE_GROESSE} ist JETZT VERFUEGBAR!\n{KAUF_LINK}"
    elif jetzt == "ausverkauft" and vorher == "verfuegbar":
        nachricht = f"Groesse {GESUCHTE_GROESSE} ist wieder ausverkauft."
    if nachricht:
        print("Monitor-Alarm ->", nachricht)
        try:
            sende_telegram(nachricht)
        except Exception as fehler:
            print(f"Monitor-Telegram fehlgeschlagen: {fehler}")
            sys.exit(1)   # Status NICHT speichern -> naechster Lauf versucht erneut
    with open(STATUS_DATEI, "w") as f:
        f.write(jetzt)
else:
    print("Keine Aenderung.")
