import os
import requests
import time
from datetime import datetime

# Gestione sicura della chiave API (rimuove eventuali spazi o apici indesiderati)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")

# Watchlist con dati di fallback "storici" (Settembre 2026) per evitare visualizzazioni N/D
WATCHLIST = [
    {"name": "Enel", "isin": "XS3358330820", "coupon": 3.875, "maturity": "2033", "fallback_price": 97.87, "fallback_ytm": 4.15},
    {"name": "Terna", "isin": "XS2655852726", "coupon": 3.875, "maturity": "2033", "fallback_price": 100.26, "fallback_ytm": 3.83},
    {"name": "E.ON", "isin": "XS3171591889", "coupon": 3.000, "maturity": "2031", "fallback_price": 97.98, "fallback_ytm": 3.42},
    {"name": "Orange", "isin": "FR001400AF72", "coupon": 2.375, "maturity": "2032", "fallback_price": 92.99, "fallback_ytm": 3.84},
    {"name": "Deutsche Telekom", "isin": "DE000A2TSDE2", "coupon": 1.750, "maturity": "2031", "fallback_price": 92.02, "fallback_ytm": 3.69},
    {"name": "Unilever", "isin": "XS2450200741", "coupon": 1.250, "maturity": "2031", "fallback_price": 91.23, "fallback_ytm": 3.39},
    {"name": "Iberdrola", "isin": "XS2455983861", "coupon": 1.375, "maturity": "2032", "fallback_price": 88.96, "fallback_ytm": 3.61},
    {"name": "Engie S.A.", "isin": "FR001400OJB9", "coupon": 3.625, "maturity": "2031", "fallback_price": 99.30, "fallback_ytm": 3.79},
    {"name": "AB InBev", "isin": "BE6248644013", "coupon": 3.250, "maturity": "2033", "fallback_price": 98.37, "fallback_ytm": 3.55},
    {"name": "Sanofi", "isin": "FR0014016SW6", "coupon": 3.375, "maturity": "2033", "fallback_price": 99.35, "fallback_ytm": 3.48}
]

def get_bond_quote(isin, fallback_p, fallback_y):
    """Recupera prezzo e YTM, usando i dati di fallback in caso di blocco da parte di Börse Frankfurt."""
    url = f"https://api.boerse-frankfurt.de/v1/data/quote_box/bond?isin={isin}"
    
    # Intestazioni complete per emulare un browser reale
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.boerse-frankfurt.de",
        "Referer": f"https://www.boerse-frankfurt.de/anleihe/{isin.lower()}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    for attempt in range(2):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                price = data.get("lastPrice")
                ytm = data.get("yieldToMaturity")
                
                # Se i dati sono numerici e validi, li usiamo
                if isinstance(price, (int, float)) and isinstance(ytm, (int, float)):
                    return {"price": price, "ytm": ytm, "source": "live"}
        except Exception as e:
            print(f"[{isin}] Tentativo {attempt+1} fallito: {e}")
        time.sleep(1)

    # In caso di errore o N/D, usiamo i nostri dati reali di fallback (con etichetta)
    return {"price": fallback_p, "ytm": fallback_y, "source": "archivio"}

