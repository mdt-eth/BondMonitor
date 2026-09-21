import os
import sys
import subprocess
import re
from datetime import datetime

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = ["pandas", "yfinance", "beautifulsoup4", "requests"]
    for pip_name in packages:
        try:
            __import__(pip_name if pip_name != "beautifulsoup4" else "bs4")
        except ImportError:
            print(f"[*] Installazione di {pip_name} in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. SCRAPER UNIVERSALE (5 Motori di Ricerca)
# ==========================================
def clean_price(value_str):
    """Estrae e converte formati di prezzo misti europei in float."""
    try:
        val = str(value_str).split()[0].replace('%', '').replace('G', '').replace('B', '').replace('€', '').strip()
        if not val or val == '-': return None
        return float(val.replace('.', '').replace(',', '.'))
    except (ValueError, AttributeError, IndexError):
        return None

def get_isin_prices(isin):
    """Cerca il prezzo a cascata su 5 portali finanziari europei."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    ultimo = None
    chiusura = None

    # 1. ARIVA.DE (Il database più completo per i bond XS e FR)
    try:
        url = f"https://www.ariva.de/{isin}/kurs"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.find('span', itemprop='price')
            if price_tag:
                ultimo = clean_price(price_tag.text)
            
            vortag_th = soup.find('th', string=re.compile("Vortag", re.I))
            if vortag_th and vortag_th.find_next_sibling('td'):
                chiusura = clean_price(vortag_th.find_next_sibling('td').text)
                
            if ultimo: return ultimo, (chiusura or ultimo)
    except Exception: pass

    # 2. FINANZEN.NET (Colosso tedesco per corporate bond)
    try:
        url = f"https://www.finanzen.net/anleihen/{isin}"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            parts = soup.get_text(separator='|', strip=True).lower().split('|')
            for i, part in enumerate(parts):
                if part == "aktuell" or "brief" in part:
                    for offset in range(1, 4):
                        if i + offset < len(parts):
                            val = re.sub(r'[^\d,]', '', parts[i + offset])
                            if val and ',' in val:
                                ultimo = clean_price(val)
                                break
                if "vortag" in part or "schluss" in part:
                    for offset in range(1, 4):
                        if i + offset < len(parts):
                            val = re.sub(r'[^\d,]', '', parts[i + offset])
                            if val and ',' in val:
                                chiusura = clean_price(val)
                                break
            if ultimo: return ultimo, (chiusura or ultimo)
    except Exception: pass

    # 3. TRADEGATE (Eccellente per i titoli scambiati su Xetra)
    try:
        url = f"https://www.tradegate.de/orderbuch.php?isin={isin}"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            ult_tag = soup.find(id='last')
            chiu_tag = soup.find(id='close')
            if ult_tag and ult_tag.text.strip():
                ultimo = clean_price(ult_tag.text)
            if chiu_tag and chiu_tag.text.strip():
                chiusura = clean_price(chiu_tag.text)
            if ultimo: return ultimo, (chiusura or ultimo)
    except Exception: pass

    # 4. BORSA ITALIANA & 5. TELEBORSA (Per BTP e bond retail IT)
    segments = ["mot/obbligazioni-corporate", "eurotlx/obbligazioni", "mot/euro-obbligazioni"]
    for segment in segments:
        try:
            url = f"https://www.borsaitaliana.it/borsa/obbligazioni/{segment}/scheda/{isin}.html"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200 and isin in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                parts = soup.get_text(separator='|', strip=True).lower().split('|')
                for i, part in enumerate(parts):
                    if "ultimo contratto" in part or part == "ultimo":
                        val = re.sub(r'[^\d,]', '', parts[i + 2])
                        if val: ultimo = clean_price(val)
                    if "chiusura precedente" in part:
                        val = re.sub(r'[^\d,]', '', parts[i + 2])
                        if val: chiusura = clean_price(val)
                if ultimo: return ultimo, (chiusura or ultimo)
        except Exception: pass

    return None, None


# ==========================================
# 2. RACCOLTA DATI 
# ==========================================
def fetch_bond_data():
    tickers_macro = {"US 10Y Yield": "^TNX", "US 2Y Yield": "^IRX", "US 30Y Yield": "^TYX"}
    macro_data = []
    for name, ticker in tickers_macro.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if not data.empty:
                current_yield = data["Close"].iloc[-1]
                prev_yield = data["Close"].iloc[-2]
                macro_data.append({
                    "Benchmark": name,
                    "Rendimento (%)": f"{current_yield:.2f}%",
                    "Chiusura Prec. (%)": f"{prev_yield:.2f}%",
                    "Variazione (bp)": f"{(current_yield - prev_yield) * 100:+.1f}"
                })
        except Exception: pass
            
    df_macro = pd.DataFrame(macro_data)

    portfolio_list = [
        {"Isin": "XS3358330820", "Nome": "Enel S.p.A. 3.875% 2033"},
        {"Isin": "XS2655852726", "Nome": "Terna S.p.A. 3.875% 2033"},
        {"Isin": "XS3171591889", "Nome": "E.ON 3.000% 2031"},
        {"Isin": "FR001400AF72", "Nome": "Orange S.A. 2.375% 2032"},
        {"Isin": "DE000A2TSDE2", "Nome": "Deutsche Telekom 1.750% 2031"},
        {"Isin": "XS2450200741", "Nome": "Unilever 1.250% 2031"},
        {"Isin": "XS2455983861", "Nome": "Iberdrola 1.375% 2032"},
        {"Isin": "FR001400OJB9", "Nome": "Engie S.A. 3.625% 2031"},
        {"Isin": "BE6248644013", "Nome": "AB InBev 3.250% 2033"},
        {"Isin": "FR0014016SW6", "Nome": "Sanofi 2.000%"}
    ]
    
    print("[*] Avvio scraping prezzi in tempo reale sui circuiti internazionali...")
    portfolio_data = []
    for bond in portfolio_list:
        print(f"    -> Ricerca {bond['Nome']} ({bond['Isin']})...")
        prezzo_oggi, prezzo_ieri = get_isin_prices(bond["Isin"])
        
        if prezzo_oggi:
            bond["Prezzo (€)"] = f"{prezzo_oggi:.2f}"
            bond["Chiusura Prec. (€)"] = f"{prezzo_ieri:.2f}"
            variazione_perc = ((prezzo_oggi - prezzo_ieri) / prezzo_ieri) * 100 if prezzo_ieri else 0
            bond["Variazione (%)"] = f"{variazione_perc:+.2f}%"
        else:
            bond["Prezzo (€)"] = "N/D"
            bond["Chiusura Prec. (€)"] = "N/D"
            bond["Variazione (%)"] = "N/D"
            
        portfolio_data.append(bond)
    
    df_portfolio = pd.DataFrame(portfolio_data)
    cols = ["Isin", "Nome", "Prezzo (€)", "Chiusura Prec. (€)", "Variazione (%)"]
    df_portfolio = df_portfolio[cols]

    return df_macro, df_portfolio


# ==========================================
# 3. GENERAZIONE DASHBOARD HTML + JS
# ==========================================
def generate_html_page(df_macro, df_portfolio):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_macro = df_macro.to_html(index=False, classes="data-table", justify="left") if not df_macro.empty else "<p>Dati non disponibili</p>"
    html_portfolio = df_portfolio.to_html(index=False, classes="data-table", justify="left")
    raw_text = f"BENCHMARK:\n{df_macro.to_string(index=False)}\n\nPORTAFOGLIO:\n{df_portfolio.to_string(index=False)}"

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bond Monitor Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; max-width: 950px; margin: auto; background-color: #fcfcfc; color: #333; }}
        h1 {{ color: #004494; border-bottom: 2px solid #004494; padding-bottom: 10px; }}
        h2 {{ color: #0056b3; font-size: 1.2em; margin-top: 30px; }}
        .timestamp {{ color: #777; font-size: 0.9em; margin-bottom: 20px; font-style: italic; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95em; background: white; }}
        .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .data-table th {{ background-color: #f4f6f8; }}
        .data-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .ai-panel {{ background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 25px; margin-top: 35px; }}
        #ai-btn {{ background-color: #004494; color: white; border: none; padding: 12px 24px; font-size: 1em; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        #ai-btn:disabled {{ background-color: #999; cursor: not-allowed; }}
        #ai-result {{ margin-top: 25px; padding-top: 20px; border-top: 1px dashed #ccc; }}
        .error {{ color: #d9534f; font-weight: bold; padding: 10px; border-left: 4px solid #d9534f; background: #fdf2f2; }}
    </style>
</head>
<body>
    <h1>Dashboard Bond Monitor</h1>
    <div class="timestamp">Dati aggiornati al: {timestamp}</div>
    <h2>Rendimenti Macro</h2>{html_macro}
    <h2>Shortlist Corporate (Copertura Internazionale)</h2>{html_portfolio}
    <div class="ai-panel">
        <h2>Genera Analisi</h2>
        <button id="ai-btn" onclick="generateAnalysis()">Elabora Dati con Gemini</button>
        <button onclick="localStorage.removeItem('gemini_api_key'); alert('Chiave rimossa.');" style="background:none;border:none;color:#666;text-decoration:underline;cursor:pointer;margin-left:15px;">Reset API Key</button>
        <div id="ai-result"></div>
    </div>
    <pre id="raw-data" style="display:none;">{raw_text}</pre>
    <script>
        async function generateAnalysis() {{
            let apiKey = localStorage.getItem('gemini_api_key');
            if (!apiKey) {{ apiKey = prompt("API Key Gemini:"); if (!apiKey) return; localStorage.setItem('gemini_api_key', apiKey); }}
            const btn = document.getElementById('ai-btn'), resDiv = document.getElementById('ai-result');
            btn.disabled = true; btn.innerText = "Elaborazione..."; resDiv.innerHTML = "<p><em>Lettura dati in corso...</em></p>";
            try {{
                const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${{apiKey}}`, {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{contents: [{{parts: [{{text: `Analizza questi dati estratti oggi:\\n\\n${{document.getElementById('raw-data').innerText}}\\n\\nFornisci un'analisi sintetica in HTML (usa solo <h3>, <ul>, <li>, <b>). Nessun blocco markdown.`}}]}}]}})
                }});
                if (!res.ok) throw new Error("Errore Google API: " + res.status);
                const data = await res.json();
                resDiv.innerHTML = data.candidates[0].content.parts[0].text.replace(/```html/gi, '').replace(/```/g, '');
            }} catch (e) {{ resDiv.innerHTML = `<p class="error">${{e.message}}</p>`; }} 
            finally {{ btn.disabled = false; btn.innerText = "Rigenera Analisi"; }}
        }}
    </script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)
    print("[*] Dashboard aggiornata in index.html!")

if __name__ == "__main__":
    macro, port = fetch_bond_data()
    generate_html_page(macro, port)
