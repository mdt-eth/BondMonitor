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
# 1. SCRAPER AVANZATO (Borsa ITA + Teleborsa + Tradegate/Xetra)
# ==========================================
def clean_price(value_str):
    """Pulisce formati di prezzo misti e li converte in float Python."""
    try:
        # Rimuove lettere (es. 'G' o 'B' usate nelle borse tedesche), % e spazi
        val = str(value_str).split()[0].replace('%', '').replace('G', '').replace('B', '').replace('€', '').strip()
        return float(val.replace('.', '').replace(',', '.'))
    except (ValueError, AttributeError, IndexError):
        return None

def get_isin_prices(isin):
    """Motore di ricerca a cascata per trovare il prezzo dell'ISIN."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9"
    }
    
    ultimo = None
    chiusura = None

    # TENTATIVO 1: Tradegate (Proxy per Xetra / Francoforte) - Ottimo per bond esteri
    try:
        url_tg = f"https://www.tradegate.de/orderbuch.php?isin={isin}"
        res_tg = requests.get(url_tg, headers=headers, timeout=5)
        if res_tg.status_code == 200 and "orderbuch" in res_tg.text.lower():
            soup_tg = BeautifulSoup(res_tg.text, 'html.parser')
            
            ult_tag = soup_tg.find(id='last')
            chiu_tag = soup_tg.find(id='close')
            
            if ult_tag and ult_tag.text.strip():
                ultimo = clean_price(ult_tag.text)
            if chiu_tag and chiu_tag.text.strip():
                chiusura = clean_price(chiu_tag.text)
                
            if ultimo and chiusura:
                return ultimo, chiusura
    except Exception:
        pass

    # TENTATIVO 2: Borsa Italiana
    segments = ["mot/btp", "mot/obbligazioni-corporate", "mot/euro-obbligazioni", "eurotlx/obbligazioni"]
    for segment in segments:
        try:
            url = f"https://www.borsaitaliana.it/borsa/obbligazioni/{segment}/scheda/{isin}.html"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200 and isin in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                parts = soup.get_text(separator='|', strip=True).lower().split('|')
                
                for i, part in enumerate(parts):
                    if "ultimo contratto" in part or part == "ultimo":
                        for offset in range(1, 4):
                            if i + offset < len(parts):
                                val = re.sub(r'[^\d,]', '', parts[i + offset])
                                if val and ',' in val:
                                    ultimo = clean_price(val)
                                    break
                    if "chiusura precedente" in part or "prezzo di riferimento" in part:
                        for offset in range(1, 4):
                            if i + offset < len(parts):
                                val = re.sub(r'[^\d,]', '', parts[i + offset])
                                if val and ',' in val:
                                    chiusura = clean_price(val)
                                    break
                if ultimo and chiusura:
                    return ultimo, chiusura
        except Exception:
            pass

    # TENTATIVO 3: Teleborsa
    try:
        url_tb = f"https://www.teleborsa.it/Quotazioni/Ricerca?q={isin}"
        res_tb = requests.get(url_tb, headers=headers, timeout=5)
        if res_tb.status_code == 200:
            soup_tb = BeautifulSoup(res_tb.text, 'html.parser')
            ult_tag = soup_tb.find('span', {'id': re.compile(r'lblPrezzoUltimo', re.I)})
            chiu_tag = soup_tb.find('span', {'id': re.compile(r'lblPrezzoRiferimento', re.I)})
            
            if ult_tag and ult_tag.text.strip():
                ultimo = clean_price(ult_tag.text)
            if chiu_tag and chiu_tag.text.strip():
                chiusura = clean_price(chiu_tag.text)
                
            if ultimo and chiusura:
                return ultimo, chiusura
    except Exception:
        pass

    return None, None


# ==========================================
# 2. RACCOLTA DATI 
# ==========================================
def fetch_bond_data():
    # Benchmark Macro tramite YFinance
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
        except Exception:
            pass
            
    df_macro = pd.DataFrame(macro_data)

    # Shortlist Personalizzata dell'utente
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
        {"Isin": "FR0014016SW6", "Nome": "Sanofi 2.000% (?) (Stima)"}
    ]
    
    print("[*] Avvio scraping prezzi in tempo reale...")
    portfolio_data = []
    for bond in portfolio_list:
        print(f"    -> Ricerca {bond['Nome']} ({bond['Isin']})...")
        prezzo_oggi, prezzo_ieri = get_isin_prices(bond["Isin"])
        
        if prezzo_oggi and prezzo_ieri:
            bond["Prezzo (€)"] = f"{prezzo_oggi:.2f}"
            bond["Chiusura Prec. (€)"] = f"{prezzo_ieri:.2f}"
            variazione_perc = ((prezzo_oggi - prezzo_ieri) / prezzo_ieri) * 100
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
    
    raw_text_for_prompt = f"BENCHMARK:\n{df_macro.to_string(index=False)}\n\nPORTAFOGLIO:\n{df_portfolio.to_string(index=False)}"

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bond Monitor Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; max-width: 950px; margin: auto; color: #333; line-height: 1.5; background-color: #fcfcfc; }}
        h1 {{ color: #004494; border-bottom: 2px solid #004494; padding-bottom: 10px; }}
        h2 {{ color: #0056b3; font-size: 1.2em; margin-top: 30px; }}
        .timestamp {{ color: #777; font-size: 0.9em; margin-bottom: 20px; font-style: italic; }}
        
        .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95em; box-shadow: 0 1px 3px rgba(0,0,0,0.1); background: white; }}
        .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .data-table th {{ background-color: #f4f6f8; font-weight: bold; color: #333; }}
        .data-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
        
        .ai-panel {{ background: #ffffff; border: 1px solid #e9ecef; border-radius: 8px; padding: 25px; margin-top: 35px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        #ai-btn {{ background-color: #004494; color: white; border: none; padding: 12px 24px; font-size: 1em; border-radius: 6px; cursor: pointer; transition: background 0.3s; font-weight: bold; }}
        #ai-btn:hover {{ background-color: #003370; }}
        #ai-btn:disabled {{ background-color: #999; cursor: not-allowed; }}
        
        #ai-result {{ margin-top: 25px; padding-top: 20px; border-top: 1px dashed #ccc; }}
        .error {{ color: #d9534f; font-weight: bold; padding: 10px; border-left: 4px solid #d9534f; background: #fdf2f2; }}
    </style>
</head>
<body>
    <h1>Dashboard Bond Monitor</h1>
    <div class="timestamp">Dati raccolti in tempo reale il: {timestamp}</div>
    
    <h2>Rendimenti Macro (Benchmark)</h2>
    {html_macro}
    
    <h2>Shortlist Portafoglio (Corporate & Sovereign)</h2>
    {html_portfolio}

    <div class="ai-panel">
        <h2>Genera Analisi con Gemini</h2>
        <p>Clicca il bottone per generare il commento finanziario basato sulle chiusure odierne.</p>
        <button id="ai-btn" onclick="generateAnalysis()">Elabora Dati</button>
        <button id="reset-key-btn" onclick="resetApiKey()" style="background:none; border:none; color:#666; text-decoration:underline; font-size:0.8em; cursor:pointer; margin-left:15px;">Aggiorna API Key</button>
        
        <div id="ai-result"></div>
    </div>

    <pre id="raw-data" style="display:none;">{raw_text_for_prompt}</pre>

    <script>
        function resetApiKey() {{
            localStorage.removeItem('gemini_api_key');
            alert('Chiave API cancellata. Ti verrà richiesta al prossimo click.');
        }}

        async function generateAnalysis() {{
            let apiKey = localStorage.getItem('gemini_api_key');
            if (!apiKey) {{
                apiKey = prompt("Inserisci la tua API Key di Gemini:");
                if (!apiKey) return;
                localStorage.setItem('gemini_api_key', apiKey);
            }}

            const btn = document.getElementById('ai-btn');
            const resultDiv = document.getElementById('ai-result');
            
            btn.disabled = true;
            btn.innerText = "Consultazione in corso...";
            resultDiv.innerHTML = "<p><em>Elaborazione dell'analisi sui bond odierni...</em></p>";

            const rawData = document.getElementById('raw-data').innerText;
            const promptText = `Sei un analista obbligazionario. Analizza questi dati estratti oggi:\\n\\n${{rawData}}\\n\\nFornisci un'analisi sintetica. Evidenzia quali titoli hanno registrato le variazioni più interessanti. FORMATTA LA TUA RISPOSTA IN HTML (usa i tag <h3>, <ul>, <li>, <b>). Non includere markdown.`;

            try {{
                const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${{apiKey}}`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        contents: [{{ parts: [{{ text: promptText }}] }}]
                    }})
                }});

                if (!response.ok) {{
                    if(response.status === 400 || response.status === 403) {{
                        localStorage.removeItem('gemini_api_key');
                        throw new Error("La chiave API non è valida. Riprova.");
                    }}
                    throw new Error("Errore API Google: " + response.status);
                }}

                const data = await response.json();
                let htmlContent = data.candidates[0].content.parts[0].text;
                htmlContent = htmlContent.replace(/```html/gi, '').replace(/```/g, '').trim();
                
                resultDiv.innerHTML = htmlContent;
            }} catch (error) {{
                resultDiv.innerHTML = `<p class="error">Si è verificato un errore: ${{error.message}}</p>`;
            }} finally {{
                btn.disabled = false;
                btn.innerText = "Rigenera Analisi";
            }}
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("[*] Dashboard HTML salvata in index.html!")

if __name__ == "__main__":
    macro, port = fetch_bond_data()
    generate_html_page(macro, port)
