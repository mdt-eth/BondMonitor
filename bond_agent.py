import os
import requests
import time
from datetime import datetime

# Pulizia e importazione della chiave API (rimuove eventuali apici inseriti per errore)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")

WATCHLIST = [
    {"name": "Enel", "isin": "XS3358330820", "coupon": 3.875, "maturity": "2033"},
    {"name": "Terna", "isin": "XS2655852726", "coupon": 3.875, "maturity": "2033"},
    {"name": "E.ON", "isin": "XS3171591889", "coupon": 3.000, "maturity": "2031"},
    {"name": "Orange", "isin": "FR001400AF72", "coupon": 2.375, "maturity": "2032"},
    {"name": "Deutsche Telekom", "isin": "DE000A2TSDE2", "coupon": 1.750, "maturity": "2031"},
    {"name": "Unilever", "isin": "XS2450200741", "coupon": 1.250, "maturity": "2031"},
    {"name": "Iberdrola", "isin": "XS2455983861", "coupon": 1.375, "maturity": "2032"},
    {"name": "Engie", "isin": "FR001400OJB9", "coupon": 3.625, "maturity": "2031"},
    {"name": "AB InBev", "isin": "BE6248644013", "coupon": 3.250, "maturity": "2033"},
    {"name": "Sanofi", "isin": "FR0014016SW6", "coupon": 3.375, "maturity": "2033"}
]

def get_bond_quote(isin):
    """Recupera prezzo e YTM con intestazioni reali e tentativi multipli."""
    url = f"https://api.boerse-frankfurt.de/v1/data/quote_box/bond?isin={isin}"
    
    # Intestazioni complete per emulare un browser reale e bypassare i blocchi IP
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.boerse-frankfurt.de",
        "Referer": f"https://www.boerse-frankfurt.de/anleihe/{isin.lower()}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Connection": "keep-alive"
    }

    # Prova fino a 3 volte con ritardo in caso di rate-limit
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                price = data.get("lastPrice", "N/D")
                ytm = data.get("yieldToMaturity", "N/D")
                
                # Se otteniamo dati validi, interrompiamo i tentativi
                if price != "N/D" or ytm != "N/D":
                    return {"price": price, "ytm": ytm}
            elif res.status_code == 429:
                print(f"[{isin}] Rate limited (429). Attesa prima di riprovare...")
                time.sleep(3)
            else:
                print(f"[{isin}] Errore HTTP {res.status_code} al tentativo {attempt+1}")
        except Exception as e:
            print(f"[{isin}] Eccezione {type(e).__name__} al tentativo {attempt+1}: {e}")
        time.sleep(1) # Piccolo delay tra tentativi

    return {"price": "N/D", "ytm": "N/D"}

def generate_outlook(data_summary):
    """Genera l'analisi macro ed evidenzia la mancanza della chiave se assente."""
    if not GEMINI_API_KEY:
        print("❌ ERRORE: GEMINI_API_KEY non configurata o vuota nei Secrets.")
        return """
        <p style='color:red;'>⚠️ <strong>Errore di configurazione:</strong> 
        La chiave GEMINI_API_KEY non è stata trovata o è vuota nei repository Secrets di GitHub. 
        Controlla in <em>Settings > Secrets and variables > Actions</em> di averla salvata correttamente.</p>
        """

    prompt = f"""
    Dati obbligazioni EUR (Investitore svizzero):
    {data_summary}
    Genera due brevi paragrafi HTML (usa solo i tag <p> e <strong>):
    1. Commento sulle performance YTD del settore corporate e convenienza fiscale svizzera (enfatizza i bond sotto la pari).
    2. Outlook tassi BCE e impatto cambio EUR/CHF per la settimana.
    """
    
    # Proviamo a usare gemini-1.5-flash che ha maggiore compatibilità e tassi di successo globali
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    try:
        res = requests.post(
            url, 
            json={"contents": [{"parts": [{"text": prompt}]}]}, 
            headers={"Content-Type": "application/json"},
            timeout=20
        )
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"❌ Gemini API errore {res.status_code}: {res.text}")
            return f"<p style='color:orange;'>⚠️ Gemini ha risposto con codice d'errore {res.status_code}. Riprova tra poco.</p>"
    except Exception as e:
        print(f"❌ Eccezione durante la connessione a Gemini: {e}")
        return f"<p style='color:orange;'>⚠️ Errore di connessione a Gemini ({type(e).__name__}). Controlla se l'API Key nei Secrets è corretta e attiva.</p>"

def main():
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    table_rows, data_for_llm = "", []

    print("Inizio scansione mercato obbligazionario...")
    for b in WATCHLIST:
        q = get_bond_quote(b["isin"])
        
        # Formattiamo i valori se presenti
        price_display = f"{q['price']:.2f}" if isinstance(q["price"], (int, float)) else q["price"]
        ytm_display = f"{q['ytm']:.2f}%" if isinstance(q["ytm"], (int, float)) else f"{q['ytm']}"
        
        # Genera riga HTML della tabella
        table_rows += f"<tr><td><strong>{b['name']}</strong></td><td>{b['isin']}</td><td>{b['coupon']}%</td><td>{b['maturity']}</td><td>{price_display}</td><td><strong>{ytm_display}</strong></td></tr>"
        data_for_llm.append(f"{b['name']} ({b['isin']}): Prezzo {price_display}, YTM {ytm_display}")
        print(f"-> {b['name']} terminato.")

    print("Scrittura report macro...")
    outlook_html = generate_outlook("\n".join(data_for_llm))

    html_content = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bond Monitor Svizzera</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px auto; max-width: 900px; line-height: 1.6; color: #333; padding: 0 20px; background-color: #f9f9f9; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }}
            th {{ background-color: #f6f8fa; color: #24292e; font-weight: 600; }}
            tr:hover {{ background-color: #f1f8ff; }}
            .grid-container {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 30px; }}
            .outlook {{ background: #f8f9fa; padding: 20px; border-left: 4px solid #0366d6; border-radius: 4px; }}
            .chart-container {{ min-height: 250px; }}
            .footer {{ margin-top: 40px; font-size: 0.8em; color: #6a737d; text-align: center; }}
            @media (max-width: 768px) {{ .grid-container {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Dashboard Bond Corporate EUR</h1>
            <p>Ultimo aggiornamento automatico: <strong>{date_str}</strong></p>
            
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>Emittente</th><th>ISIN</th><th>Cedola</th><th>Scad.</th><th>Prezzo</th><th>Rendimento (YTM)</th></tr>
                    {table_rows}
                </table>
            </div>

            <div class="grid-container">
                <div class="outlook">
                    <h3 style="margin-top:0;">📈 Outlook Macro e Fiscalità</h3>
                    {outlook_html}
                </div>
                
                <div class="chart-container">
                    <!-- TradingView Widget BEGIN -->
                    <div class="tradingview-widget-container">
                      <div class="tradingview-widget-container__widget"></div>
                      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
                      {{
                      "symbol": "FX:EURCHF",
                      "width": "100%",
                      "height": "100%",
                      "locale": "it",
                      "dateRange": "12M",
                      "colorTheme": "light",
                      "isTransparent": true,
                      "autosize": true,
                      "largeChartUrl": ""
                    }}
                      </script>
                    </div>
                    <!-- TradingView Widget END -->
                </div>
            </div>

            <div class="footer">Generato automaticamente tramite GitHub Actions e Gemini API. I dati hanno puro scopo informativo.</div>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Salvataggio completato in index.html!")

if __name__ == "__main__":
    main()
