import os
import datetime
from flask import Flask, render_template, request, jsonify
from google import genai
from tavily import TavilyClient

app = Flask(__name__)

# 讀取雙引擎金鑰
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# 初始化 AI 與搜尋引擎客戶端
client = genai.Client(api_key=GOOGLE_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

def handle_api_error(e):
    """統一解析 API 錯誤，區分免費額度用完與一般連線失敗"""
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
    
    # 動態獲取系統當下真實時間與年份，打破 AI 時間幻覺
    now = datetime.datetime.now()
    current_date = now.strftime("%Y年%m月%d日")
    current_year = now.year
    previous_year = current_year - 1
    
    if topic_name == "即時法規與新制快報":
        # 讓搜尋關鍵字自動帶入「去年」與「今年」
        search_query = f"台灣 BERS 建築能效評估 綠建築標章 {previous_year} {current_year} 最新法規 新制"
        search_context = search_with_tavily(search_query, max_results=10)

        prompt = f"""
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        ⚠️ 【系統時間校準】：請注意，今天是真實世界的 {current_date}。
        
        請根據下方【最新搜尋資料】，專門整理【即時法規與新制快報】。
        
        【彈性與高智商整理要求】：
        1. 精準收錄：請優先採用 {previous_year} 與 {current_year} 年的最新資訊。
        2. 嚴禁死板過濾：只要判斷該資料對目前台灣 ESG 與 BERS 法規推動有實質參考價值，請直接納入整理。絕對不可因為「日期看起來像未來」、「時間戳記疑似異常」或「略早於 12 個月」就將有效新聞盲目刪除。
        3. 請統整產出最多 10 則資訊（以條列式呈現）。若資訊不足 10 則，有幾則就顯示幾則，嚴禁無中生有。
        4. 每一則資訊請給予清晰的標題，並簡明扼要說明重點。
        5. 【最重要】：請務必在每一則整理資訊的最後面，利用 Markdown 語法附上對應的資料來源超連結，格式為：`[👉 點此查看資料來源](真實網址)`。
        
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
