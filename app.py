import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from duckduckgo_search import DDGS

app = Flask(__name__)

# 設定金鑰
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# 根據 Google 最新官方錯誤提示，直接指定使用支援新用戶的最新模型
model = genai.GenerativeModel('models/gemini-3.6-flash')

def search_latest_news(query, max_results=3):
    """免費的即時搜尋工具，用來抓取最新法規新聞"""
    try:
        results = DDGS().text(query, region='tw-tz', safesearch='off', max_results=max_results)
        context = "\n".join([f"【標題】: {r['title']}\n【內容摘要】: {r['body']}" for r in results])
        return context
    except Exception as e:
        return "目前無法取得最新網路資訊。"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auto_update', methods=['GET'])
def auto_update():
    search_context = search_latest_news("台灣 BERS 建築能效評估 綠建築標章 最新規定 法規 2026")
    prompt = f"""
    你是一位台灣 ESG 建築能效法規解析專家。請根據以下「最新的網路搜尋結果」，整理目前「BERS 建築能效評估」與「綠建築標章」的最新動態。
    請包含以下三個段落（請用 Markdown 格式與繁體中文排版）：
    ### 📢 即時法規與新制快報
    ### ⚖️ 新舊法規差異分析
    ### 🏢 產業影響評估
    【最新搜尋結果參考資料】：\n{search_context}
    """
    try:
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/query', methods=['POST'])
def query():
    user_input = request.json.get("message", "")
    search_context = search_latest_news(f"台灣 建築能效 綠建築 {user_input}")
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答用戶的問題：「{user_input}」
    若涉及法規變動，請務必分析新舊差異與影響。
    【最新搜尋結果參考資料】：\n{search_context}
    """
    try:
        response = model.generate_content(prompt)
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
