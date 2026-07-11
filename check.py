import urllib.request

SEITE_URL = "https://blackroll.com/de/products/blackroll-compression-boots-second-chance"

anfrage = urllib.request.Request(SEITE_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(anfrage, timeout=30) as antwort:
    html = antwort.read().decode("utf-8", errors="ignore")

print(f"HTML-Laenge: {len(html)}")

# Zeige den Text rund um jedes Vorkommen von "available"
start = 0
nr = 0
while True:
    pos = html.find('"available"', start)
    if pos == -1:
        break
    nr += 1
    von = max(0, pos - 300)
    bis = min(len(html), pos + 120)
    print(f"\n===== TREFFER {nr} (Position {pos}) =====")
    print(html[von:bis])
    start = pos + 1

print(f"\nGesamt: {nr} Treffer")
