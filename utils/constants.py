"""
アプリケーション全体で使用される定数
"""

# デフォルト設定
DEFAULT_CHAT_MODEL = "gemini-1.5-flash"
DEFAULT_VOICE = "kore"
DEFAULT_TEMPERATURE = 0.7

# セッション設定
SESSION_TIMEOUT = 3600  # 1時間（秒）
MAX_CHAT_HISTORY = 50  # チャット履歴の最大保持数
MAX_SCENARIO_HISTORY = 30  # シナリオ履歴の最大保持数
MAX_WATCH_HISTORY = 20  # 観戦履歴の最大保持数

# 利用可能なモデル
AVAILABLE_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

# 利用可能な音声（女性）
FEMALE_VOICES = [
    "kore",  # 会社的
    "aoede",  # 軽快
    "callirrhoe",  # おおらか
    "leda",  # 若々しい
    "algieba",  # スムーズ
    "autonoe",  # 明るい
    "despina",  # スムーズ
    "erinome",  # クリア
    "laomedeia",  # アップビート
    "pulcherrima",  # 前向き
    "vindemiatrix",  # 優しい
]

# 利用可能な音声（男性）
MALE_VOICES = [
    "enceladus",  # 息づかい
    "charon",  # 情報提供的
    "fenrir",  # 興奮しやすい
    "orus",  # 会社的
    "iapetus",  # クリア
    "algenib",  # 砂利声
    "rasalgethi",  # 情報豊富
    "achernar",  # ソフト
    "alnilam",  # 確実
    "gacrux",  # 成熟
    "achird",  # フレンドリー
    "zubenelgenubi",  # カジュアル
    "sadachbia",  # 活発
    "sadaltager",  # 知識豊富
    "sulafat",  # 温かい
]

# 利用可能な音声（中性）
NEUTRAL_VOICES = ["puck", "zephyr", "umbriel", "schedar"]  # アップビート  # 明るい  # 気楽  # 均等

# すべての音声
AVAILABLE_VOICES = FEMALE_VOICES + MALE_VOICES + NEUTRAL_VOICES

# 感情と推奨音声のマッピング
EMOTION_VOICE_MAPPING = {
    "happy": "autonoe",  # 明るい女性音声
    "excited": "fenrir",  # 興奮しやすい男性音声
    "sad": "vindemiatrix",  # 優しい女性音声
    "tired": "enceladus",  # 息づかいのある男性音声
    "angry": "algenib",  # 砂利声の男性音声
    "worried": "achernar",  # ソフトな男性音声
    "calm": "schedar",  # 均等な中性音声
    "confident": "alnilam",  # 確実な男性音声
    "professional": "orus",  # 会社的な男性音声
    "friendly": "achird",  # フレンドリーな男性音声
}

# メッセージの最大長
MAX_MESSAGE_LENGTH = 4000
MAX_FEEDBACK_LENGTH = 2000

# レート制限
RATE_LIMIT_CHAT = 30  # 1分あたりのチャットメッセージ数
RATE_LIMIT_SCENARIO = 10  # 1分あたりのシナリオ開始数
RATE_LIMIT_WATCH = 5  # 1分あたりの観戦開始数
RATE_LIMIT_TTS = 20  # 1分あたりのTTS要求数

# ファイルサイズ制限
MAX_AUDIO_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# TTSモデル設定
TTS_MODEL = "models/gemini-2.5-flash-preview-tts"
TTS_SAMPLE_RATE = 24000
TTS_CHANNELS = 1
TTS_SAMPLE_WIDTH = 2


# セッションキーの定義
class SessionKeys:
    """セッション内で使用するキーの定義"""

    CHAT_HISTORY = "chat_history"
    SCENARIO_HISTORY = "scenario_history"
    WATCH_HISTORY = "watch_history"
    LEARNING_HISTORY = "learning_history"
    CURRENT_MODEL = "current_model"
    CURRENT_VOICE = "current_voice"


# 履歴フォーマットの定義
class HistoryFormat:
    """履歴取得時のフォーマット"""

    FULL = "full"
    MESSAGES_ONLY = "messages_only"
    LATEST = "latest"
