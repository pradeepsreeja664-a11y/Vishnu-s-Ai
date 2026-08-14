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
from fpdf import FPDF
import uuid
from streamlit_cookies_controller import CookieController

# 1. Page Configuration
st.set_page_config(page_title="SSLC AI Master 📚", page_icon="🎓", layout="wide")

# Cookie Controller for Persistent Login
controller = CookieController()

# --- Database Setup for Chat History ---
def init_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (session_id TEXT PRIMARY KEY, email TEXT, title TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT)''')
    conn.commit()
    return conn

conn = init_db()

def save_chat_message(session_id, email, role, content):
    c = conn.cursor()
    c.execute("SELECT session_id FROM chat_sessions WHERE session_id=?", (session_id,))
    if not c.fetchone():
        title = content[:25] + "..." if len(content) > 25 else content
        c.execute("INSERT INTO chat_sessions (session_id, email, title) VALUES (?, ?, ?)", (session_id, email, title))
    c.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()

def get_chat_sessions(email):
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM chat_sessions WHERE email = ? ORDER BY rowid DESC", (email,))
    return c.fetchall()

def get_chat_messages(session_id):
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    return c.fetchall()

# 2. Themes Palette
THEMES = {
    "1. Ultra Dark Premium": {"bg": "#0B0F19", "card": "#111827", "text": "#F9FAFB", "accent": "#6366F1", "border": "#1F2937"},
    "2. Glassmorphism Navy": {"bg": "#0F172A", "card": "#1E293B", "text": "#F8FAFC", "accent": "#38BDF8", "border": "#334155"},
    "3. Neon Cyberpunk": {"bg": "#0D0221", "card": "#1A0836", "text": "#00F5D4", "accent": "#FF007F", "border": "#7B2CBF"},
    "4. Classic Light": {"bg": "#F8FAFC", "card": "#FFFFFF", "text": "#0F172A", "accent": "#2563EB", "border": "#E2E8F0"},
}

# 3. Extensive Voice Dictionary
VOICES = {
    "മലയാളം - ശോഭന (Malayalam Female)": "ml-IN-SobhanaNeural",
    "മലയാളം - മിഥുൻ (Malayalam Male)": "ml-IN-MidhunNeural",
    "English (India) - Neerja (Female)": "en-IN-NeerjaNeural",
    "English (India) - Prabhat (Male)": "en-IN-PrabhatNeural",
    "English (US) - Aria (Female)": "en-US-AriaNeural",
    "English (US) - Guy (Male)": "en-US-GuyNeural",
    "English (US) - Jenny (Female)": "en-US-JennyNeural",
    "English (US) - Christopher (Male)": "en-US-ChristopherNeural",
    "English (US) - Michelle (Female)": "en-US-MichelleNeural",
    "English (US) - Eric (Male)": "en-US-EricNeural",
    "English (US) - Roger (Male)": "en-US-RogerNeural",
    "English (UK) - Sonia (Female)": "en-GB-SoniaNeural",
    "English (UK) - Ryan (Male)": "en-GB-RyanNeural",
    "English (UK) - Libby (Female)": "en-GB-LibbyNeural",
    "English (UK) - Thomas (Male)": "en-GB-ThomasNeural",
    "English (Australia) - Natasha (Female)": "en-AU-NatashaNeural",
    "English (Australia) - William (Male)": "en-AU-WilliamNeural",
    "English (Canada) - Clara (Female)": "en-CA-ClaraNeural",
    "English (Canada) - Liam (Male)": "en-CA-LiamNeural",
    "English (South Africa) - Leah (Female)": "en-ZA-LeahNeural",
    "English (South Africa) - Luke (Male)": "en-ZA-LukeNeural",
    "മലയാളം - Standard A (Female)": "ml-IN-Standard-A",
    "മലയാളം - Standard B (Male)": "ml-IN-Standard-B", 
    "മലയാളം - Standard C (Female)": "ml-IN-Standard-C",
    "മലയാളം - Standard D (Male)": "ml-IN-Standard-D",
    "മലയാളം - Wavenet A (Female)": "ml-IN-Wavenet-A",
    "മലയാളം - Wavenet B (Male)": "ml-IN-Wavenet-B",
    "മലയാളം - Wavenet C (Female)": "ml-IN-Wavenet-C",
    "മലയാളം - Wavenet D (Male)": "ml-IN-Wavenet-D",
   "മലയാളം - Aditi (Female)": "Aditi", 
    "മലയാളം - Raveena (Female)": "Raveena",
    "മലയാളം - Bella (Female)": "Bella",
    "മലയാളം - Antoni (Male)": "Antoni",
    "മലയാളം - Elli (Female)": "Elli",
    "മലയാളം - Josh (Male)": "Josh",
    "മലയാളം - Rachel (Female)": "Rachel",
    "മലയാളം - en-US_MichaelV3Voice (Male)": "en-US_MichaelV3Voice",
    "മലയാളം - Ananya (Female)": "Ananya",
    "മലയാളം - Arjun (Male)": "Arjun",
    "മലയാളം - Kavya (Female)": "Kavya",
    "മലയാളം - Aadhya (Female)": "ml-IN-Aadhya",
    "മലയാളം - Arnav (Male)": "ml-IN-Arnav"
}

# --- Session States ---
if "logged_in" not in st.session_state: 
    st.session_state.logged_in = False
    st.session_state.user_email = ""

if "current_session_id" not in st.session_state: 
    st.session_state.current_session_id = str(uuid.uuid4())
    
if "selected_voice" not in st.session_state:
    st.session_state.selected_voice = "ml-IN-SobhanaNeural"

# Persistent Login Check
if not st.session_state.logged_in:
    cookie_email = controller.get('user_email')
    if cookie_email:
        st.session_state.logged_in = True
        st.session_state.user_email = cookie_email

for i in range(8):
    if f"out_{i}" not in st.session_state:
        st.session_state[f"out_{i}"] = ""

if "app_mode_select" not in st.session_state:
    st.session_state.app_mode_select = "1. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)"

# --- Helper Functions ---
def create_docx(text):
    doc = docx.Document()
    doc.add_heading('SSLC AI Smart Notes', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_pdf(text):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica", size=12)
        safe_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=safe_text)
        return bytes(pdf.output(dest='S'))
    except Exception: return b""

def create_audio_improved(text, voice):
    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    try:
        audio_file_path = asyncio.run(_generate())
        with open(audio_file_path, "rb") as f: audio_bytes = f.read()
        os.remove(audio_file_path)
        return audio_bytes
    except Exception: return None

def render_smart_actions(text_content, feature_id):
    st.markdown("---")
    st.markdown(f"### 🛠️ സേവ് ചെയ്യാം (Save & Share)")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.download_button("📄 Word (Docx)", create_docx(text_content), f"Result_{feature_id}.docx", key=f"docx_{feature_id}")
    with col2: st.download_button("📕 PDF", create_pdf(text_content), f"Result_{feature_id}.pdf", key=f"pdf_{feature_id}")
    with col3:
        if st.button("🎧 ഓഡിയോ കേൾക്കാം", key=f"audio_{feature_id}"):
            with st.spinner("ഓഡിയോ തയ്യാറാക്കുന്നു..."):
                audio_bytes = create_audio_improved(text_content, st.session_state.selected_voice)
                if audio_bytes: st.audio(audio_bytes, format='audio/mp3')
                else: st.error("ഓഡിയോ ഉണ്ടാക്കുന്നതിൽ തകരാർ.")
    with col4:
        with st.expander("📝 കോപ്പി ചെയ്യാൻ"): st.code(text_content, language='text')

def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    return "".join([page.extract_text() or "" for page in reader.pages])

def download_gdrive_pdf(url):
    try:
        file_id_match = re.search(r'[/=]([-\w]{25,})', url)
        if not file_id_match: return None, "ലിങ്കിൽ നിന്നും ഫയൽ ഐഡി കണ്ടെത്താൻ കഴിഞ്ഞില്ല."
        download_url = f"https://drive.google.com/uc?export=download&id={file_id_match.group(1)}"
        response = requests.get(download_url, allow_redirects=True)
        if response.status_code == 200 and response.content.startswith(b'%PDF'):
            return BytesIO(response.content), "Success"
        else: return None, "ഡൗൺലോഡ് ചെയ്തത് PDF അല്ല."
    except Exception as e: return None, f"Error: {str(e)}"

# ==========================================
# 🔑 API KEY CONFIGURATION
# ==========================================
MY_GEMINI_API_KEY = "AIzaSyB-YOUR_API_KEY_HERE" # <--- നിന്റെ API Key ഇവിടെ പേസ്റ്റ് ചെയ്യുക

try:
    api_key_to_use = st.secrets.get("GEMINI_API_KEY", MY_GEMINI_API_KEY)
except:
    api_key_to_use = MY_GEMINI_API_KEY

if api_key_to_use == "AIzaSyB-YOUR_API_KEY_HERE":
    st.error("⚠️ കോഡിൽ API Key നൽകിയിട്ടില്ല! app.py ഫയലിൽ നിന്റെ API Key നൽകുക.")
    st.stop()

genai.configure(api_key=api_key_to_use)
model = genai.GenerativeModel('gemini-3.5-flash') 


# --- Sidebar Setup ---
st.sidebar.title("📌 മെനു")
app_mode = st.sidebar.radio(
    "ഫീച്ചർ തിരഞ്ഞെടുക്കുക:",
    ["1. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)",
     "2. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)",
     "3. AI Mock Test (ക്വിസ്)",
     "4. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)",
     "5. YouTube Video Summarizer",
     "6. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)",
     "7. സ്റ്റഡി പ്ലാനർ (Study Planner)",
     "8. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)"],
    key="app_mode_select"
)

st.sidebar.markdown("---")
with st.sidebar.expander("🎨 Appearance (Theme)"):
    selected_theme_name = st.selectbox("തീം തിരഞ്ഞെടുക്കുക:", list(THEMES.keys()))
    current_theme = THEMES[selected_theme_name]

st.sidebar.markdown("---")
st.sidebar.title("🔊 Audio Settings")
selected_voice_name = st.sidebar.selectbox("വോയിസ് തിരഞ്ഞെടുക്കുക:", list(VOICES.keys()))
st.session_state.selected_voice = VOICES[selected_voice_name]

if st.sidebar.button("▶️ Test Voice (മുൻകൂട്ടി കേൾക്കാം)", use_container_width=True):
    with st.spinner("തയ്യാറാക്കുന്നു..."):
        test_text = "നമസ്കാരം, ഇത് എന്റെ ശബ്ദമാണ്. നിങ്ങളുടെ പഠനത്തിനായി ഞാൻ സഹായിക്കാം." if "Malayalam" in selected_voice_name else "Hello there! This is a sample of my voice. I am ready to help you with your studies."
        test_audio = create_audio_improved(test_text, st.session_state.selected_voice)
        if test_audio:
            st.sidebar.audio(test_audio, format='audio/mp3')

st.sidebar.markdown("---")
st.sidebar.title("🔐 Login (Permanent)")
st.sidebar.caption("ലോഗിൻ ചെയ്താൽ പിന്നീട് വെബ്സൈറ്റ് ക്ലോസ് ചെയ്താലും ലോഗൗട്ട് ആവില്ല.")

if not st.session_state.logged_in:
    login_email = st.sidebar.text_input("📧 Email Address:", placeholder="example@gmail.com")
    if st.sidebar.button("Login", use_container_width=True) and login_email:
        controller.set('user_email', login_email)
        st.session_state.logged_in = True
        st.session_state.user_email = login_email
        st.rerun()
else:
    st.sidebar.success(f"👤 {st.session_state.user_email}")
    if st.sidebar.button("Logout", use_container_width=True):
        controller.remove('user_email')
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.current_session_id = str(uuid.uuid4())
        st.rerun()
        
    st.sidebar.markdown("### 🕒 നിന്റെ ചാറ്റുകൾ")
    
    # --- FIXED ERROR SECTION: Using Callbacks ---
    def start_new_chat():
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.app_mode_select = "6. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)"
        
    def load_existing_chat(sess_id):
        st.session_state.current_session_id = sess_id
        st.session_state.app_mode_select = "6. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)"

    # Button with on_click callback
    st.sidebar.button("➕ New Chat", use_container_width=True, on_click=start_new_chat)

    sessions = get_chat_sessions(st.session_state.user_email)
    if sessions:
        for sess_id, title in sessions:
            st.sidebar.button(f"💬 {title}", key=f"btn_{sess_id}", use_container_width=True, on_click=load_existing_chat, args=(sess_id,))
    # ---------------------------------------------

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: gray;'>Created by <b>Vishnu</b> 💻</p>", unsafe_allow_html=True)

# Dynamic CSS
st.markdown(f"""
    <style>
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; }}
    .stApp, p, span, div, label, h1, h2, h3, h4 {{ color: {current_theme['text']} !important; }}
    .main-card {{ background-color: {current_theme['card']}; border: 1px solid {current_theme['border']}; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 20px; }}
    .stButton>button {{ background: linear-gradient(135deg, {current_theme['accent']}, {current_theme['border']}) !important; color: #FFFFFF !important; border: none !important; border-radius: 12px !important; padding: 12px 24px !important; font-weight: 700 !important; }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='text-align: center; color: {current_theme['accent']};'>SSLC AI Master 🎓</h1>", unsafe_allow_html=True)
st.write("---")

# =============================================================================
# 0. PDF / Notes Chat
# =============================================================================
if app_mode == "1. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)":
    st.header("📄 PDF നോട്ട്സ് അനാലിസിസ്")
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    pdf_text = ""
    upload_method = st.radio("എങ്ങനെയാണ് നോട്ട്സ് നൽകുന്നത്?", ("വേണ്ട (ചോദ്യം മാത്രം)", "PDF അപ്‌ലോഡ് ചെയ്യുക", "Google Drive ലിങ്ക് നൽകുക"))
    
    if upload_method == "PDF അപ്‌ലോഡ് ചെയ്യുക":
        uploaded_pdfs = st.file_uploader("📄 പാഠപുസ്തകം (PDF) - Max 20:", type=["pdf"], accept_multiple_files=True)
        if uploaded_pdfs: 
            for pdf in uploaded_pdfs[:20]:
                pdf_text += extract_text_from_pdf(pdf) + "\n\n"
    elif upload_method == "Google Drive ലിങ്ക് നൽകുക":
        gdrive_url = st.text_input("🔗 ഗൂഗിൾ ഡ്രൈവ് ലിങ്ക്:")
        if gdrive_url:
            with st.spinner("ഡൗൺലോഡ് ചെയ്യുന്നു..."):
                pdf_bytes, status = download_gdrive_pdf(gdrive_url)
                if pdf_bytes: pdf_text = extract_text_from_pdf(pdf_bytes)
                
    user_input = st.text_area("ചോദ്യം നൽകുക:", height=120)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("ഉത്തരം കണ്ടെത്തുക 🚀"):
        if user_input or pdf_text:
            combined_input = user_input + (f"\n\nContext:\n{pdf_text[:10000]}" if pdf_text else "")
            with st.spinner('AI ഉത്തരം തയ്യാറാക്കുന്നു...'):
                try:
                    response = model.generate_content(f"Act as an expert Kerala SSLC teacher. Explain the topic simply. Topic: {combined_input}")
                    st.session_state.out_0 = response.text
                except Exception as e: st.error(f"Error: {e}")
                
    if st.session_state.out_0:
        st.write(st.session_state.out_0)
        render_smart_actions(st.session_state.out_0, "0")

# =============================================================================
# 1. Image Analysis
# =============================================================================
elif app_mode == "2. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)":
    st.header("📷 ചിത്രങ്ങൾ നൽകി പഠിക്കാം")
    
    uploaded_files = st.file_uploader("ചിത്രങ്ങൾ അപ്‌ലോഡ് ചെയ്യുക (Max 20)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        images_to_process = []
        cols = st.columns(4) 
        for idx, file in enumerate(uploaded_files[:20]):
            img = Image.open(file)
            images_to_process.append(img)
            with cols[idx % 4]: 
                st.image(img, use_container_width=True)
                
        prompt = st.text_input("എന്താണ് അറിയേണ്ടത്?")
        if st.button("കണ്ടെത്തുക"):
            with st.spinner("പരിശോധിക്കുന്നു..."):
                try:
                    content_list = [prompt if prompt else "വിശദീകരിച്ചു തരുക (മലയാളത്തിൽ)."] + images_to_process
                    response = model.generate_content(content_list)
                    st.session_state.out_1 = response.text
                except Exception as e: st.error(f"Error: {e}")
                
    if st.session_state.out_1:
        st.write(st.session_state.out_1)
        render_smart_actions(st.session_state.out_1, "1")

# =============================================================================
# 2. Mock Test
# =============================================================================
elif app_mode == "3. AI Mock Test (ക്വിസ്)":
    st.header("📝 സ്വയം പരീക്ഷിക്കാം")
    topic = st.text_input("ഏത് വിഷയത്തിലാണ് ടെസ്റ്റ് വേണ്ടത്?")
    if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
    
    if st.button("ക്വിസ് തുടങ്ങുക"):
        if topic:
            with st.spinner("ചോദ്യങ്ങൾ തയ്യാറാക്കുന്നു..."):
                try:
                    response = model.generate_content(f"Create a 5-question multiple choice quiz on '{topic}' for 10th-grade. Return ONLY a valid JSON array of objects. Format: [{{\"question\": \"Q in Malayalam\", \"options\": [\"o1\", \"o2\", \"o3\", \"o4\"], \"answer\": \"correct_opt\"}}]")
                    st.session_state.quiz_data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                    quiz_str = f"📝 Mock Test: {topic}\n\n"
                    for i, q in enumerate(st.session_state.quiz_data): quiz_str += f"Q{i+1}: {q['question']}\nAns: {q['answer']}\n\n"
                    st.session_state.out_2 = quiz_str
                except Exception as e: st.error(f"Error: {e}")
                
    if st.session_state.quiz_data:
        user_answers = {}
        for i, q in enumerate(st.session_state.quiz_data):
            user_answers[i] = st.radio(f"{i+1}. {q['question']}", q['options'], key=f"q_{i}")
        if st.button("പരിശോധിക്കുക"):
            score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_answers[i] == q['answer']])
            st.header(f"സ്കോർ: {score}/5")
            st.success("ഉത്തരങ്ങൾ താഴെ സേവ് ചെയ്യാം!")
            
    if st.session_state.out_2:
        render_smart_actions(st.session_state.out_2, "2")

# =============================================================================
# 3. Voice Input
# =============================================================================
elif app_mode == "4. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)":
    st.header("🎙️ സംസാരിച്ച് ചോദ്യം ചോദിക്കാം")
    
    components_html = """
    <div style="text-align: center; margin-top: 20px;">
        <button id="start-btn" style="padding: 15px 30px; font-size: 18px; border-radius: 50px; background-color: #6366F1; color: white; border: none; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🎙️ സംസാരിക്കാൻ തുടങ്ങുക</button>
        <p id="status" style="color: gray; margin-top: 10px;">മൈക്ക് ഓഫ് ആണ്.</p>
        <textarea id="output" rows="4" style="width: 100%; padding: 10px; font-size: 16px; border-radius: 10px; border: 1px solid #ccc; margin-top: 10px;" placeholder="നിങ്ങൾ പറയുന്നത് ഇവിടെ തനിയെ ടൈപ്പ് ചെയ്യപ്പെടും..."></textarea>
    </div>
    <script>
        const startBtn = document.getElementById('start-btn');
        const statusTxt = document.getElementById('status');
        const outputBox = document.getElementById('output');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'ml-IN'; 
            
            let isRecording = false;
            
            startBtn.addEventListener('click', () => {
                if(!isRecording) {
                    recognition.start();
                    startBtn.innerText = "🛑 നിർത്തുക";
                    startBtn.style.backgroundColor = "#EF4444";
                    statusTxt.innerText = "ശ്രദ്ധിക്കുന്നു... സംസാരിച്ചോളൂ!";
                    isRecording = true;
                } else {
                    recognition.stop();
                    startBtn.innerText = "🎙️ സംസാരിക്കാൻ തുടങ്ങുക";
                    startBtn.style.backgroundColor = "#6366F1";
                    statusTxt.innerText = "റെക്കോർഡിങ് നിർത്തി. താഴെ കാണുന്ന ചോദ്യം കോപ്പി ചെയ്തു AI-ക്ക് നൽകുക.";
                    isRecording = false;
                }
            });
            
            recognition.onresult = (event) => {
                let transcript = '';
                for (let i = 0; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                outputBox.value = transcript;
            };
        } else {
            statusTxt.innerText = "നിങ്ങളുടെ ബ്രൗസറിൽ ഈ ഫീച്ചർ സപ്പോർട്ട് ചെയ്യുന്നില്ല.";
        }
    </script>
    """
    st.components.v1.html(components_html, height=250)
    
    st.info("👆 മുകളിൽ റെക്കോർഡ് ചെയ്ത ചോദ്യം താഴെയുള്ള ബോക്സിൽ നൽകുക:")
    voice_query = st.text_input("ചോദ്യം ഇവിടെ പേസ്റ്റ് ചെയ്യുക:")
    
    if st.button("ഉത്തരം കണ്ടെത്തുക"):
        with st.spinner("കണ്ടെത്തുന്നു..."):
            try:
                response = model.generate_content(f"Answer in Malayalam: {voice_query}")
                st.session_state.out_3 = response.text
            except Exception as e: st.error(f"Error: {e}")
            
    if st.session_state.out_3:
        st.write(st.session_state.out_3)
        render_smart_actions(st.session_state.out_3, "3")

# =============================================================================
# 4. YouTube Summarizer
# =============================================================================
elif app_mode == "5. YouTube Video Summarizer":
    st.header("📺 YouTube ക്ലാസ്സ് നോട്ട്സ്")
    yt_url = st.text_input("YouTube Link നൽകുക:")
    if st.button("Summary തയ്യാറാക്കുക") and yt_url:
        try:
            parsed_url = urllib.parse.urlparse(yt_url)
            video_id = parsed_url.path[1:] if parsed_url.hostname == 'youtu.be' else urllib.parse.parse_qs(parsed_url.query)['v'][0]
            with st.spinner("ശേഖരിക്കുന്നു..."):
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ml'])
                response = model.generate_content(f"Summarize in Malayalam bullet points:\n\n{' '.join([i['text'] for i in transcript])[:5000]}")
                st.session_state.out_4 = response.text
        except Exception as e: st.error("സബ്ടൈറ്റിലുകൾ ലഭ്യമല്ല.")
        
    if st.session_state.out_4:
        st.write(st.session_state.out_4)
        render_smart_actions(st.session_state.out_4, "4")

# =============================================================================
# 5. Chatbot UI (With Memory & Smart Actions)
# =============================================================================
elif app_mode == "6. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)":
    st.header("💬 AI Study Assistant")
    session_id = st.session_state.current_session_id
    
    current_email = st.session_state.user_email if st.session_state.logged_in else f"guest_{session_id}"
    
    db_messages = get_chat_messages(session_id)
    
    for role, content in db_messages:
        with st.chat_message(role): st.markdown(content)

    if prompt := st.chat_input("നിങ്ങളുടെ സംശയം ചോദിക്കുക..."):
        st.chat_message("user").markdown(prompt)
        save_chat_message(session_id, current_email, "user", prompt)

        gemini_history = [{"role": "model" if r == "assistant" else "user", "parts": [c]} for r, c in db_messages]

        with st.spinner("ചിന്തിക്കുന്നു..."):
            try:
                chat_session = model.start_chat(history=gemini_history)
                response = chat_session.send_message(prompt)
                st.session_state.out_5 = response.text
                with st.chat_message("assistant"): st.markdown(response.text)
                save_chat_message(session_id, current_email, "assistant", response.text)
            except Exception as e: st.error(f"Error: {e}")

    if st.session_state.out_5:
        render_smart_actions(st.session_state.out_5, "5")

# =============================================================================
# 6. Study Planner
# =============================================================================
elif app_mode == "7. സ്റ്റഡി പ്ലാനർ (Study Planner)":
    st.header("📅 സ്റ്റഡി പ്ലാനർ")
    days = st.number_input("ദിവസങ്ങൾ?", min_value=1, value=30)
    hours = st.number_input("മണിക്കൂർ?", min_value=1, value=3)
    subjects = st.text_area("വിഷയങ്ങൾ:", "Physics, Chemistry, Maths")
    if st.button("തയ്യാറാക്കുക"):
        with st.spinner("പ്ലാൻ തയ്യാറാക്കുന്നു..."):
            try:
                response = model.generate_content(f"Create a study timetable in Markdown. Days: {days}, Hours: {hours}, Subjects: {subjects}. Explain strategy in Malayalam.")
                st.session_state.out_6 = response.text
            except Exception as e: st.error(f"Error: {e}")
            
    if st.session_state.out_6:
        st.markdown(st.session_state.out_6)
        render_smart_actions(st.session_state.out_6, "6")

# =============================================================================
# 7. Flash Cards
# =============================================================================
elif app_mode == "8. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)":
    st.header("⚡ ഫ്ലാഷ് കാർഡുകൾ")
    flash_topic = st.text_input("ഏത് വിഷയമാണ് റിവിഷൻ ചെയ്യേണ്ടത്?")
    if "flash_cards_data" not in st.session_state: st.session_state.flash_cards_data = None
    
    if st.button("തയ്യാറാക്കുക") and flash_topic:
        with st.spinner("ഉണ്ടാക്കുന്നു..."):
            try:
                flash_prompt = f"Create 10 key flashcards for '{flash_topic}' for 10th-grade. Provide explanation in BOTH English and Malayalam. Format strictly as JSON array: [{{\"title\": \"Concept\", \"description\": \"English.\\n\\nമലയാളം.\"}}]"
                response = model.generate_content(flash_prompt)
                st.session_state.flash_cards_data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                cards_str = f"⚡ ഫ്ലാഷ് കാർഡുകൾ: {flash_topic}\n\n"
                for card in st.session_state.flash_cards_data: cards_str += f"📌 {card['title']}\n{card['description']}\n\n"
                st.session_state.out_7 = cards_str
            except Exception as e: st.error("പിഴവ് സംഭവിച്ചു.")
            
    if st.session_state.flash_cards_data:
        cols = st.columns(3)
        for idx, card in enumerate(st.session_state.flash_cards_data):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(card['title'])
                    st.write(card['description'])
                    
    if st.session_state.out_7:
        render_smart_actions(st.session_state.out_7, "7")
