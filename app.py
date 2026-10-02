import os
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types  # 匯入新型態設定模組

app = Flask(__name__)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

def handle_api_error(e):
    """直接將真實錯誤訊息偽裝成正常對話傳給前端，強迫顯示在畫面上！"""
    error_msg = f"⚠️️ **系統底層除錯報告**\n\n伺服器傳回的真實錯誤原因如下：\n```text\n{str(e)}\n```\n\n👉 *請將這段代碼提供給顧問，我們馬上就能對症下藥！*"
    # 注意：我們故意不用 "error" 標籤回傳，而是用 "response"，這樣前端就會乖乖把它印出來
    return jsonify({"response": error_msg})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic', methods=['POST'])
def topic():
    topic_name = request.json.get("topic", "")
    
    if topic_name == "即時法規與新制快報":
        prompt = """
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        請使用 Google 搜尋檢索台灣「BERS 建築能效評估」與「綠建築標章」的最新動態。
        
        【嚴格執行要求】：
        1. 僅篩選「近 12 個月內」的動態與資料。
        2. 請統整產出最多 10 則資訊（以條列式呈現）。若資訊不足 10 則，有幾則就顯示幾則，絕對不要無中生有湊數。
        3. 每一則資訊請給予清晰的標題，並簡明扼要說明重點。
        4. 【最重要】：請務必在每一則整理資訊的最後面，利用 Markdown 語法附上對應的資料來源超連結，格式為：`[👉 點此查看資料來源](真實網址)`。
        """
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]  # 🚀 關鍵升級：直接賦予模型 Google 官方搜尋能力
                )
            )
            return jsonify({"response": response.text})
        except Exception as e:
            return handle_api_error(e)

@app.route('/analyze_diff', methods=['POST'])
def analyze_diff():
    regulation_name = request.json.get("regulation", "")
    
    prompt = f"""
    你是一位台灣 ESG 法規專家。
    使用者要求針對法規：「{regulation_name}」進行新舊法規差異分析。
    請使用 Google 搜尋檢索相關資料，整理出新舊版本的不同之處與帶來的影響。
    
    【分析要求】：
    1. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    2. 【重要】：請務必在提及特定法規或新聞段落的下方，附上對應的參考來源，格式為：`[👉 參考來源](真實網址)`。
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return handle_api_error(e)

@app.route('/query', methods=['POST'])
def query():
    user_input = request.json.get("message", "")
    
    prompt = f"""
    你是一位台灣 ESG 建築能效專家。請回答使用者的問題：「{user_input}」
    
    【要求】：請在回答中適當使用 Google 搜尋確認最新資料，並在段落後方使用 Markdown 格式附上超連結：`[參考來源](真實網址)`。
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return handle_api_error(e)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
