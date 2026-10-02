import os
from flask import Flask, render_template, request, jsonify
from google import genai
from tavily import TavilyClient

app = Flask(__name__)

# 讀取雙引擎金鑰
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

client = genai.Client(api_key=GOOGLE_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

def handle_api_error(e):
    err_str = str(e).lower()
    if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
        return jsonify({"error": "QUOTA_EXCEEDED"})
    else:
        return jsonify({"error": "CONNECTION_FAILED"})

def search_with_tavily(query, max_results=8):
    """使用 Tavily API 進行專為 AI 打造的深度搜尋"""
    if not tavily_client:
        return "系統異常：找不到 TAVILY_API_KEY，請至 Render 後台設定環境變數。"

    try:
        # search_depth="advanced" 會獲取更高品質的結果與摘要
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
        )
        
        context = ""
        for result in response.get('results', []):
            title = result.get('title', '').strip()
            url = result.get('url', '').strip()
            content = result.get('content', '').strip()
            if title and url:
                context += f"【標題】: {title}\n【網址】: {url}\n【內容摘要】: {content}\n\n"
                
        return context if context else "目前無法取得最新網路資訊。"
    except Exception as e:
        return f"搜尋系統回報錯誤：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic', methods=['POST'])
def topic():
    topic_name = request.json.get("topic", "")
    
    if topic_name == "即時法規與新制快報":
        # 放寬年份限制，讓 Tavily 自己用自然語言理解能力去找最新資料
        search_query = "台灣 BERS 建築能效評估 綠建築標章 2026 最新法規 新制"
        search_context = search_with_tavily(search_query, max_results=10)

        prompt = f"""
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        請專門整理【即時法規與新制快報】。
        
        【嚴格執行要求】：
        1. 僅篩選下方資料中「近 12 個月內」的動態。
        2. 請統整產出最多 10 則資訊（以條列式呈現）。若資訊不足 10 則，有幾則就顯示幾則，絕對不要無中生有。
        3. 每一則資訊請給予清晰的標題，並簡明扼要說明重點。
        4. 【最重要】：請務必在每一則整理資訊的最後面，利用 Markdown 語法附上對應的資料來源超連結，格式為：`[👉 點此查看資料來源](真實網址)`。
        
        【最新搜尋資料】：
        {search_context}
        """
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            return jsonify({"response": response.text})
        except Exception as e:
            return handle_api_error(e)

@app.route('/analyze_diff', methods=['POST'])
def analyze_diff():
    regulation_name = request.json.get("regulation", "")
    search_query = f"台灣 {regulation_name} 新舊法規 差異 影響 比較"
    search_context = search_with_tavily(search_query, max_results=6)
    
    prompt = f"""
    你是一位台灣 ESG 法規專家。
    使用者要求針對法規：「{regulation_name}」進行新舊法規差異分析。
    
    【分析要求】：
    1. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    2. 請優先參考下方最新搜尋資料。若資料不足，請運用你的專業知識輔助說明。
    3. 【重要】：若引用了搜尋資料，請在段落下方附上對應的參考來源，格式為：`[👉 參考來源](真實網址)`。
    
    【最新搜尋資料】：
    {search_context}
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return handle_api_error(e)

@app.route('/query', methods=['POST'])
def query():
    user_input = request.json.get("message", "")
    search_context = search_with_tavily(f"台灣 建築能效 綠建築 {user_input}", max_results=5)
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答使用者的問題：「{user_input}」
    
    【要求】：請在回答中適當引用下方資料（或內建知識），並在段落後方使用 Markdown 格式附上超連結：`[參考來源](網址)`。
    
    【最新搜尋資料】：\n{search_context}
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return handle_api_error(e)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
