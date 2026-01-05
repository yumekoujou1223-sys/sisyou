import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io

# --- 設定：道場の構築 ---
st.set_page_config(
    page_title="昭和の師匠 - 鉄の庵",
    page_icon="🔨",
    layout="centered"
)

# --- 哲学：UIデザイン ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Shippori Mincho', serif;
        background-color: #1a1a1a;
        color: #e0e0e0;
    }
    p, div, input, textarea, button { font-size: 1.0em !important; }
    
    /* 公式マイクボタンの調整 */
    .stAudioInput > div > button {
        background-color: #8c2f2f !important;
        color: white !important;
        border: none;
    }

    .user-msg {
        text-align: right;
        color: #a0a0a0;
        margin: 10px 0;
        padding: 10px;
        border-right: 3px solid #555;
    }
    .bot-msg {
        text-align: left;
        color: #ffffff;
        margin: 20px 0;
        padding: 15px;
        border-left: 5px solid #8c2f2f;
        background-color: #2b2b2b;
        border-radius: 0 10px 10px 0;
        line-height: 1.8;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 秘密の鍵を取り出す（裏口入学） ---
# Streamlitの金庫(Secrets)に鍵があればそれを使う。なければサイドバーを表示（開発用）
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    has_valid_key = True
else:
    with st.sidebar:
        st.markdown("### 🔧 鉄の工具箱")
        api_key = st.text_input("Gemini API Key", type="password")
        has_valid_key = bool(api_key)

# --- サイドバー設定 ---
with st.sidebar:
    if "GEMINI_API_KEY" in st.secrets:
        st.success("認証済み：師匠は準備万端だ。")
    
    st.divider()
    st.markdown("### 🔊 音声設定")
    speed_setting = st.radio(
        "読み上げ速度",
        ("🐢 ゆっくり（高齢者向）", "🐇 普通（サクサク）"),
        index=0
    )

# --- 魂：システムプロンプト ---
SYSTEM_PROMPT = """
あなたは「昭和の頑固な雷親父（師匠）」だ。
ユーザーの音声を文字起こしし、それに対する返答を行え。

# 出力形式（厳守）
1行目：【聞き取った言葉】（ユーザーの音声を文字起こし）
2行目以降：【師匠の返答】（雷親父としての説教）

# キャラクター定義
- 一人称：「俺」
- 口調：べらんめぇ調、激昂。「バカ野郎！」「〜だと？」「〜しやがれ！」
- スタンス：甘えを許さず、図星を突き、最後に道を示す。
"""

# --- 初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 画面構成 ---
st.markdown("<h1 style='text-align: center; color: #8c2f2f;'>雷親父の道場</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; opacity: 0.8;'>下のマイクボタンを押して喋り、送信せよ。</p>", unsafe_allow_html=True)
st.divider()

# --- 履歴表示 ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='bot-msg'>{msg['content']}</div>", unsafe_allow_html=True)
        if "audio" in msg:
            st.audio(msg["audio"], format="audio/mp3")

# --- 入力エリア（新・公式マイク） ---
st.write("### 🗣️ 声で相談する")

# ここが新しい公式マイクパーツ！スマホに強い！
audio_input = st.audio_input("録音ボタン")

# テキスト入力（予備）
with st.expander("筆談（キーボード）で挑む"):
    with st.form(key="text_form", clear_on_submit=True):
        text_input = st.text_area("相談内容", height=70)
        submit_btn = st.form_submit_button("送信")

# --- 処理ロジック ---
input_content = None
is_audio = False

if audio_input:
    # 公式マイクは録音完了後すぐにデータが入る
    input_content = audio_input
    is_audio = True
elif submit_btn and text_input:
    input_content = text_input
    is_audio = False

if input_content:
    if not has_valid_key:
        st.error("おい！鍵（APIキー）がねぇぞ！設定を確認しろ！")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash-exp", system_instruction=SYSTEM_PROMPT)
            
            with st.spinner("師匠が腹に力を入れている……"):
                if is_audio:
                    # 公式マイクのデータを読み込む
                    audio_bytes = input_content.read()
                    response = model.generate_content([
                        "以下の音声を文字起こしして、返答せよ。",
                        {"mime_type": "audio/wav", "data": audio_bytes}
                    ])
                else:
                    response = model.generate_content(input_content)

                full_text = response.text
                parts = full_text.split("\n", 1)
                
                if len(parts) >= 2:
                    user_voice_text = parts[0].replace("【聞き取った言葉】", "").strip()
                    bot_reply_text = parts[1].replace("【師匠の返答】", "").strip()
                else:
                    user_voice_text = "（解析中...）"
                    bot_reply_text = full_text

                if not is_audio: user_voice_text = text_input

                # 音声合成
                is_slow = True if speed_setting == "🐢 ゆっくり（高齢者向）" else False
                tts = gTTS(text=bot_reply_text, lang='ja', slow=is_slow)
                audio_output = io.BytesIO()
                tts.write_to_fp(audio_output)
                audio_data = audio_output.getvalue()

                # 履歴に追加
                st.session_state.messages.append({"role": "user", "content": user_voice_text})
                st.session_state.messages.append({"role": "assistant", "content": bot_reply_text, "audio": audio_data})
                
                st.rerun()

        except Exception as e:
            st.error(f"通信エラーだ: {e}")
