import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS

app = Flask(__name__)

# 設定 Gemini API Key
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('models/gemini-3.6-flash')

def handle_api_error(e):
    """統一解析 API 錯誤，區分免費額度用完與一般連線失敗"""
    err_str = str(e).lower()
    # 若錯誤訊息包含 429、quota 或 exhausted，代表免費額度用完或請求過於頻繁
    if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
        return jsonify({"error": "QUOTA_EXCEEDED"})
    else:
        return jsonify({"error": "CONNECTION_FAILED"})
        
def search_latest_news_with_sources(query, max_results=10, timelimit=None):
    """即時搜尋，支援時間範圍過濾，並自動彙整可點選的來源超連結"""
    try:
        # 參數 timelimit='y' 代表抓取過去一年內的資料（幫助模型從中篩選半年內）
        results = list(DDGS().text(query, region='tw-tz', safesearch='off', timelimit=timelimit, max_results=max_results))
        context = ""
        sources_markdown = "\n\n---\n### 🔗 參考資料與最新來源連結\n"
        has_sources = False
        
        for r in results:
            title = r.get('title', '').strip()
            href = r.get('href', '').strip()
            body = r.get('body', '').strip()
            if title and href:
                context += f"【標題】: {title}\n【內容摘要】: {body}\n\n"
                sources_markdown += f"- [{title}]({href})\n"
                has_sources = True
                
        if not has_sources:
            sources_markdown = ""
            
        return context, sources_markdown
    except Exception as e:
        return "目前無法取得最新網路資訊。", ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic', methods=['POST'])
def topic():
    """處理左側 3 個專題按鈕點擊事件"""
    topic_name = request.json.get("topic", "")
    
    if topic_name == "即時法規與新制快報":
        # 將抓取筆數提高至 20 筆，確保 12 個月內有足夠的新聞素材供 AI 篩選
        search_query = "台灣 BERS 建築能效評估 綠建築標章 新制 法規"
        search_context, sources_md = search_latest_news_with_sources(search_query, max_results=20, timelimit='y')

        prompt = f"""
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        請根據下列「最新即時搜尋資料」，專門整理【即時法規與新制快報】。
        
        【嚴格執行要求】：
        1. 僅篩選「近 12 個月內」的動態與資料。
        2. 請統整產出 10 則資訊（以條列式呈現）。
        3. 若半年內或近 12 個月內符合條件的資訊不足 10 則，【有幾則就顯示幾則】，絕對不要無中生有湊數。
        4. 每則資訊請給予清晰的標題，並簡明扼要說明重點。
        
        【最新搜尋參考資料】：
        {search_context}
        """
        try:
            response = model.generate_content(prompt)
            full_reply = response.text + sources_md
            return jsonify({"response": full_reply})
        except Exception as e:
            return handle_api_error(e)

@app.route('/analyze_diff', methods=['POST'])
def analyze_diff():
    """處理【新舊法規差異分析】(當使用者輸入法規名稱後觸發)"""
    regulation_name = request.json.get("regulation", "")
    
    search_query = f"台灣 {regulation_name} 新舊法規差異 新制 影響"
    search_context, sources_md = search_latest_news_with_sources(search_query, max_results=8)
    
    prompt = f"""
    你是一位台灣 ESG 法規專家。
    使用者要求針對法規：「{regulation_name}」進行新舊法規差異分析。
    請根據下列「最新即時搜尋資料」，整理出新舊版本的不同之處與帶來的影響。
    
    【分析要求】：
    1. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    2. 若搜尋資料不足，請運用你的專業知識輔助說明可能的新舊差異與預期影響。
    
    【最新搜尋參考資料】：
    {search_context}
    """
    try:
        response = model.generate_content(prompt)
        full_reply = response.text + sources_md
        return jsonify({"response": full_reply})
    except Exception as e:
        return handle_api_error(e)

@app.route('/query', methods=['POST'])
def query():
    """處理使用者一般問答"""
    user_input = request.json.get("message", "")
    search_context, sources_md = search_latest_news_with_sources(f"台灣 建築能效 綠建築 {user_input}", max_results=5)
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答使用者的問題：「{user_input}」
    【最新搜尋參考資料】：\n{search_context}
    """
    try:
        response = model.generate_content(prompt)
        full_reply = response.text + sources_md
        return jsonify({"response": full_reply})
    except Exception as e:
        return handle_api_error(e)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
