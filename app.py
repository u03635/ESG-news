import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify
from google import genai

app = Flask(__name__)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

def search_news_rss(query, max_results=15):
    """
    使用 Python 內建庫直連 Google News RSS。
    免 API Key、免綁卡、提供真實超連結與發布時間，大幅降低被擋機率。
    """
    try:
        # 將中文搜尋詞轉換為 URL 編碼
        encoded_query = urllib.parse.quote(query)
        # 組合 Google News RSS 專屬網址 (鎖定台灣與繁體中文)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
        # 加入 User-Agent 偽裝成一般瀏覽器，避免被伺服器拒絕
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        # 解析 XML 資料
        root = ET.fromstring(xml_data)
        
        context = ""
        count = 0
        for item in root.findall('./channel/item'):
            if count >= max_results:
                break
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # 將標題、日期、真實網址打包給 AI
            context += f"【標題】: {title}\n【發布時間】: {pub_date}\n【網址】: {link}\n\n"
            count += 1
            
        return context if context else "無即時連網資料。"
    except Exception as e:
        return f"新聞檢索失敗，錯誤訊息：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/topic', methods=['POST'])
def topic():
    topic_name = request.json.get("topic", "")
    
    if topic_name == "即時法規與新制快報":
        search_query = "台灣 BERS 建築能效評估 綠建築標章 新制"
        search_context = search_news_rss(search_query, max_results=20)

        prompt = f"""
        你是一位台灣 ESG 建築能效與綠建築法規專家。
        請專門整理【即時法規與新制快報】。
        
        【嚴格執行要求】：
        1. 僅篩選下方資料中發布時間為「近 12 個月內」的動態。
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
            return jsonify({"response": f"系統發生錯誤：{str(e)}"})

@app.route('/analyze_diff', methods=['POST'])
def analyze_diff():
    regulation_name = request.json.get("regulation", "")
    search_query = f"台灣 {regulation_name} 新舊法規 差異 影響"
    search_context = search_news_rss(search_query, max_results=10)
    
    prompt = f"""
    你是一位台灣 ESG 法規專家。
    使用者要求針對法規：「{regulation_name}」進行新舊法規差異分析。
    
    【分析要求】：
    1. 條理分明、層次清晰，使用清晰的 Markdown 標題與條列式排版。
    2. 請優先參考下方最新搜尋資料。若資料不足，請直接運用你的專業知識輔助說明。
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
        return jsonify({"response": f"系統發生錯誤：{str(e)}"})

@app.route('/query', methods=['POST'])
def query():
    user_input = request.json.get("message", "")
    search_context = search_news_rss(f"台灣 建築能效 綠建築 {user_input}", max_results=5)
    
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
        return jsonify({"response": f"系統發生錯誤：{str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
