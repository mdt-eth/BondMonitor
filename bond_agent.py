import os
import sys
import subprocess
from datetime import datetime

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = ["pandas", "yfinance"] # google-genai non serve più in Python!
    for pip_name in packages:
        try:
            __import__(pip_name)
        except ImportError:
            print(f"[*] Installazione di {pip_name} in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf

# ==========================================
# 1. RACCOLTA DATI OBBLIGAZIONARI 
# ==========================================
def fetch_bond_data():
    # Benchmark Macro
    tickers_macro = {
        "US 10Y Yield": "^TNX",
        "US 2Y Yield": "^IRX",
        "US 30Y Yield": "^TYX",
    }
    
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

    # Shortlist Portafoglio 
    # Nota: su yfinance alcuni BTP non hanno ticker perfetti, usiamo dati proxy o strutturati per l'esempio
    portfolio = [
        {"Isin": "IT0005436693", "Nome": "BTP 0.95% Mar 2037", "Prezzo": 68.50, "Chiusura Prec.": 68.10, "Duration": 11.2, "Rating": "BBB"},
        {"Isin": "DE0001102580", "Nome": "Bund 0.0% Feb 2032", "Prezzo": 79.20, "Chiusura Prec.": 79.45, "Duration": 7.8, "Rating": "AAA"},
    ]
    
    df_portfolio = pd.DataFrame(portfolio)
    # Calcolo variazione % per il portafoglio
    df_portfolio["Variazione (%)"] = ((df_portfolio["Prezzo"] - df_portfolio["Chiusura Prec."]) / df_portfolio["Chiusura Prec."] * 100).apply(lambda x: f"{x:+.2f}%")
    
    # Riordino le colonne per chiarezza
    cols = ["Isin", "Nome", "Prezzo", "Chiusura Prec.", "Variazione (%)", "Duration", "Rating"]
    df_portfolio = df_portfolio[cols]

    return df_macro, df_portfolio

# ==========================================
# 2. GENERAZIONE DASHBOARD HTML + JS
# ==========================================
def generate_html_page(df_macro, df_portfolio):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Convertiamo i DataFrame in tabelle HTML pulite
    html_macro = df_macro.to_html(index=False, classes="data-table", justify="left") if not df_macro.empty else "<p>Dati non disponibili</p>"
    html_portfolio = df_portfolio.to_html(index=False, classes="data-table", justify="left")
    
    # Il testo grezzo che verrà inviato a Gemini dal Javascript
    raw_text_for_prompt = f"BENCHMARK:\n{df_macro.to_string(index=False)}\n\nPORTAFOGLIO:\n{df_portfolio.to_string(index=False)}"

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bond Monitor Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; max-width: 900px; margin: auto; color: #333; line-height: 1.5; }}
        h1 {{ color: #004494; border-bottom: 2px solid #004494; padding-bottom: 10px; }}
        h2 {{ color: #0056b3; font-size: 1.2em; margin-top: 30px; }}
        .timestamp {{ color: #777; font-size: 0.9em; margin-bottom: 20px; font-style: italic; }}
        
        .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95em; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        .data-table th {{ background-color: #f4f6f8; font-weight: bold; color: #333; }}
        .data-table tr:nth-child(even) {{ background-color: #fcfcfc; }}
        
        .ai-panel {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-top: 30px; }}
        #ai-btn {{ background-color: #004494; color: white; border: none; padding: 10px 20px; font-size: 1em; border-radius: 5px; cursor: pointer; transition: background 0.3s; }}
        #ai-btn:hover {{ background-color: #003370; }}
        #ai-btn:disabled {{ background-color: #999; cursor: not-allowed; }}
        
        #ai-result {{ margin-top: 20px; padding-top: 15px; border-top: 1px dashed #ccc; }}
        .error {{ color: #d9534f; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Dashboard Bond Monitor</h1>
    <div class="timestamp">Dati aggiornati al: {timestamp}</div>
    
    <h2>Dati Macro (Benchmark)</h2>
    {html_macro}
    
    <h2>Shortlist Portafoglio</h2>
    {html_portfolio}

    <!-- Sezione AI Generativa Client-Side -->
    <div class="ai-panel">
        <h2>Analisi Smart</h2>
        <p>I dati sono pronti. Clicca il bottone per generare il commento tramite l'API di Gemini.</p>
        <button id="ai-btn" onclick="generateAnalysis()">Genera Analisi con AI</button>
        <button id="reset-key-btn" onclick="resetApiKey()" style="background:none; border:none; color:#666; text-decoration:underline; font-size:0.8em; cursor:pointer; margin-left:15px;">Cambia API Key</button>
        
        <div id="ai-result"></div>
    </div>

    <!-- Dati grezzi nascosti per il prompt JS -->
    <pre id="raw-data" style="display:none;">{raw_text_for_prompt}</pre>

    <script>
        function resetApiKey() {{
            localStorage.removeItem('gemini_api_key');
            alert('Chiave API rimossa dal browser. Ti verrà richiesta al prossimo utilizzo.');
        }}

        async function generateAnalysis() {{
            let apiKey = localStorage.getItem('gemini_api_key');
            if (!apiKey) {{
                apiKey = prompt("Inserisci la tua API Key di Gemini (verrà salvata solo nel tuo browser per sicurezza, non sul server):");
                if (!apiKey) return;
                localStorage.setItem('gemini_api_key', apiKey);
            }}

            const btn = document.getElementById('ai-btn');
            const resultDiv = document.getElementById('ai-result');
            
            btn.disabled = true;
            btn.innerText = "Connessione a Gemini in corso...";
            resultDiv.innerHTML = "<p><em>Elaborazione dell'analisi sui tassi e sui bond. Attendere...</em></p>";

            const rawData = document.getElementById('raw-data').innerText;
            const promptText = `Sei un analista obbligazionario. Analizza questi dati estratti oggi:\\n\\n${{rawData}}\\n\\nFornisci un'analisi sintetica strutturata. FORMATTA LA TUA RISPOSTA IN HTML (usa i tag <h3>, <ul>, <li>, <b>). Non includere markdown come \`\`\`html.`;

            try {{
                // Chiamata REST diretta ai server Google dal browser
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
                        throw new Error("La chiave API non è valida o non ha i permessi. La chiave è stata rimossa, riprova.");
                    }}
                    throw new Error("Errore API dal server Google: " + response.status);
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
    print("[*] Dashboard HTML aggiornata con successo!")

if __name__ == "__main__":
    macro, port = fetch_bond_data()
    generate_html_page(macro, port)
