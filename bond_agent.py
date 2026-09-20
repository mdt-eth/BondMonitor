import os
import requests
import time
import json
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
MEMORY_FILE = "previous_data.json"

WATCHLIST = [
    {"name": "Enel", "isin": "XS3358330820", "coupon": 3.875, "maturity": "2033", "fallback_price": 97.87, "fallback_ytm": 4.15},
    {"name": "Terna", "isin": "XS2655852726", "coupon": 3.875, "maturity": "2033", "fallback_price": 100.26, "fallback_ytm": 3.83},
    {"name": "E.ON", "isin": "XS3171591889", "coupon": 3.000, "maturity": "2031", "fallback_price": 97.98, "fallback_ytm": 3.42},
    {"name": "Orange", "isin": "FR001400AF72", "coupon": 2.375, "maturity": "2032", "fallback_price": 92.99, "fallback_ytm": 3.84},
    {"name": "Deutsche Telekom", "isin": "DE000A2TSDE2", "coupon": 1.750, "maturity": "2031", "fallback_price": 92.02, "fallback_ytm": 3.69},
    {"name": "Unilever", "isin": "XS2450200741", "coupon": 1.250, "maturity": "2031", "fallback_price": 91.23, "fallback_ytm": 3.39},
    {"name": "Iberdrola", "isin": "XS2455983861", "coupon": 1.375, "maturity": "2032", "fallback_price": 88.96, "fallback_ytm": 3.61},
    {"name": "Engie", "isin": "FR001400OJB9", "coupon": 3.625, "maturity": "2031", "fallback_price": 99.30, "fallback_ytm": 3.79},
    {"name": "AB InBev", "isin": "BE6248644013", "coupon": 3.250, "maturity": "2033", "fallback_price": 98.37, "fallback_ytm": 3.55},
    {"name": "Sanofi", "isin": "FR0014016SW6", "coupon": 3.375, "maturity": "2033", "fallback_price": 99.35, "fallback_ytm": 3.48}
]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_memory(current_data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(current_data, f)

def get_bond_quote(isin, fallback_p, fallback_y):
    prot = "https"
    dom = "api.boerse-frankfurt.de"
    url = f"{prot}://{dom}/v1/data/quote_box/bond?isin={isin}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": f"{prot}://www.boerse-frankfurt.de",
        "Referer": f"{prot}://www.boerse-frankfurt.de/anleihe/{isin.lower()}"
    }
    for _ in range(2):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                price = data.get("lastPrice")
                ytm = data.get("yieldToMaturity")
                if isinstance(price, (int, float)) and isinstance(ytm, (int, float)):
                    return {"price": price, "ytm": ytm, "source": "live"}
        except:
            pass
        time.sleep(1)
    return {"price": fallback_p, "ytm": fallback_y, "source": "archivio"}

def generate_outlook(data_summary):
    if not GEMINI_API_KEY:
        return "<p>⚠️ API Key mancante nei Secrets.</p>"

    prompt = f"""
    Sei un consulente finanziario per un investitore svizzero.
    Ecco i dati attuali e i dati della rilevazione precedente (Prec) per i bond EUR:
    
    {data_summary}
    
    Scrivi ESATTAMENTE questo codice HTML sostituendo i tuoi commenti intelligenti dove indicato. 
    Usa un tono professionale. Non usare markdown extra (` ```html `), scrivi solo i tag HTML puri.

    <div class="insight-box">
        <h3 style="margin-top:0;">📈 Outlook Macro e Fiscalità</h3>
        <p>[Tuo commento sull'outlook dei tassi, andamento YTD e convenienza fiscale svizzera]</p>
    </div>
    <div class="insight-box" style="margin-top: 15px; border-left-color: #28a745;">
        <h3 style="margin-top:0;">🔄 Cosa è cambiato (Variazioni Giornaliere)</h3>
        <p>[Tuo commento descrittivo sulle variazioni di prezzo. Se prec è N/D, dai il benvenuto al primo avvio]</p>
    </div>
    """
    
    prot = "https"
    dom = "generativelanguage.googleapis.com"
    # Modello aggiornato alla versione Flash di ultima generazione (gratuita e senza quota 0)
    path = "/v1beta/models/gemini-3.1-flash:generateContent"
    url = f"{prot}://{dom}{path}?key={GEMINI_API_KEY}"
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, headers={"Content-Type": "application/json"}, timeout=25)
        
        if res.status_code == 200:
            data = res.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.replace("```html", "").replace("```", "").strip()
            else:
                return f"<p style='color:red;'>⚠️ Risposta vuota dall'IA.</p>"
        else:
            return f"<p style='color:red;'>⚠️ Errore API: Codice {res.status_code}. {res.text}</p>"
            
    except Exception as e:
        return f"<p style='color:red;'>⚠️ Errore di sistema durante la generazione: {e}</p>"

def main():
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    previous_memory = load_memory()
    current_memory = {}
    table_rows, data_for_llm = "", []

    for b in WATCHLIST:
        q = get_bond_quote(b["isin"], b["fallback_price"], b["fallback_ytm"])
        current_memory[b["isin"]] = {"price": q["price"], "ytm": q["ytm"]}
        
        price_disp = f"{q['price']:.2f}" if isinstance(q["price"], (int, float)) else q["price"]
        ytm_disp = f"{q['ytm']:.2f}%" if isinstance(q["ytm"], (int, float)) else f"{q['ytm']}"
        
        prev_data = previous_memory.get(b["isin"], {})
        prev_price = prev_data.get("price", "N/D")
        prev_price_disp = f"{prev_price:.2f}" if isinstance(prev_price, (int, float)) else prev_price
        
        trend_arrow = ""
        if isinstance(q["price"], (int, float)) and isinstance(prev_price, (int, float)):
            if q["price"] > prev_price: trend_arrow = " <span style='color:green'>▲</span>"
            elif q["price"] < prev_price: trend_arrow = " <span style='color:red'>▼</span>"

        table_rows += f"<tr><td><strong>{b['name']}</strong></td><td>{b['isin']}</td><td>{b['coupon']}%</td><td>{b['maturity']}</td><td>{price_disp}{trend_arrow}</td><td><strong>{ytm_disp}</strong></td></tr>"
        data_for_llm.append(f"{b['name']} ({b['isin']}): Prezzo Attuale {price_disp} (Prec: {prev_price_disp}), YTM {ytm_disp}")

    insights_html = generate_outlook("\n".join(data_for_llm))
    save_memory(current_memory)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bond Monitor Svizzera</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px auto; max-width: 950px; line-height: 1.6; color: #333; padding: 0 20px; background-color: #f9f9f9; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }}
            th {{ background-color: #f6f8fa; color: #24292e; font-weight: 600; }}
            tr:hover {{ background-color: #f1f8ff; }}
            .grid-container {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 30px; }}
            .analysis-col {{ display: flex; flex-direction: column; }}
            .insight-box {{ background: #f8f9fa; padding: 20px; border-left: 4px solid #0366d6; border-radius: 4px; }}
            .chart-container {{ min-height: 350px; }}
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
                <div class="analysis-col">
                    {insights_html}
                </div>
                
                <div class="chart-container">
                    <div class="tradingview-widget-container">
                      <div class="tradingview-widget-container__widget"></div>
                      <script type="text/javascript" src="[https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js](https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js)" async>
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

            <div class="footer">Generato automaticamente tramite GitHub Actions e Gemini API (Modello: 3.1-Flash).</div>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
