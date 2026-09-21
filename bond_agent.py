import os
import sys
import subprocess
from datetime import datetime

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = ["pandas", "yfinance", "tabulate", "google-genai"]
    
    try:
        __import__("google.generativeai")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "google-generativeai", "--quiet"])
    except ImportError:
        pass

    for pip_name in packages:
        try:
            if pip_name == "google-genai":
                __import__("google.genai")
            else:
                __import__(pip_name)
        except ImportError:
            print(f"[*] Installazione di {pip_name} in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf
from google import genai

# ==========================================
# 1. CONFIGURAZIONE API
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente.")

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3.6-flash"


# ==========================================
# 2. RACCOLTA DATI OBBLIGAZIONARI 
# ==========================================
def fetch_bond_yields():
    tickers = {
        "US 10Y Yield": "^TNX",
        "US 2Y Yield": "^IRX",
        "US 30Y Yield": "^TYX",
    }

    snapshot = {}
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if not data.empty:
                current_yield = data["Close"].iloc[-1]
                prev_yield = data["Close"].iloc[-2]
                delta_bp = (current_yield - prev_yield) * 100
                snapshot[name] = {
                    "Rendimento (%)": round(current_yield, 2),
                    "Variazione 1G (bp)": round(delta_bp, 1),
                }
        except Exception:
            pass

    sample_portfolio = [
        {"Isin": "IT0005436693", "Nome": "BTP 0.95% Mar 2037", "Prezzo": 68.50, "Duration": 11.2, "Rating": "BBB"},
        {"Isin": "DE0001102580", "Nome": "Bund 0.0% Feb 2032", "Prezzo": 79.20, "Duration": 7.8, "Rating": "AAA"},
    ]

    return pd.DataFrame(snapshot).T, pd.DataFrame(sample_portfolio)


# ==========================================
# 3. GENERAZIONE HTML CON GEMINI 
# ==========================================
def generate_html_page(content_html):
    """Crea la struttura della pagina index.html e la salva"""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bond Monitor</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; max-width: 800px; margin: auto; color: #333; }}
        h1 {{ color: #004494; border-bottom: 2px solid #004494; padding-bottom: 10px; }}
        h2 {{ color: #0056b3; font-size: 1.2em; margin-top: 20px; }}
        .timestamp {{ color: #777; font-size: 0.9em; margin-bottom: 30px; font-style: italic; }}
        .error {{ color: red; font-weight: bold; border: 1px solid red; padding: 10px; background: #ffe6e6; }}
    </style>
</head>
<body>
    <h1>Report Bond Monitor</h1>
    <div class="timestamp">Ultimo aggiornamento: {timestamp}</div>
    {content_html}
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("[*] File index.html generato con successo!")

def run_bond_monitor():
    print(f"[*] Inizializzazione con modello fisso: {MODEL_ID}")
    
    macro_yields, portfolio = fetch_bond_yields()

    prompt = f"""
Sei un analista obbligazionario. Analizza i seguenti dati:

Benchmark:
{macro_yields.to_markdown() if not macro_yields.empty else "N/A"}

Portafoglio:
{portfolio.to_markdown(index=False)}

Fornisci un'analisi sintetica in 3 punti. 
FORMATTA LA TUA RISPOSTA DIRETTAMENTE IN CODICE HTML. 
Usa solo i tag <h2>, <ul>, <li>, <b> e <p>. Non usare il markdown e non mettere backtick (```html) attorno alla risposta.
"""

    print("[*] Recupero dati completato. Generazione report in corso...\n")
    try:
        chat = client.chats.create(model=MODEL_ID)
        response = chat.send_message(prompt)
        
        # Pulisce eventuali formattazioni extra di Gemini
        clean_html = response.text.replace("```html", "").replace("```", "").strip()
        generate_html_page(clean_html)
        
    except Exception as e:
        error_msg = f'<div class="error">Errore di aggiornamento API: {e}</div>'
        generate_html_page(error_msg)
        print(f"Errore API, ma stampato nell'HTML: {e}")

if __name__ == "__main__":
    run_bond_monitor()
