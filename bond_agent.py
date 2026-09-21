import os
import sys
import subprocess
from datetime import datetime

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = ["pandas", "yfinance", "requests"]
    for pip_name in packages:
        try:
            __import__(pip_name)
        except ImportError:
            print(f"[*] Installazione di {pip_name} in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf
import requests

# ==========================================
# 1. RACCOLTA DATI (YFinance + EODHD API Avanzato)
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
        except Exception: pass
            
    df_macro = pd.DataFrame(macro_data)

    # Shortlist Personalizzata 
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
        {"Isin": "FR0014016SW6", "Nome": "Sanofi 3.375 2033%"}
    ]
    
    eodhd_key = os.environ.get("EODHD_API_KEY")
    if not eodhd_key:
        print("\n[!] ERRORE CRITICO: EODHD_API_KEY non trovata. GitHub non sta leggendo il Secret!")
    
    print("\n[*] Avvio interrogazione EODHD per i corporate bond...")
    portfolio_data = []
    
    for bond in portfolio_list:
        prezzo_oggi, prezzo_ieri = None, None
        trovato = False
        
        if eodhd_key:
            # Prova a cascata i listini di Francoforte, Xetra e il listino generico Bond
            for suffix in ["F", "XFRA", "BOND", "MU"]:
                url = f"https://eodhd.com/api/real-time/{bond['Isin']}.{suffix}?api_token={eodhd_key}&fmt=json"
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        data = res.json()
                        val_oggi = data.get("close", "NA")
                        val_ieri = data.get("previousClose", "NA")
                        
                        if val_oggi != "NA" and float(val_oggi) > 0:
                            prezzo_oggi = float(val_oggi)
                            prezzo_ieri = float(val_ieri) if val_ieri != "NA" else None
                            print(f"    -> {bond['Nome']}: TROVATO sul listino .{suffix}")
                            trovato = True
                            break
                    elif res.status_code == 403:
                        print(f"    -> [ERRORE 403] API Key EODHD non valida o permessi negati.")
                        break
                except Exception:
                    pass
            
            if not trovato:
                 print(f"    -> {bond['Nome']}: Non trovato su EODHD o nessun dato in tempo reale disponibile.")
        
        if prezzo_oggi:
            bond["Prezzo (€)"] = f"{prezzo_oggi:.2f}"
            bond["Chiusura Prec. (€)"] = f"{prezzo_ieri:.2f}" if prezzo_ieri else "N/D"
            if prezzo_ieri:
                variazione_perc = ((prezzo_oggi - prezzo_ieri) / prezzo_ieri) * 100
                bond["Variazione (%)"] = f"{variazione_perc:+.2f}%"
            else:
                bond["Variazione (%)"] = "N/D"
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
# 2. GENERAZIONE DASHBOARD HTML + JS
# ==========================================
def generate_html_page(df_macro, df_portfolio):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    html_macro = df_macro.to_html(index=False, classes="data-table", justify="left") if not df_macro.empty else "<p>Dati Macro non disponibili</p>"
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
    <div class="timestamp">Dati API aggiornati al: {timestamp}</div>
    <h2>Rendimenti Macro</h2>{html_macro}
    <h2>Shortlist Corporate (Copertura Ufficiale EODHD)</h2>{html_portfolio}
    <div class="ai-panel">
        <h2>Genera Analisi</h2>
        <button id="ai-btn" onclick="generateAnalysis()">Elabora Dati con Gemini</button>
        <button onclick="localStorage.removeItem('gemini_api_key'); alert('Chiave Gemini rimossa.');" style="background:none;border:none;color:#666;text-decoration:underline;cursor:pointer;margin-left:15px;">Reset API Key Gemini</button>
        <div id="ai-result"></div>
    </div>
    <pre id="raw-data" style="display:none;">{raw_text}</pre>
    <script>
        async function generateAnalysis() {{
            let apiKey = localStorage.getItem('gemini_api_key');
            if (!apiKey) {{ apiKey = prompt("Inserisci la tua API Key Gemini (viene salvata solo nel browser):"); if (!apiKey) return; localStorage.setItem('gemini_api_key', apiKey); }}
            const btn = document.getElementById('ai-btn'), resDiv = document.getElementById('ai-result');
            btn.disabled = true; btn.innerText = "Elaborazione in corso..."; resDiv.innerHTML = "<p><em>Lettura dati oracolo in corso...</em></p>";
            try {{
                const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${{apiKey}}`, {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{contents: [{{parts: [{{text: `Sei un analista obbligazionario. Analizza questi dati estratti oggi:\\n\\n${{document.getElementById('raw-data').innerText}}\\n\\nFornisci un'analisi sintetica in HTML (usa solo <h3>, <ul>, <li>, <b>). Nessun blocco markdown.`}}]}}]}})
                }});
                if (!res.ok) throw new Error("Errore Google API: " + res.status);
                const data = await res.json();
                resDiv.innerHTML = data.candidates[0].content.parts[0].text.replace(/```html/gi, '').replace(/```/g, '');
            }} catch (e) {{ resDiv.innerHTML = `<p class="error">${{e.message}}</p>`; }} 
            finally {{ btn.disabled = false; btn.innerText = "Rigenera Analisi"; }}
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("[*] Dashboard API salvata in index.html!")

if __name__ == "__main__":
    macro, port = fetch_bond_data()
    generate_html_page(macro, port)
