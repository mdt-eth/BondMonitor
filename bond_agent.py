import os
import sys
import subprocess
import re

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE MANCANTI
# ==========================================
def install_dependencies():
    """Controlla le librerie necessarie e le installa se mancano."""
    packages = {
        "pandas": "pandas",
        "yfinance": "yfinance",
        "google.generativeai": "google-generativeai"
    }
    for module_name, pip_name in packages.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"[*] Rilevata carenza: '{pip_name}'. Installazione automatica in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

# Esegui il controllo prima di caricare il resto del codice
install_dependencies()

# Ora possiamo importare tutto in totale sicurezza
import pandas as pd
import yfinance as yf
import google.generativeai as genai

# ==========================================
# 1. CONFIGURAZIONE & SELEZIONE MODELLO AUTO
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY non trovata nelle variabili d'ambiente.")

genai.configure(api_key=API_KEY)


def get_latest_free_flash_model() -> str:
    """
    Ispeziona i modelli abilitati sul tuo account e seleziona automaticamente
    il modello Flash (free tier) di generazione più recente disponibile.
    """
    flash_candidates = []

    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            name = m.name.lower()
            # Filtra modelli Flash ed esclude varianti sperimentali di fine-tuning
            if "flash" in name and "tuning" not in name:
                match = re.search(r"gemini[^\d]*(\d+(?:\.\d+)?)", name)
                version = float(match.group(1)) if match else 0.0
                flash_candidates.append((version, m.name))

    if not flash_candidates:
        return "models/gemini-1.5-flash"

    # Ordina per versione numerica decrescente (es. 2.0 > 1.5)
    flash_candidates.sort(key=lambda x: x[0], reverse=True)
    return flash_candidates[0][1]


# ==========================================
# 2. RACCOLTA DATI OBBLIGAZIONARI (BOND DATA)
# ==========================================
def fetch_bond_yields():
    """
    Recupera i rendimenti di riferimento (US 10Y, US 2Y, US 30Y).
    """
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
# 3. ANALISI TRAMITE GEMINI
# ==========================================
def run_bond_monitor():
    best_model_name = get_latest_free_flash_model()
    print(f"[*] Modello selezionato: {best_model_name}")
    model = genai.GenerativeModel(best_model_name)

    macro_yields, portfolio = fetch_bond_yields()

    prompt = f"""
Sei un analista obbligazionario esperto. Analizza i seguenti dati di mercato e il portafoglio obbligazionario fornito:

### Rendimenti Benchmark (Ultima seduta):
{macro_yields.to_markdown() if not macro_yields.empty else "Dati live non disponibili"}

### Monitor Posizioni Obbligazionarie:
{portfolio.to_markdown(index=False)}

Fornisci un'analisi sintetica strutturata in:
1. **Dinamica dei Tassi & Curva**: Movimento dei benchmark e implicazioni (appiattimento/inclinazione).
2. **Valutazione Rischio Portafoglio**: Sensibilità ai tassi (Duration) e rischio di credito (Rating).
3. **Alert Operativi**: Eventuali segnali di criticità o opportunità di ribilanciamento.
"""

    print("[*] Generazione report in corso...\n")
    try:
        response = model.generate_content(prompt)
        print(response.text)
    except Exception as e:
        print(f"Errore durante l'analisi: {e}")

if __name__ == "__main__":
    run_bond_monitor()
