"""
Image generation routes for the workplace-roleplay application.
Handles AI character image generation.
"""

from flask import Blueprint, jsonify, request

from config import get_cached_config
from errors import ExternalAPIError, secure_error_handler
from scenarios import load_scenarios

# セキュリティ関連のインポート
try:
    from utils.security import SecurityUtils
except ImportError:

    class SecurityUtils:
        @staticmethod
        def get_safe_error_message(e):
            return str(e)


# Blueprint作成
image_bp = Blueprint("image", __name__)

# 設定の取得
config = get_cached_config()

# シナリオをロード
try:
    scenarios = load_scenarios()
except Exception as e:
    print(f"❌ シナリオロードエラー (image_routes): {e}")
    scenarios = {}

# 画像キャッシュ
image_cache = {}
MAX_CACHE_SIZE = 50


# シナリオごとの固定的な外見特徴
SCENARIO_APPEARANCES = {
    # 男性上司系
    "scenario1": "short black hair with slight gray at temples, clean-shaven, rectangular glasses, serious demeanor",
    "scenario3": "graying hair neatly styled, clean-shaven, thin-rimmed glasses, authoritative look",
    "scenario5": "dark hair with professional cut, clean-shaven, no glasses, confident bearing",
    "scenario9": "salt-and-pepper hair, clean-shaven, round glasses, thoughtful expression",
    "scenario11": "silver hair, clean-shaven, no glasses, distinguished appearance",
    "scenario13": "short black hair, clean-shaven, modern glasses, tech-savvy look",
    "scenario16": "well-groomed dark hair, clean-shaven, designer glasses, strategic thinker",
    "scenario22": "athletic build, short hair, clean-shaven, energetic presence",
    "scenario29": "experienced look, graying temples, clean-shaven, warm smile",
    # 女性上司・先輩系
    "scenario7": "shoulder-length black hair, professional style, light makeup, leadership aura",
    "scenario15": "bob-cut hair, elegant makeup, pearl earrings, managerial presence",
    "scenario17": "sophisticated short hair, refined makeup, executive appearance",
    "scenario19": "long hair in low ponytail, gentle makeup, mentoring demeanor",
    "scenario26": "stylish medium-length hair, polished makeup, PR professional look",
    # デフォルト外見
    "default_male": "short black hair, clean-shaven, casual professional look",
    "default_female": "medium-length black hair, natural makeup, approachable appearance",
}


@image_bp.route("/api/generate_character_image", methods=["POST"])
@secure_error_handler
def generate_character_image():
    """AIキャラクターの画像を生成するAPI"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        scenario_id = data.get("scenario_id")
        emotion = data.get("emotion", "neutral")

        if not scenario_id:
            return jsonify({"error": "シナリオIDが必要です"}), 400

        if scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオID"}), 400

        scenario = scenarios[scenario_id]
        character_setting = scenario.get("character_setting", {})
        personality = character_setting.get("personality", "")

        # 年齢・性別・役職の推定
        age_range = "40s"
        gender = "male"
        position = "manager"

        if "女性" in personality or "female" in personality.lower():
            gender = "female"
        elif "男性" in personality or "male" in personality.lower():
            gender = "male"

        if "20代" in personality or "新人" in personality:
            age_range = "20s"
        elif "30代" in personality:
            age_range = "30s"
        elif "40代" in personality:
            age_range = "40s"
        elif "50代" in personality:
            age_range = "50s"

        if "部長" in personality:
            position = "department manager"
        elif "課長" in personality:
            position = "section manager"
        elif "先輩" in personality:
            position = "senior colleague"
        elif "同僚" in personality:
            position = "colleague"
        elif "後輩" in personality or "新人" in personality:
            position = "junior colleague"

        # 感情から表情への変換
        emotion_expressions = {
            "happy": "with a warm, genuine smile and bright eyes",
            "sad": "with a concerned, sympathetic expression",
            "angry": "with a slightly frustrated but controlled expression",
            "excited": "with an enthusiastic, energetic expression",
            "worried": "with a worried, concerned look",
            "tired": "looking slightly fatigued but professional",
            "calm": "with a calm, composed expression",
            "confident": "with a confident, assured expression",
            "professional": "with a professional, neutral expression",
            "friendly": "with a friendly, approachable expression",
            "neutral": "with a neutral, attentive expression",
        }

        expression = emotion_expressions.get(emotion, emotion_expressions["neutral"])
        gender_text = "woman" if gender == "female" else "man"

        # シナリオに基づいて外見を決定
        if scenario_id in SCENARIO_APPEARANCES:
            appearance = SCENARIO_APPEARANCES[scenario_id]
        else:
            default_key = f"default_{gender}"
            appearance = SCENARIO_APPEARANCES.get(default_key, "professional appearance")

        # キャッシュキーの生成
        cache_key = f"{scenario_id}_{emotion}"

        # キャッシュチェック
        if cache_key in image_cache:
            print(f"画像キャッシュヒット: {cache_key}")
            cached_data = image_cache[cache_key]
            cached_data["cache_hit"] = True
            return jsonify(cached_data)

        try:
            import base64

            from google import genai
            from google.genai import types

            # Geminiクライアントの初期化
            client = genai.Client(api_key=config.GOOGLE_API_KEY)

            # プロンプトの構築
            character_seed = f"character_{scenario_id}_{gender}_{age_range}"

            prompt = (
                f"IMPORTANT: Generate the EXACT SAME person in every image. "
                f"Character ID: {character_seed}. "
                f"This is a professional Japanese {gender_text} in their {age_range}, "
                f"with EXACTLY these features: {appearance}. "
                f"They must have the SAME face structure, SAME hairstyle, SAME facial features. "
                f"Only the expression changes to show {expression}. "
                f"Dressed in appropriate business attire for a {position}, "
                f"in a modern Japanese office environment, "
                f"photorealistic portrait style, high quality, professional lighting."
            )

            # 状況に応じた背景の追加
            situation = character_setting.get("situation", "")
            if "会議" in situation:
                prompt += ", meeting room background"
            elif "休憩" in situation or "ランチ" in situation:
                prompt += ", office break room or cafeteria background"
            elif "懇親会" in situation:
                prompt += ", casual office party setting"

            print(f"画像生成開始: {cache_key}")

            # 画像生成リクエスト
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )

            # レスポンスから画像データを取得
            image_data = None
            generated_text = None

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        generated_text = part.text
                    elif hasattr(part, "inline_data") and part.inline_data:
                        image_data = part.inline_data.data

            if not image_data:
                raise ValueError("画像データが生成されませんでした")

            # 画像データの処理
            if isinstance(image_data, str):
                image_base64 = image_data
            else:
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            response_data = {
                "image": image_base64,
                "format": "png",
                "prompt": prompt,
                "emotion": emotion,
                "character_info": {
                    "age": age_range,
                    "gender": gender,
                    "position": position,
                },
            }

            if generated_text:
                response_data["description"] = generated_text

            # キャッシュに保存
            if len(image_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(image_cache))
                del image_cache[oldest_key]
                print(f"キャッシュサイズ制限により削除: {oldest_key}")

            image_cache[cache_key] = response_data.copy()
            print(f"画像をキャッシュに保存: {cache_key}")

            return jsonify(response_data)

        except Exception as e:
            print(f"Image generation error: {str(e)}")
            raise ExternalAPIError(service="Image Generator", message="画像生成に失敗しました")

    except Exception as e:
        print(f"Error in generate_character_image: {str(e)}")
        return (
            jsonify({"error": f"画像生成に失敗しました: {SecurityUtils.get_safe_error_message(e)}"}),
            500,
        )
