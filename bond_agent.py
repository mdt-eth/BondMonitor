import os
import requests
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
    url = f"https://api.boerse-frankfurt.de/v1/data/quote_box/bond?isin={isin}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return {"price": data.get("lastPrice", "N/D"), "ytm": data.get("yieldToMaturity", "N/D")}
    except Exception:
        pass
    return {"price": "N/D", "ytm": "N/D"}

def generate_outlook(data_summary):
    if not GEMINI_API_KEY: return "<p>⚠️ Chiave API mancante.</p>"
    prompt = f"""
    Dati obbligazioni EUR (Investitore svizzero):
    {data_summary}
    Genera due paragrafi HTML (usa solo i tag <p> e <strong>):
    1. Commento sulle performance YTD del settore corporate e convenienza fiscale svizzera (enfatizza i bond sotto la pari).
    2. Outlook tassi BCE e impatto cambio EUR/CHF per la settimana.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass
    return "<p>Errore di connessione API Gemini.</p>"

def main():
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    table_rows, data_for_llm = "", []

    for b in WATCHLIST:
        q = get_bond_quote(b["isin"])
        table_rows += f"<tr><td><strong>{b['name']}</strong></td><td>{b['isin']}</td><td>{b['coupon']}%</td><td>{b['maturity']}</td><td>{q['price']}</td><td><strong>{q['ytm']}%</strong></td></tr>"
        data_for_llm.append(f"{b['name']} ({b['isin']}): Prezzo {q['price']}, YTM {q['ytm']}%")

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

if __name__ == "__main__":
    main()
