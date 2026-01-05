import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
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
    /* 文字サイズ設定 */
    p, div, input, textarea, button { font-size: 1.0em !important; }
    
    .stButton > button {
        background-color: #4a4a4a;
        color: white;
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: bold;
        width: 100%;
    }
    .stButton > button:hover { background-color: #8c2f2f; color: white; }
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

# --- サイドバー：工具箱（設定） ---
with st.sidebar:
    st.markdown("### 🔧 鉄の工具箱")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    
    # ★ここが新機能：速度切り替えスイッチ★
    st.markdown("### 🔊 音声設定")
    speed_setting = st.radio(
        "読み上げ速度",
        ("🐢 ゆっくり（高齢者向）", "🐇 普通（サクサク）"),
        index=0 # 初期値は「ゆっくり」
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
st.markdown("<p style='text-align: center; opacity: 0.8;'>マイクボタンを押して、腹の底から喋れ。</p>", unsafe_allow_html=True)
st.divider()

# --- 履歴表示 ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='bot-msg'>{msg['content']}</div>", unsafe_allow_html=True)
        if "audio" in msg:
            st.audio(msg["audio"], format="audio/mp3")

# --- 入力エリア ---
st.write("### 🗣️ 声で相談する")
c1, c2 = st.columns([1, 3])

with c1:
    audio = mic_recorder(start_prompt="🎙️ 録音開始", stop_prompt="⏹️ 完了", just_once=True, key='recorder')
with c2:
    st.info("左のボタンを押して話し、もう一度押すと送信されるぞ。")

with st.expander("筆談（キーボード）で挑む"):
    with st.form(key="text_form", clear_on_submit=True):
        text_input = st.text_area("相談内容", height=70)
        submit_btn = st.form_submit_button("送信")

# --- 処理ロジック ---
input_content = None
is_audio = False

if audio:
    input_content = audio['bytes']
    is_audio = True
elif submit_btn and text_input:
    input_content = text_input
    is_audio = False

if input_content:
    if not api_key:
        st.error("おい、工具箱（サイドバー）にAPIキーが入ってねぇぞ！")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash-exp", system_instruction=SYSTEM_PROMPT)
            
            with st.spinner("師匠が腹に力を入れている……"):
                if is_audio:
                    response = model.generate_content([
                        "以下の音声を文字起こしして、返答せよ。",
                        {"mime_type": "audio/wav", "data": input_content}
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

                # --- ★ここが新機能：速度切り替えロジック ---
                # サイドバーで選んだ設定に合わせて、slowをTrue/False切り替え
                is_slow = True if speed_setting == "🐢 ゆっくり（高齢者向）" else False
                
                tts = gTTS(text=bot_reply_text, lang='ja', slow=is_slow)
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                audio_data = audio_bytes.getvalue()

                st.session_state.messages.append({"role": "user", "content": user_voice_text})
                st.session_state.messages.append({"role": "assistant", "content": bot_reply_text, "audio": audio_data})
                
                st.rerun()

        except Exception as e:
            st.error(f"通信エラーだ: {e}")