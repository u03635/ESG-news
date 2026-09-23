import os
from flask import Flask, render_template, request, jsonify
from google import genai
from duckduckgo_search import DDGS

app = Flask(__name__)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

def handle_api_error(e):
    err_str = str(e).lower()
    if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
        return jsonify({"error": "QUOTA_EXCEEDED"})
    else:
        return jsonify({"error": "CONNECTION_FAILED"})

def search_latest_news_with_sources(query, max_results=10, timelimit=None):
    try:
        results = list(DDGS().text(query, region='tw-tz', safesearch='off', timelimit=timelimit, max_results=max_results))
        context = ""
        
        for r in results:
            title = r.get('title', '').strip()
            href = r.get('href', '').strip()
            body = r.get('body', '').strip()
            if title and href:
                context += f"【標題】: {title}\n【網址】: {href}\n【內容摘要】: {body}\n\n"
                
        return context if context else "未搜尋到相關資料。"
    except Exception as e:
        # 修改這裡：將真實的系統錯誤訊息抓出來給 AI 看，方便我們除錯
        return f"目前無法取得最新網路資訊，搜尋系統回報錯誤：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic', methods=['POST'])
def topic():
    topic_name = request.json.get("topic", "")
    
    if topic_name == "即時法規與新制快報":
        # 將 max_results 微調為 15，降低對 DuckDuckGo 的負擔，減少被擋機率
        search_query = "台灣 BERS 建築能效評估 綠建築標章 新制 法規"
        search_context = search_latest_news_with_sources(search_query, max_results=15, timelimit='y')

        prompt = f"""
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        請根據下列「最新即時搜尋資料」，專門整理【即時法規與新制快報】。
        
        【嚴格執行要求】：
        1. 僅篩選「近 12 個月內」的動態與資料。
        2. 請統整產出 10 則資訊（以條列式呈現）。
        3. 若半年內或近 12 個月內符合條件的資訊不足 10 則，【有幾則就顯示幾則】，絕對不要無中生有湊數。
        4. 每則資訊請給予清晰的標題，並簡明扼要說明重點。
        5. 【最重要】：請務必在「每一則」整理資訊的最後面，附上對應的資料來源超連結，格式為：[👉 點此查看資料來源](此處填入真實網址)
        
        【最新搜尋參考資料】：
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
    search_query = f"台灣 {regulation_name} 新舊法規差異 新制 影響"
    search_context = search_latest_news_with_sources(search_query, max_results=8)
    
    prompt = f"""
    你是一位台灣 ESG 法規專家。
    使用者要求針對法規：「{regulation_name}」進行新舊法規差異分析。
    請根據下列「最新即時搜尋資料」，整理出新舊版本的不同之處與帶來的影響。
    
    【分析要求】：
    1. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    2. 若搜尋資料不足，請運用你的專業知識輔助說明可能的新舊差異與預期影響。
    3. 【重要】：請務必在提及特定法規或新聞段落的下方，附上對應的參考來源，格式為：[👉 參考來源](此處填入真實網址)
    
    【最新搜尋參考資料】：
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
    search_context = search_latest_news_with_sources(f"台灣 建築能效 綠建築 {user_input}", max_results=5)
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答使用者的問題：「{user_input}」
    
    【要求】：請在回答中適當引用資料，並在段落後方使用 Markdown 格式附上超連結：[參考來源](此處填入真實網址)
    
    【最新搜尋參考資料】：\n{search_context}
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
