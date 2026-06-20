import base64, requests, sys, json

with open("arayuz_akisi.mmd", "r", encoding="utf-8") as f:
    diagram = f.read()

# Try JSON API first
try:
    resp = requests.post(
        "https://mermaid.ink/api/render",
        json={
            "code": diagram,
            "mermaid": {
                "theme": "dark",
                "themeVariables": {
                    "primaryColor": "#1a1a2e",
                    "primaryTextColor": "#ecf0f1",
                    "primaryBorderColor": "#e94560",
                    "lineColor": "#533483",
                    "secondaryColor": "#16213e",
                    "tertiaryColor": "#0f3460",
                    "fontFamily": "Segoe UI",
                    "fontSize": "12px",
                },
            },
        },
        timeout=30,
    )
    print(f"JSON API Status: {resp.status_code}")
    if resp.status_code == 200:
        with open("arayuz_akisi.png", "wb") as f:
            f.write(resp.content)
        print(f"Saved: {len(resp.content)} bytes")
        sys.exit(0)
except Exception as e:
    print(f"JSON API failed: {e}")

# Fallback: base64 URL encoding
encoded = base64.b64encode(diagram.encode("utf-8")).decode("ascii")
url = f"https://mermaid.ink/img/{encoded}?theme=dark"
resp = requests.get(url, timeout=30)
print(f"URL API Status: {resp.status_code}")
if resp.status_code == 200:
    with open("arayuz_akisi.png", "wb") as f:
        f.write(resp.content)
    print(f"Saved: {len(resp.content)} bytes")
else:
    print(f"Failed: {resp.text[:500]}")
    sys.exit(1)
