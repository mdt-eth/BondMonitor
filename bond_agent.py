import os
import sys
import subprocess

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = {
        "pandas": "pandas",
        "yfinance": "yfinance",
        "tabulate": "tabulate",
        "google.genai": "google-genai"
    }
    
    try:
        __import__("google.generativeai")
        print("[*] Rimozione del pacchetto deprecato 'google-generativeai'...")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "google-generativeai", "--quiet"])
    except ImportError:
        pass

    for module_name, pip_name in packages.items():
        try:
            if module_name == "google.genai":
                __import__("google.genai")
            else:
                __import__(module_name)
        except ImportError:
            print(f"[*] Rilevata carenza: '{pip_name}'. Installazione automatica in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf
from google import genai
from google.genai import errors

# ==========================================
# 1. CONFIGURAZIONE & SELEZIONE MODELLO
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente.")

client = genai.Client(api_key=API_KEY)


def get_safest_flash_model() -> str:
    """
    Whitelist aggiornata alle versioni 3.x richieste dall'API.
    """
    preferred_models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.0-flash"
    ]
    
    try:
        available_models = [m.name.lower() for m in client.models.list()]
        clean_available = [name.replace("models/", "") for name in available_models]
        
        for pref in preferred_models:
            if pref in clean_available:
                return pref
    except Exception as e:
        print(f"[*] Impossibile leggere la lista dei modelli ({e}). Uso default.")
        
    # Fallback esatto suggerito dall'errore dell'API
    return "gemini-3.6-flash"


# ==========================================
# 2. RACCOLTA DATI OBBLIGAZIONARI (BOND DATA)
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
        {"Isin": "XS2345678901", "Nome": "Corp High Yield 5.5% 2029", "Prezzo": 98.10, "Duration": 4.1, "Rating": "BB+"},
    ]

    return pd.DataFrame(snapshot).T, pd.DataFrame(sample_portfolio)


# ==========================================
# 3. ANALISI TRAMITE GEMINI (API CHAT)
# ==========================================
def run_bond_monitor():
    best_model_name = get_safest_flash_model()
    print(f"[*] Modello selezionato: {best_model_name}")

    macro_yields, portfolio = fetch_bond_yields()

    prompt = f"""
Sei un analista obbligazionario esperto. Analizza i seguenti dati di mercato e il portafoglio obbligazionario fornito:

### Rendimenti Benchmark (Ultima seduta):
{macro_yields.to_markdown() if not macro_yields.empty else "Dati live non disponibili"}

### Monitor Posizioni Obbligazionarie:
{portfolio.to_markdown(index=False)}

Fornisci un'analisi sintetica strutturata in:
1. **Dinamica dei Tassi & Curva**: Movimento dei benchmark e implicazioni.
2. **Valutazione Rischio Portafoglio**: Sensibilità ai tassi e rischio di credito.
3. **Alert Operativi**: Eventuali segnali di criticità.
"""

    print("[*] Generazione report in corso...\n")
    try:
        # Passaggio da generate_content a chats.create().send_message() per rispettare le nuove direttive SDK
        chat = client.chats.create(model=best_model_name)
        response = chat.send_message(prompt)
        print(response.text)
    except errors.APIError as api_err:
        if api_err.code == 404:
            print(f"[*] Fallback d'emergenza diretto su gemini-3.6-flash...")
            chat = client.chats.create(model="gemini-3.6-flash")
            response = chat.send_message(prompt)
            print(response.text)
        else:
            print(f"Errore API: {api_err}")
    except Exception as e:
        print(f"Errore inaspettato durante l'analisi: {e}")

if __name__ == "__main__":
    run_bond_monitor()
