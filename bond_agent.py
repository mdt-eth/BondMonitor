import os
import sys
import subprocess
from datetime import datetime

# ==========================================
# 0. AUTO-INSTALLAZIONE DIPENDENZE
# ==========================================
def install_dependencies():
    packages = ["pandas", "yfinance", "feedparser", "requests"]
    for pip_name in packages:
        try:
            __import__(pip_name)
        except ImportError:
            print(f"[*] Installazione di {pip_name} in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

install_dependencies()

import pandas as pd
import yfinance as yf
import feedparser

# ==========================================
# 1. RACCOLTA DATI (Macro + News RSS)
# ==========================================
def fetch_market_data():
    # 1. Benchmark Macro (YFinance)
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

    # 2. Portafoglio Target (Statico - serve come contesto per Gemini)
    portfolio_list = [
        {"Isin": "XS3358330820", "Nome": "Enel 3.875% 2033", "Settore": "Utility"},
        {"Isin": "XS2655852726", "Nome": "Terna 3.875% 2033", "Settore": "Utility"},
        {"Isin": "XS3171591889", "Nome": "E.ON 3.000% 2031", "Settore": "Utility"},
        {"Isin": "FR001400AF72", "Nome": "Orange 2.375% 2032", "Settore": "Telecom"},
        {"Isin": "DE000A2TSDE2", "Nome": "Deutsche Telekom 1.750% 2031", "Settore": "Telecom"},
        {"Isin": "XS2450200741", "Nome": "Unilever 1.250% 2031", "Settore": "Consumer"},
        {"Isin": "XS2455983861", "Nome": "Iberdrola 1.375% 2032", "Settore": "Utility"},
        {"Isin": "FR001400OJB9", "Nome": "Engie 3.625% 2031", "Settore": "Utility"},
        {"Isin": "BE6248644013", "Nome": "AB InBev 3.250% 2033", "Settore": "Consumer"},
        {"Isin": "FR0014016SW6", "Nome": "Sanofi", "Settore": "Pharma"}
    ]
    df_portfolio = pd.DataFrame(portfolio_list)

    # 3. Market Intelligence (Lettura Feed RSS Finanziari)
    print("[*] Download delle ultime news dai Feed RSS Istituzionali...")
    rss_feeds = [
        ("BCE (European Central Bank)", "https://www.ecb.europa.eu/rss/press.html"),
        ("Yahoo Finance (Bonds)", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^TNX,^TYX,^IRX"),
        ("CNBC Finance", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664")
    ]
    
    news_items = []
    for source, url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                news_items.append({
                    "Fonte": source,
                    "Titolo": entry.title,
                    "Data": entry.get("published", "Oggi"),
                    "Link": entry.link
                })
        except Exception as e:
            print(f"Errore lettura feed {source}: {e}")
            
    df_news = pd.DataFrame(news_items)
    return df_macro, df_portfolio, df_news


# ==========================================
# 2. GENERAZIONE DASHBOARD HTML + JS
# ==========================================
def generate_html_page(df_macro, df_portfolio, df_news):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    html_macro = df_macro.to_html(index=False, classes="data-table", justify="left") if not df_macro.empty else "<p>Dati Macro non disponibili</p>"
    html_portfolio = df_portfolio.to_html(index=False, classes="data-table", justify="left")
    
    html_news = "<ul class='news-list'>"
    for _, row in df_news.iterrows():
        html_news += f"<li><span class='source'>[{row['Fonte']}]</span> <a href='{row['Link']}' target='_blank'>{row['Titolo']}</a> <i>({row['Data']})</i></li>"
    html_news += "</ul>"

    raw_text = f"""
1. RENDIMENTI MACRO ODIERNI:
{df_macro.to_string(index=False)}

2. IL MIO PORTAFOGLIO CORPORATE (Elenco Titoli e Settori target):
{df_portfolio.to_string(index=False)}

3. ULTIME NOTIZIE E COMUNICATI DI MERCATO (Feed RSS):
{df_news[['Fonte', 'Titolo']].to_string(index=False)}
"""

    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bond Market Intelligence</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; max-width: 1000px; margin: auto; background-color: #f8f9fc; color: #2c3e50; line-height: 1.6; }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #3182ce; padding-bottom: 10px; font-size: 2em; }}
        h2 {{ color: #2b6cb0; font-size: 1.3em; margin-top: 35px; border-left: 4px solid #3182ce; padding-left: 10px; }}
        .timestamp {{ color: #718096; font-size: 0.9em; margin-bottom: 25px; font-style: italic; }}
        
        .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95em; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        .data-table th, .data-table td {{ border: 1px solid #e2e8f0; padding: 12px; text-align: left; }}
        .data-table th {{ background-color: #ebf4ff; color: #2c3e50; font-weight: 600; }}
        .data-table tr:nth-child(even) {{ background-color: #f7fafc; }}
        
        .news-list {{ list-style-type: none; padding: 0; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .news-list li {{ margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #edf2f7; font-size: 0.95em; }}
        .news-list li:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        .news-list a {{ color: #3182ce; text-decoration: none; font-weight: 500; }}
        .news-list a:hover {{ text-decoration: underline; }}
        .source {{ font-weight: bold; color: #4a5568; font-size: 0.85em; text-transform: uppercase; margin-right: 5px; }}
        
        .ai-panel {{ background: linear-gradient(to right, #ebf8ff, #ffffff); border: 1px solid #bee3f8; border-radius: 12px; padding: 30px; margin-top: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .ai-panel p {{ margin-top: 0; color: #2d3748; }}
        #ai-btn {{ background-color: #2b6cb0; color: white; border: none; padding: 14px 28px; font-size: 1.05em; border-radius: 8px; cursor: pointer; font-weight: bold; transition: background-color 0.2s; box-shadow: 0 2px 4px rgba(43, 108, 176, 0.3); }}
        #ai-btn:hover {{ background-color: #2c5282; }}
        #ai-btn:disabled {{ background-color: #a0aec0; cursor: not-allowed; box-shadow: none; }}
        
        #ai-result {{ margin-top: 30px; padding-top: 25px; border-top: 2px dashed #cbd5e0; }}
        #ai-result h3 {{ color: #2c5282; }}
        .error {{ color: #c53030; font-weight: bold; padding: 15px; border-left: 4px solid #c53030; background: #fff5f5; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Dashboard Market Intelligence</h1>
    <div class="timestamp">Notizie e Benchmark aggiornati al: {timestamp}</div>
    
    <h2>1. Rendimenti Macro (Titoli di Stato USA)</h2>
    {html_macro}
    
    <h2>2. Radar Portafoglio (Titoli Monitorati)</h2>
    {html_portfolio}
    
    <h2>3. Rassegna Stampa Istituzionale (Ultime ore)</h2>
    {html_news}

    <div class="ai-panel">
        <h2 style="margin-top: 0; border: none; padding: 0; color: #1a365d;">Genera Analisi Strategica con Gemini</h2>
        <p>L'intelligenza artificiale leggerà le ultime notizie di mercato e scriverà un report sugli impatti previsti per i tuoi settori target (Utility, Telecom, Consumer, Pharma).</p>
        <button id="ai-btn" onclick="generateAnalysis()">Elabora Report Strategico</button>
        <button onclick="localStorage.removeItem('gemini_api_key'); alert('Chiave Gemini rimossa con successo.');" style="background:none;border:none;color:#718096;text-decoration:underline;cursor:pointer;margin-left:20px;font-size:0.9em;">Reset API Key</button>
        
        <div id="ai-result"></div>
    </div>
    
    <pre id="raw-data" style="display:none;">{raw_text}</pre>
    
    <script>
        async function generateAnalysis() {{
            let apiKey = localStorage.getItem('gemini_api_key');
            if (!apiKey) {{ 
                apiKey = prompt("Inserisci la tua API Key di Gemini:"); 
                if (!apiKey) return; 
                localStorage.setItem('gemini_api_key', apiKey); 
            }}
            
            const btn = document.getElementById('ai-btn');
            const resDiv = document.getElementById('ai-result');
            
            btn.disabled = true; 
            btn.innerText = "Stesura del report in corso..."; 
            resDiv.innerHTML = "<p><em>Lettura dei feed RSS e incrocio dei dati con il portafoglio. Attendere...</em></p>";
            
            const systemPrompt = `Sei un Portfolio Manager obbligazionario esperto e strategico.
Analizza il seguente set di dati aggiornati a oggi:
\\n${{document.getElementById('raw-data').innerText}}\\n
Scrivi un report strategico strutturato in 3 sezioni:
1. Sintesi del sentiment macroeconomico odierno (basato sui tassi e le news).
2. Impatto settoriale: come le notizie e i tassi influenzano in generale i settori che ho in portafoglio (Utility, Telecom, Consumer, Pharma).
3. Conclusione operativa.

FORMATTAZIONE OBBLIGATORIA: Usa ESCLUSIVAMENTE codice HTML pulito (tag <h3>, <ul>, <li>, <b>, <p>). 
Non inserire assolutamente il markdown \`\`\`html all'inizio o alla fine, fornisci solo i tag.`;

            try {{
                const url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=" + apiKey.trim();
                const res = await fetch(url, {{
                    method: 'POST', 
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        contents: [{{parts: [{{text: systemPrompt}}]}}]
                    }})
                }});
                
                if (!res.ok) throw new Error("Errore Google API (Stato " + res.status + "). Controlla la chiave o i permessi.");
                
                const data = await res.json();
                let finalHtml = data.candidates[0].content.parts[0].text;
                finalHtml = finalHtml.replace(/```html/gi, '').replace(/```/g, '').trim();
                resDiv.innerHTML = finalHtml;
                
            }} catch (e) {{ 
                resDiv.innerHTML = `<p class="error">${{e.message}}</p>`; 
            }} finally {{ 
                btn.disabled = false; 
                btn.innerText = "Rigenera Report Strategico"; 
            }}
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f: 
        f.write(html_template)
    print("[*] Dashboard Market Intelligence salvata in index.html!")

if __name__ == "__main__":
    macro, port, news = fetch_market_data()
    generate_html_page(macro, port, news)
