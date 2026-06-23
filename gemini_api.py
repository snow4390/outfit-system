import requests
import time
from config import API_KEY, GEMINI_API_URL, REQUEST_TIMEOUT, GEMINI_MAX_RETRIES


def call_gemini_api(payload, max_retries=GEMINI_MAX_RETRIES):
    if not API_KEY:
        return None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={API_KEY}",
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue

            print(f"Gemini API 呼叫失敗: {response.status_code}, {response.text}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"Gemini API 例外: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None

    return None


def extract_text_from_gemini_response(resp):
    try:
        if not resp:
            return ""

        candidates = resp.get("candidates", [])
        if not candidates:
            return ""

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        return "\n".join(texts).strip()
    except Exception as e:
        print(f"Gemini 回應解析失敗: {e}")
        return ""


def build_ranked_outfit_summary(top_outfit):
    top_item = top_outfit["items"]["top"]
    bottom_item = top_outfit["items"]["bottom"]

    summary_text = f"""
你現在要根據系統分析結果，生成自然、專業的繁體中文穿搭建議。

【上衣資訊】
- 品類：{top_item.get("category", "未知")}
- 主要風格：{top_item.get("style", "未知")}
- Top3 風格：{top_item.get("style_top3", [])}
- 主色 HSV：{top_item.get("color", {}).get("main_hsv", [])}
- 是否中性色：{top_item.get("color", {}).get("is_neutral", False)}
- 版型：{top_item.get("fit", {}).get("label", "unknown")}

【下裝資訊】
- 品類：{bottom_item.get("category", "未知")}
- 主要風格：{bottom_item.get("style", "未知")}
- Top3 風格：{bottom_item.get("style_top3", [])}
- 主色 HSV：{bottom_item.get("color", {}).get("main_hsv", [])}
- 是否中性色：{bottom_item.get("color", {}).get("is_neutral", False)}
- 版型：{bottom_item.get("fit", {}).get("label", "unknown")}

【規則評分】
- 總分：{top_outfit.get("score", 0)}
- 分項：{top_outfit.get("breakdown", {})}
- 優點：{top_outfit.get("reasons", [])}
- 注意事項：{top_outfit.get("warnings", [])}
"""
    return summary_text.strip()


def generate_suggestion_gemini_from_ranked_outfits(ranked_outfits, user_text=None):
    if not ranked_outfits:
        return "目前無法生成穿搭建議，請重新上傳圖片再試一次。"

    top_outfit = ranked_outfits[0]
    summary_text = build_ranked_outfit_summary(top_outfit)

    if user_text:
        summary_text += f"\n\n【使用者需求】\n{user_text}"

    system_prompt = """
你是一位專業時尚造型師。
請根據系統提供的分析結果，用自然、親切、專業的繁體中文生成穿搭建議。

要求：
1. 先描述整體風格。
2. 說明為什麼這樣搭配好看。
3. 提供鞋款、包款、配件建議。
4. 若有 warnings，要自然地提醒避雷點。
5. 最後補充適合的場合。
6. 不要輸出 JSON，不要輸出程式碼。
7. 回答要讓大學生看得懂，也要自然。
""".strip()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": summary_text}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_prompt}
            ]
        }
    }

    resp = call_gemini_api(payload)
    text = extract_text_from_gemini_response(resp)

    if text:
        return text

    # fallback
    top_item = top_outfit["items"]["top"]
    bottom_item = top_outfit["items"]["bottom"]
    return (
        f"建議以上衣「{top_item.get('category', '未知')}」搭配下裝「{bottom_item.get('category', '未知')}」作為主體，"
        f"整體風格偏向 {top_item.get('style', '未知')} 與 {bottom_item.get('style', '未知')} 的融合。"
        f"可搭配簡約鞋款與中性色配件，適合日常外出、聚會或輕鬆約會。"
    )


def generate_suggestion_text(text_query):
    if not text_query:
        return "請輸入你想要的穿搭需求，例如場合、風格或顏色偏好。"

    system_prompt = """
你是一位專業時尚造型師，請根據使用者的文字需求提供自然、專業、實用的繁體中文穿搭建議。
不要輸出 JSON 或程式碼。
""".strip()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"使用者需求：{text_query}"}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_prompt}
            ]
        }
    }

    resp = call_gemini_api(payload)
    text = extract_text_from_gemini_response(resp)

    if text:
        return text

    return f"依據你的需求「{text_query}」，建議從簡約、好搭配的單品開始，並搭配中性色鞋包提升整體完成度。"