def get_hardcoded_outlook():
    """Genera un commento di altissima qualità nel caso in cui le API di Gemini falliscano (es. Errore 404)."""
    return """
    <p><strong>Convenienza Fiscale Svizzera:</strong> Le attuali condizioni di mercato continuano a favorire l'acquisto di obbligazioni con quotazioni sotto la pari per gli investitori residenti in Svizzera. Titoli come <em>Iberdrola (88,96)</em>, <em>Unilever (91,23)</em>, <em>Deutsche Telekom (92,02)</em> e <em>Orange (92,99)</em> permettono di minimizzare la componente cedolare (soggetta a imposta ordinaria sul reddito) e di massimizzare il rendimento a scadenza sotto forma di capital gain, che risulta esente da imposte per i privati. I titoli vicini alla pari, come <em>Enel</em> o <em>Terna</em>, rimangono solidi ma offrono una minore ottimizzazione fiscale causa cedole più alte.</p>
    <p><strong>Outlook Tassi e Cambio:</strong> Il trend di allentamento monetario della BCE supporta il comparto obbligazionario corporate in Euro (Investment Grade), riducendo i rendimenti e favorendo un recupero dei prezzi (YTD positivo per la maggior parte delle emissioni). Tuttavia, per un investitore con riferimento in CHF, il rischio di cambio EUR/CHF rimane il fattore critico: la persistente forza del franco svizzero contro l'euro rischia di erodere parte dei rendimenti nominali, rendendo consigliabile un monitoraggio attivo del tasso di cambio (attualmente visibile nel grafico a lato) o la valutazione di coperture se non si desidera l'esposizione valutaria.</p>
    """

def generate_outlook(data_summary):
    """Chiama l'API di Gemini con fallback robusto in caso di errore (come il 404)."""
    if not GEMINI_API_KEY:
        print("⚠️ Gemini API Key mancante. Uso dell'analisi pre-configurata.")
        return get_hardcoded_outlook()

    prompt = f"""
    Dati obbligazioni EUR (Investitore svizzero):
    {data_summary}
    Genera due brevi paragrafi HTML (usa solo i tag <p> e <strong>):
    1. Commento sulle performance YTD del settore corporate e convenienza fiscale svizzera (enfatizza i bond sotto la pari).
    2. Outlook tassi BCE e impatto cambio EUR/CHF per la settimana.
    """
    
    # Lista di tentativi su URL e Modelli diversi per bypassare il 404
    api_attempts = [
        {"url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}", "headers": {"Content-Type": "application/json"}},
        {"url": f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}", "headers": {"Content-Type": "application/json"}}
    ]

    for api in api_attempts:
        try:
            res = requests.post(api["url"], json={"contents": [{"parts": [{"text": prompt}]}]}, headers=api["headers"], timeout=15)
            if res.status_code == 200:
                html_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                if html_text and "<p>" in html_text:
                    return html_text
            else:
                print(f"Tentativo API fallito con codice {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Errore connessione API: {e}")

    # Se tutti i tentativi falliscono (es. 404), restituiamo l'analisi di archivio
    print("⚠️ API di Gemini non raggiungibili o non configurate. Applicazione dell'outlook di fallback.")
    return get_hardcoded_outlook()

def main():
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    table_rows, data_for_llm = "", []

    print("Scansione mercato in corso...")
    for b in WATCHLIST:
        q = get_bond_quote(b["isin"], b["fallback_price"], b["fallback_ytm"])
        
        # Formattazione e marcatura in base all'origine del dato
        is_live = q.get("source") == "live"
        price_display = f"{q['price']:.2f}" if isinstance(q["price"], (int, float)) else q["price"]
        ytm_display = f"{q['ytm']:.2f}%" if isinstance(q["ytm"], (int, float)) else f"{q['ytm']}"
        
        source_badge = "" if is_live else " <small style='color:#a0a0a0; font-size:10px;' title='Dato di archivio per mancata risposta della borsa'>(storia)</small>"
        
        table_rows += f"<tr><td><strong>{b['name']}</strong></td><td>{b['isin']}</td><td>{b['coupon']}%</td><td>{b['maturity']}</td><td>{price_display}{source_badge}</td><td><strong>{ytm_display}</strong></td></tr>"
        data_for_llm.append(f"{b['name']} ({b['isin']}): Prezzo {price_display}, YTM {ytm_display}")

    print("Generazione dell'outlook...")
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
                </div>
            </div>

            <div class="footer">Generato tramite GitHub Actions e Gemini API (con dati d'archivio in caso di offline dei servizi). I dati hanno scopo informativo.</div>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Salvataggio completato!")

if __name__ == "__main__":
    main()
