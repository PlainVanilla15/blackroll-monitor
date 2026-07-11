import re, urllib.request

SEITE_URL = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"

anfrage = urllib.request.Request(SEITE_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(anfrage, timeout=30) as antwort:
    html = antwort.read().decode("utf-8", errors="ignore")

print(f"HTML-Laenge: {len(html)}")

# Alle <script>-Bloecke; zeige Anfang derer, die die Varianten-Daten enthalten
bloecke = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Anzahl script-Bloecke: {len(bloecke)}")

for i, b in enumerate(bloecke):
    if '"available"' in b or 'selectedOptions' in b:
        print(f"\n===== BLOCK {i} (Laenge {len(b)}) =====")
        print("ANFANG (erste 400 Zeichen):")
        print(b[:400])
        # zeige auch, ob Groessen-Buchstaben als Werte vorkommen
        for g in ['"S"', '"M"', '"L"']:
            print(f'  enthaelt {g}: {g in b}')
