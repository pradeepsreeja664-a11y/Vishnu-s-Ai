import streamlit as st
import google.generativeai as genai
import os
import pypdf
import docx
from io import BytesIO
import sqlite3
import re
import requests
import asyncio
import edge_tts
import tempfile
from PIL import Image
from youtube_transcript_api import YouTubeTranscriptApi
import json
import urllib.parse
from streamlit_mic_recorder import speech_to_text

# 1. Page Configuration
st.set_page_config(page_title="SSLC AI Master 📚", page_icon="🎓", layout="wide")

# --- Database Setup for Chat History ---
def init_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, topic TEXT, prompt TEXT, response TEXT)''')
    conn.commit()
    return conn

conn = init_db()

def save_chat(email, topic, prompt, response):
    c = conn.cursor()
    c.execute("INSERT INTO history (email, topic, prompt, response) VALUES (?, ?, ?, ?)", (email, topic, prompt, response))
    conn.commit()

def get_history(email):
    c = conn.cursor()
    c.execute("SELECT id, topic, prompt, response FROM history WHERE email = ? ORDER BY id DESC", (email,))
    return c.fetchall()

# 2. Themes Palette
THEMES = {
    "1. Ultra Dark Premium": {"bg": "#0B0F19", "card": "#111827", "text": "#F9FAFB", "accent": "#6366F1", "border": "#1F2937"},
    "2. Glassmorphism Navy": {"bg": "#0F172A", "card": "#1E293B", "text": "#F8FAFC", "accent": "#38BDF8", "border": "#334155"},
    "3. Neon Cyberpunk": {"bg": "#0D0221", "card": "#1A0836", "text": "#00F5D4", "accent": "#FF007F", "border": "#7B2CBF"},
    "4. Classic Light": {"bg": "#F8FAFC", "card": "#FFFFFF", "text": "#0F172A", "accent": "#2563EB", "border": "#E2E8F0"},
}

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    return "".join([page.extract_text() or "" for page in reader.pages])

def download_gdrive_pdf(url):
    try:
        file_id_match = re.search(r'[/=]([-\w]{25,})', url)
        if not file_id_match:
            return None, "ലിങ്കിൽ നിന്നും ഫയൽ ഐഡി കണ്ടെത്താൻ കഴിഞ്ഞില്ല."
        file_id = file_id_match.group(1)
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, allow_redirects=True)
        
        if response.status_code == 200 and response.content.startswith(b'%PDF'):
            return BytesIO(response.content), "Success"
        else:
            return None, "ഡൗൺലോഡ് ചെയ്തത് PDF അല്ല അല്ലെങ്കിൽ പെർമിഷൻ ഇല്ല."
    except Exception as e:
        return None, f"Error: {str(e)}"

def create_docx(text):
    doc = docx.Document()
    doc.add_heading('SSLC Study Notes', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_audio_improved(text):
    async def _generate():
        communicate = edge_tts.Communicate(text, "ml-IN-SobhanaNeural")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    try:
        audio_file_path = asyncio.run(_generate())
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        os.remove(audio_file_path)
        return audio_bytes
    except Exception as e:
        return None

# --- Sidebar: API Key, Menu & Settings ---
st.sidebar.title("🔑 API Key Setup")
api_input = st.sidebar.text_input("നിങ്ങളുടെ Gemini API Key നൽകുക:", type="password", value=st.session_state.api_key)
if api_input:
    st.session_state.api_key = api_input
    genai.configure(api_key=st.session_state.api_key)
else:
    st.sidebar.warning("ആപ്പ് പ്രവർത്തിക്കാൻ API Key നൽകുക!")

st.sidebar.markdown("---")
st.sidebar.title("📌 മെനു")
app_mode = st.sidebar.radio(
    "ഫീച്ചർ തിരഞ്ഞെടുക്കുക:",
    ["0. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)",
     "1. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)",
     "2. AI Mock Test (ക്വിസ്)",
     "3. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)",
     "4. YouTube Video Summarizer",
     "5. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)",
     "6. സ്റ്റഡി പ്ലാനർ (Study Planner)",
     "7. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)"]
)

st.sidebar.markdown("---")
with st.sidebar.expander("🎨 Appearance (Theme)"):
    selected_theme_name = st.selectbox("തീം തിരഞ്ഞെടുക്കുക:", list(THEMES.keys()))
    current_theme = THEMES[selected_theme_name]

st.sidebar.markdown("---")
st.sidebar.title("🔐 Account & History")

if not st.session_state.logged_in:
    login_email = st.sidebar.text_input("📧 Email Address:", placeholder="example@gmail.com")
    if st.sidebar.button("Login", use_container_width=True):
        if login_email:
            st.session_state.logged_in = True
            st.session_state.user_email = login_email
            st.rerun()
else:
    st.sidebar.success(f"👤 ലോഗിൻ ചെയ്തു:\n{st.session_state.user_email}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
        
    st.sidebar.markdown("### 🕒 നിങ്ങളുടെ ഹിസ്റ്ററി")
    past_chats = get_history(st.session_state.user_email)
    if past_chats:
        for chat in past_chats:
            with st.sidebar.expander(f"📝 {chat[1][:25]}..."):
                st.write(chat[2][:100] + "...")
    else:
        st.sidebar.caption("പഴയ ചാറ്റുകൾ ലഭ്യമല്ല.")
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: red;'>Created by <b>Vishnu</b> 💻</p>", unsafe_allow_html=True)

# Dynamic CSS Injection
st.markdown(f"""
    <style>
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; }}
    .stApp, p, span, div, label, h1, h2, h3, h4 {{ color: {current_theme['text']} !important; }}
    .main-card {{
        background-color: {current_theme['card']};
        border: 1px solid {current_theme['border']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }}
    .stButton>button {{
        background: linear-gradient(135deg, {current_theme['accent']}, {current_theme['border']}) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 700 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Stop execution if API key is not provided
if not st.session_state.api_key:
    st.warning("⚠️ ആപ്പ് ഉപയോഗിക്കാൻ സൈഡ്‌ബാറിൽ നിങ്ങളുടെ Gemini API Key നൽകുക.")
    st.stop()

# Initialize Model (Using 3.6 Flash)
model = genai.GenerativeModel('gemini-3.6-flash')

st.markdown(f"<h1 style='text-align: center; color: {current_theme['accent']};'>SSLC AI Master 🎓</h1>", unsafe_allow_html=True)
st.write("---")

# ---------------------------------------------------------
# 0. PDF / Notes Chat
# ---------------------------------------------------------
if app_mode == "0. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)":
    st.header("📄 PDF നോട്ട്സ് അനാലിസിസ്")
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    
    pdf_text = ""
    upload_method = st.radio("എങ്ങനെയാണ് നോട്ട്സ് നൽകുന്നത്?", ("വേണ്ട (ചോദ്യം മാത്രം)", "PDF അപ്‌ലോഡ് ചെയ്യുക", "Google Drive ലിങ്ക് നൽകുക"))
    
    if upload_method == "PDF അപ്‌ലോഡ് ചെയ്യുക":
        uploaded_pdf = st.file_uploader("📄 പാഠപുസ്തകം (PDF):", type=["pdf"])
        if uploaded_pdf is not None:
            pdf_text = extract_text_from_pdf(uploaded_pdf)
            st.success("✅ PDF വായിച്ചെടുത്തു!")
            
    elif upload_method == "Google Drive ലിങ്ക് നൽകുക":
        gdrive_url = st.text_input("🔗 ഗൂഗിൾ ഡ്രൈവ് ലിങ്ക്:")
        if gdrive_url:
            with st.spinner("ഡൗൺലോഡ് ചെയ്യുന്നു..."):
                pdf_bytes, status = download_gdrive_pdf(gdrive_url)
                if pdf_bytes:
                    pdf_text = extract_text_from_pdf(pdf_bytes)
                    st.success("✅ PDF വായിച്ചെടുത്തു!")
                else:
                    st.error(status)
                    
    user_input = st.text_area("ചോദ്യം നൽകുക:", height=120)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("ഉത്തരം കണ്ടെത്തുക 🚀"):
        if user_input or pdf_text:
            combined_input = user_input
            if pdf_text:
                combined_input += f"\n\nContext:\n{pdf_text[:4000]}"
                
            prompt = f"Act as an expert Kerala SSLC teacher. Explain the topic simply. Write the ENGLISH point first, then MALAYALAM translation below it. Topic: {combined_input}"
            
            with st.spinner('AI ഉത്തരം തയ്യാറാക്കുന്നു...'):
                try:
                    response = model.generate_content(prompt)
                    if st.session_state.logged_in:
                        save_chat(st.session_state.user_email, user_input if user_input else "PDF Analysis", combined_input, response.text)
                    
                    st.success("✅ ഉത്തരം ലഭിച്ചു!")
                    st.write(response.text)
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("📄 Download Doc", create_docx(response.text), "Notes.docx")
                        if st.button("🎧 കേൾക്കാം"):
                            with st.spinner("ഓഡിയോ തയ്യാറാക്കുന്നു..."):
                                audio_bytes = create_audio_improved(response.text)
                                if audio_bytes:
                                    st.audio(audio_bytes, format='audio/mp3')
                                else:
                                    st.error("ഓഡിയോ ഉണ്ടാക്കുന്നതിൽ തകരാർ.")
                    with col2:
                        with st.expander("📝 കോപ്പി ചെയ്യാൻ"):
                            st.code(response.text, language='text')
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("ചോദ്യം നൽകുക!")

# ---------------------------------------------------------
# 1. Image Analysis
# ---------------------------------------------------------
elif app_mode == "1. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)":
    st.header("📷 ചിത്രങ്ങൾ നൽകി പഠിക്കാം")
    uploaded_file = st.file_uploader("ചിത്രം അപ്‌ലോഡ് ചെയ്യുക", type=["jpg", "png", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)
        prompt = st.text_input("എന്താണ് അറിയേണ്ടത്?")
        if st.button("കണ്ടെത്തുക"):
            with st.spinner("പരിശോധിക്കുന്നു..."):
                try:
                    response = model.generate_content([prompt if prompt else "വിശദീകരിച്ചു തരുക (മലയാളത്തിൽ).", image])
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------------------------------------------------
# 2. Mock Test
# ---------------------------------------------------------
elif app_mode == "2. AI Mock Test (ക്വിസ്)":
    st.header("📝 സ്വയം പരീക്ഷിക്കാം")
    topic = st.text_input("ഏത് വിഷയത്തിലാണ് ടെസ്റ്റ് വേണ്ടത്?")
    if "quiz_data" not in st.session_state:
        st.session_state.quiz_data = None

    if st.button("ക്വിസ് തുടങ്ങുക"):
        if topic:
            with st.spinner("ചോദ്യങ്ങൾ തയ്യാറാക്കുന്നു..."):
                quiz_prompt = f"Create a 5-question multiple choice quiz on '{topic}' for 10th-grade. Return ONLY a valid JSON array of objects. Format: [{{\"question\": \"Q in Malayalam\", \"options\": [\"o1\", \"o2\", \"o3\", \"o4\"], \"answer\": \"correct_opt\"}}]"
                try:
                    response = model.generate_content(quiz_prompt)
                    json_text = response.text.strip().replace('```json', '').replace('```', '')
                    st.session_state.quiz_data = json.loads(json_text)
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.quiz_data:
        user_answers = {}
        for i, q in enumerate(st.session_state.quiz_data):
            user_answers[i] = st.radio(f"{i+1}. {q['question']}", q['options'], key=f"q_{i}")
        
        if st.button("പരിശോധിക്കുക"):
            score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['answer']])
            st.header(f"സ്കോർ: {score}/5")

# ---------------------------------------------------------
# 3. Voice Input
# ---------------------------------------------------------
elif app_mode == "3. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)":
    st.header("🎙️ സംസാരിച്ച് ചോദ്യം ചോദിക്കാം")
    text = speech_to_text(language='ml-IN', use_container_width=True, just_once=True, key='STT')
    if text:
        st.info(f"ചോദ്യം: **{text}**")
        with st.spinner("കണ്ടെത്തുന്നു..."):
            try:
                response = model.generate_content(f"Answer in Malayalam: {text}")
                st.write(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# ---------------------------------------------------------
# 4. YouTube Summarizer
# ---------------------------------------------------------
elif app_mode == "4. YouTube Video Summarizer":
    st.header("📺 YouTube ക്ലാസ്സ് നോട്ട്സ്")
    yt_url = st.text_input("YouTube Link നൽകുക:")
    if st.button("Summary തയ്യാറാക്കുക") and yt_url:
        try:
            parsed_url = urllib.parse.urlparse(yt_url)
            video_id = parsed_url.path[1:] if parsed_url.hostname == 'youtu.be' else urllib.parse.parse_qs(parsed_url.query)['v'][0]
            with st.spinner("ശേഖരിക്കുന്നു..."):
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ml'])
                transcript_text = " ".join([i['text'] for i in transcript])
                response = model.generate_content(f"Summarize in Malayalam bullet points:\n\n{transcript_text[:5000]}")
                st.write(response.text)
        except Exception as e:
            st.error("സബ്ടൈറ്റിലുകൾ ലഭ്യമല്ല.")

# ---------------------------------------------------------
# 5. Chatbot UI
# ---------------------------------------------------------
elif app_mode == "5. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)":
    st.header("💬 AI Study Assistant")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("ചോദ്യം ചോദിക്കുക..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("ചിന്തിക്കുന്നു..."):
            try:
                response = model.generate_content(prompt)
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")

# ---------------------------------------------------------
# 6. Study Planner
# ---------------------------------------------------------
elif app_mode == "6. സ്റ്റഡി പ്ലാനർ (Study Planner)":
    st.header("📅 സ്റ്റഡി പ്ലാനർ")
    days = st.number_input("ദിവസങ്ങൾ?", min_value=1, value=30)
    hours = st.number_input("മണിക്കൂർ?", min_value=1, value=3)
    subjects = st.text_area("വിഷയങ്ങൾ:", "Physics, Chemistry, Maths")
    if st.button("തയ്യാറാക്കുക"):
        with st.spinner("പ്ലാൻ തയ്യാറാക്കുന്നു..."):
            try:
                response = model.generate_content(f"Create a study timetable in Markdown. Days: {days}, Hours: {hours}, Subjects: {subjects}. Explain strategy in Malayalam.")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# ---------------------------------------------------------
# 7. Flash Cards
# ---------------------------------------------------------
elif app_mode == "7. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)":
    st.header("⚡ ഫ്ലാഷ് കാർഡുകൾ")
    flash_topic = st.text_input("ഏത് വിഷയമാണ് റിവിഷൻ ചെയ്യേണ്ടത്?")
    if st.button("തയ്യാറാക്കുക") and flash_topic:
        with st.spinner("ഉണ്ടാക്കുന്നു..."):
            try:
                flash_prompt = f"Create 6 key flashcards for '{flash_topic}' for 10th-grade. Format strictly as JSON array: [{{\"title\": \"Concept\", \"description\": \"Malayalam explanation\"}}]"
                response = model.generate_content(flash_prompt)
                cards = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                cols = st.columns(3)
                for idx, card in enumerate(cards):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.subheader(card['title'])
                            st.write(card['description'])
            except Exception as e:
                st.error("പിഴവ് സംഭവിച്ചു.")
