import json, os, re, sys, urllib.parse, urllib.request

SEITE_URL = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"
KAUF_LINK = SEITE_URL
GESUCHTE_GROESSE = "S"
STATUS_DATEI = "status.txt"

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

# --- 2. Nuxt-Datenpaket (grosses Array) aus den <script>-Bloecken holen ---
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

# --- 3. Hilfsfunktion: Zahlen-Verweis in echten Wert aufloesen ---
def wert(idx):
    # Objektwerte im Nuxt-Paket sind Verweise (Zahlen) auf andere Array-Eintraege.
    if isinstance(idx, int) and 0 <= idx < len(arr):
        return arr[idx]
    return idx

# --- 4. Alle Varianten finden und Groesse -> Verfuegbarkeit zuordnen ---
def ist_variante(o):
    return isinstance(o, dict) and "available" in o and "sku" in o and "selectedOptions" in o

groessen = {}
for o in arr:
    if not ist_variante(o):
        continue
    verf = wert(o["available"])            # true / false
    groesse = None
    # bevorzugt ueber selectedOptions -> [{"name":..,"value":"M"}]
    so = wert(o["selectedOptions"])
    if isinstance(so, list) and so:
        erste = wert(so[0])
        if isinstance(erste, dict) and "value" in erste:
            groesse = wert(erste["value"])
    if not isinstance(groesse, str):       # Fallback: title
        groesse = wert(o.get("title"))
    if isinstance(groesse, str) and isinstance(verf, bool):
        groessen[groesse] = verf

print("Gefundene Groessen und Verfuegbarkeit:", groessen)

if GESUCHTE_GROESSE not in groessen:
    print(f"Groesse {GESUCHTE_GROESSE} nicht in den Daten gefunden.")
    sys.exit(0)

verfuegbar_m = groessen[GESUCHTE_GROESSE]

# --- 5. Report- bzw. Monitor-Logik (wie zuvor) ---
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
