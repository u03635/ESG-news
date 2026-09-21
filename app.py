import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS

app = Flask(__name__)

# 設定 Gemini API Key
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# 使用您專案成功運行的模型
model = genai.GenerativeModel('models/gemini-3.6-flash')

def search_latest_news_with_sources(query, max_results=4):
    """即時搜尋，並自動彙整可點選的來源超連結"""
    try:
        results = list(DDGS().text(query, region='tw-tz', safesearch='off', max_results=max_results))
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
    
    # 根據選取的專題進行精準搜尋
    search_query = f"台灣 BERS 建築能效評估 綠建築標章 {topic_name} 2026"
    search_context, sources_md = search_latest_news_with_sources(search_query)

    prompt = f"""
    你是一位台灣 ESG 建築能效與綠建築法規專家。
    請根據下列「最新即時搜尋資料」，專門針對主題【{topic_name}】進行深入解析。
    
    分析要求：
    1. 聚焦於台灣目前實施的 BERS 建築能效評估制度與綠建築標章手冊最新規定。
    2. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    3. 語氣專業、客觀，直接切中產業痛點。
    
    【最新搜尋參考資料】：
    {search_context}
    """
    try:
        response = model.generate_content(prompt)
        # 自動將後端真實爬取到的「超連結」接在 AI 回應最後面
        full_reply = response.text + sources_md
        return jsonify({"response": full_reply})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/query', methods=['POST'])
def query():
    """處理使用者下方自行輸入的問題"""
    user_input = request.json.get("message", "")
    
    search_context, sources_md = search_latest_news_with_sources(f"台灣 建築能效 綠建築 {user_input}")
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答使用者的問題：「{user_input}」
    若涉及法規變更，請分析新舊規範差異與相關影響。
    
    【最新搜尋參考資料】：
    {search_context}
    """
    try:
        response = model.generate_content(prompt)
        full_reply = response.text + sources_md
        return jsonify({"response": full_reply})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
