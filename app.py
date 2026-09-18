import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS

app = Flask(__name__)

# 設定免費的 Google Gemini API 金鑰 (部署時在雲端環境變數設定)
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
# 使用快速且免費額度高的 Gemini 1.5 Flash 模型
model = genai.GenerativeModel('gemini-1.5-flash')

def search_latest_news(query, max_results=3):
    """免費的即時搜尋工具，用來抓取最新法規新聞"""
    try:
        results = DDGS().text(query, region='tw-tz', safesearch='off', max_results=max_results)
        # 將搜尋結果組合成文字，提供給 AI 參考
        context = "\n".join([f"【標題】: {r['title']}\n【內容摘要】: {r['body']}" for r in results])
        return context
    except Exception as e:
        return "目前無法取得最新網路資訊。"

@app.route('/')
def index():
    # 載入前端網頁
    return render_template('index.html')

@app.route('/auto_update', methods=['GET'])
def auto_update():
    """網頁一打開就會自動呼叫這個路由，產生最新法規報告"""
    # 1. 自動搜尋最新的 BERS 與綠建築標章關鍵字
    search_context = search_latest_news("台灣 BERS 建築能效評估 綠建築標章 最新規定 法規 2026")
    
    # 2. 指導 AI 如何進行新舊法規比對
    prompt = f"""
    你是一位台灣 ESG 建築能效法規解析專家。
    請根據以下「最新的網路搜尋結果」，整理目前「BERS 建築能效評估」與「綠建築標章」的最新動態。
    
    請務必包含以下三個段落（請用 Markdown 格式與繁體中文排版）：
    ### 📢 即時法規與新制快報
    (列出最新規定與補充說明)
    ### ⚖️ 新舊法規差異分析
    (比較新制與舊版的不同之處)
    ### 🏢 產業影響評估
    (分析新規定對建築業、企業主帶來的實質影響)
    
    【最新搜尋結果參考資料】：
    {search_context}
    """
    try:
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/query', methods=['POST'])
def query():
    """處理用戶手動輸入的查詢"""
    user_input = request.json.get("message", "")
    
    # 針對用戶問題進行即時搜尋
    search_context = search_latest_news(f"台灣 建築能效 綠建築 {user_input}")
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答用戶的問題：「{user_input}」
    若涉及法規變動，請務必分析新舊差異與影響。
    
    【最新搜尋結果參考資料】：
    {search_context}
    """
    try:
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
