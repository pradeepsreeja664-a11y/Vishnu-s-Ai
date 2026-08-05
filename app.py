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

# --- Session State for Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    return "".join([page.extract_text() or "" for page in reader.pages])

def download_gdrive_pdf(url):
    try:
        file_id_match = re.search(r'[/=]([-\w]{25,})', url)
        if not file_id_match:
            return None, "ലിങ്കിൽ നിന്നും ഫയൽ ഐഡി കണ്ടെത്താൻ കഴിഞ്ഞില്ല. ശരിയായ ലിങ്ക് നൽകുക."
        file_id = file_id_match.group(1)
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, allow_redirects=True)
        
        if response.status_code == 200:
            if not response.content.startswith(b'%PDF'):
                return None, "ഡൗൺലോഡ് ചെയ്തത് PDF അല്ല. ഫയൽ സൈസ് കൂടുതലാണ്, അല്ലെങ്കിൽ പെർമിഷൻ ഇല്ല."
            return BytesIO(response.content), "Success"
        else:
            return None, "Google Drive-ൽ നിന്നും ഫയൽ എടുക്കാൻ കഴിഞ്ഞില്ല."
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
    audio_file_path = asyncio.run(_generate())
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(audio_file_path)
    return audio_bytes

# --- API Configuration ---API Key സെറ്റ് ചെയ്യുക (st.secrets വഴി സുരക്ഷിതമായി നൽകാം)
import streamlit as st
import google.generativeai as genai

# Streamlit Secrets-ൽ നിന്നുള്ള കീ എടുക്കുന്നു
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)

# ശരിയായ മോഡൽ നാമം നൽകുക
model = genai.GenerativeModel('gemini-1.5-flash') 
# --- Sidebar Navigation & Settings ---
st.sidebar.title("📌 മെനു")
app_mode = st.sidebar.radio(
    "നിങ്ങൾക്ക് വേണ്ട ഫീച്ചർ തിരഞ്ഞെടുക്കുക:",
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
st.sidebar.title("⚙️ Settings")
with st.sidebar.expander("🎨 Appearance (Theme)"):
    selected_theme_name = st.selectbox("തീം തിരഞ്ഞെടുക്കുക:", list(THEMES.keys()))
    current_theme = THEMES[selected_theme_name]

st.sidebar.markdown("---")
st.sidebar.title("🔐 Account & History")

# Login / Logout Logic
if not st.session_state.logged_in:
    st.sidebar.markdown("പഴയ ചാറ്റുകൾ സേവ് ചെയ്യാൻ ലോഗിൻ ചെയ്യുക:")
    login_email = st.sidebar.text_input("📧 Email Address:", placeholder="example@gmail.com")
    if st.sidebar.button("Login", use_container_width=True):
        if login_email:
            st.session_state.logged_in = True
            st.session_state.user_email = login_email
            st.rerun()
        else:
            st.sidebar.error("ദയവായി ഇമെയിൽ നൽകുക!")
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
                st.caption("ചോദ്യം:")
                st.write(chat[2][:100] + "...")
    else:
        st.sidebar.caption("പഴയ ചാറ്റുകൾ ലഭ്യമല്ല.")


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
    textarea {{ resize: vertical !important; }}
    </style>
""", unsafe_allow_html=True)


# Main UI Header
st.markdown(f"<h1 style='text-align: center; color: {current_theme['accent']};'>SSLC AI Master 🎓</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; opacity: 0.8;'>നോട്ട്സ് നൽകുക, പഠിക്കുക, കേൾക്കുക!</p>", unsafe_allow_html=True)
st.write("---")

# ---------------------------------------------------------
# 0. PDF / Notes Chat (From Code 1)
# ---------------------------------------------------------
if app_mode == "0. പാഠപുസ്തകം / നോട്ട്സ് (PDF Chat)":
    st.header("📄 PDF നോട്ട്സ് അനാലിസിസ്")
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    
    pdf_text = ""
    upload_method = st.radio("എങ്ങനെയാണ് നോട്ട്സ് നൽകുന്നത്?", ("വേണ്ട (ചോദ്യം മാത്രം)", "PDF അപ്‌ലോഡ് ചെയ്യുക", "Google Drive ലിങ്ക് നൽകുക"))
    
    if upload_method == "PDF അപ്‌ലോഡ് ചെയ്യുക":
        uploaded_pdf = st.file_uploader("📄 പാഠപുസ്തകം അല്ലെങ്കിൽ നോട്ട്സ് (PDF):", type=["pdf"])
        if uploaded_pdf is not None:
            pdf_text = extract_text_from_pdf(uploaded_pdf)
            st.success("✅ PDF വിജയകരമായി വായിച്ചെടുത്തു!")
            
    elif upload_method == "Google Drive ലിങ്ക് നൽകുക":
        gdrive_url = st.text_input("🔗 ഗൂഗിൾ ഡ്രൈവ് ലിങ്ക് ഇവിടെ പേസ്റ്റ് ചെയ്യുക (Ensure access is 'Anyone with the link'):")
        if gdrive_url:
            with st.spinner("ഡ്രൈവിൽ നിന്നും ഡൗൺലോഡ് ചെയ്യുന്നു..."):
                pdf_bytes, status = download_gdrive_pdf(gdrive_url)
                if pdf_bytes:
                    pdf_text = extract_text_from_pdf(pdf_bytes)
                    st.success("✅ ഗൂഗിൾ ഡ്രൈവിൽ നിന്നും PDF വിജയകരമായി വായിച്ചെടുത്തു!")
                else:
                    st.error(status)
                    
    user_input = st.text_area("നിങ്ങളുടെ ചോദ്യം അല്ലെങ്കിൽ വിഷയം ഇവിടെ നൽകുക:", placeholder="ഉദാഹരണത്തിന്: എന്താണ് Photosynthesis?", height=120)
    st.caption("💡 വലുതാക്കാൻ ടെക്സ്റ്റ് ബോക്സിന്റെ താഴെ വലത്തേ അറ്റത്ത് ക്ലിക്ക് ചെയ്ത് താഴേക്ക് വലിക്കുക.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("ഉത്തരം കണ്ടെത്തുക 🚀"):
        if user_input or pdf_text:
            combined_input = user_input
            if pdf_text:
                combined_input += f"\n\nContext from PDF:\n{pdf_text[:4000]}"
                
            prompt = f"Act as an expert Kerala SSLC teacher. Explain the topic in a simple, accurate, and student-friendly way. Follow this format: First write the ENGLISH point clearly. Immediately below it, write the MALAYALAM translation. Keep it organized, complete, and easy to study. Topic: {combined_input}"
            
            with st.spinner('AI ഉത്തരം തയ്യാറാക്കുന്നു...'):
                try:
                    response = model.generate_content(prompt)
                    
                    # Save to History ONLY if Logged in
                    if st.session_state.logged_in:
                        save_chat(st.session_state.user_email, user_input if user_input else "PDF Analysis", combined_input, response.text)
                    
                    st.success("✅ ഉത്തരം ലഭിച്ചു!")
                    st.write(response.text)
                    st.markdown("---")
                    
                    st.markdown(f"<h3 style='color: {current_theme['accent']};'>🛠️ Smart Actions</h3>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📄 Download as Word Doc",
                            data=create_docx(response.text),
                            file_name="SSLC_AI_Notes.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                        if st.button("🎧 ഈ ഉത്തരം കേൾക്കാം (High Quality)"):
                            with st.spinner("ഓഡിയോ തയ്യാറാക്കുന്നു..."):
                                audio_bytes = create_audio_improved(response.text)
                                st.audio(audio_bytes, format='audio/mp3')
                                
                    with col2:
                        with st.expander("📝 ഉത്തരം കോപ്പി ചെയ്യാൻ ഇവിടെ ക്ലിക്ക് ചെയ്യുക"):
                            st.code(response.text, language='text')
                            
                except Exception as e:
                    st.error(f"ഒരു പ്രശ്നമുണ്ട്: {e}")
        else:
            st.warning("ദയവായി ചോദ്യം ടൈപ്പ് ചെയ്യുകയോ PDF നൽകുകയോ ചെയ്യുക!")

# ---------------------------------------------------------
# 1. Image / Diagram Analysis
# ---------------------------------------------------------
elif app_mode == "1. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)":
    st.header("📷 ചിത്രങ്ങൾ നൽകി പഠിക്കാം")
    st.write("സയൻസ്, മാത്‌സ് പുസ്തകങ്ങളിലെ ചിത്രങ്ങൾ അപ്‌ലോഡ് ചെയ്യുക. AI അത് വിശദീകരിക്കും.")
    
    uploaded_file = st.file_uploader("ഒരു ചിത്രം അപ്‌ലോഡ് ചെയ്യുക (JPG/PNG)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="അപ്‌ലോഡ് ചെയ്ത ചിത്രം", use_container_width=True)
        prompt = st.text_input("ഈ ചിത്രത്തെക്കുറിച്ച് എന്താണ് അറിയേണ്ടത്? (ഉദാഹരണത്തിന്: ഇത് വിശദീകരിക്കാമോ?)")
        
        if st.button("വിശദീകരണം കണ്ടെത്തുക"):
            with st.spinner("ചിത്രം പരിശോധിക്കുന്നു..."):
                response = model.generate_content([prompt if prompt else "ഈ ചിത്രം വിശദീകരിച്ചു തരുക (മലയാളത്തിൽ).", image])
                st.success("✅ ഉത്തരങ്ങൾ:")
                st.write(response.text)

# ---------------------------------------------------------
# 2. AI Mock Test / Quiz
# ---------------------------------------------------------
elif app_mode == "2. AI Mock Test (ക്വിസ്)":
    st.header("📝 സ്വയം പരീക്ഷിക്കാം (Mock Test)")
    
    topic = st.text_input("ഏത് വിഷയത്തിലാണ് ടെസ്റ്റ് വേണ്ടത്? (ഉദാഹരണത്തിന്: SSLC Physics - പ്രകാശത്തിന്റെ പ്രതിപതനം)")
    if "quiz_data" not in st.session_state:
        st.session_state.quiz_data = None

    if st.button("ക്വിസ് തുടങ്ങുക"):
        if topic:
            with st.spinner("ചോദ്യങ്ങൾ തയ്യാറാക്കുന്നു..."):
                quiz_prompt = f"""
                Create a 5-question multiple choice quiz on the topic: '{topic}' for a 10th-grade student.
                Return ONLY a valid JSON array of objects. Do not include markdown tags like ```json.
                Format: [{{"question": "Question text (in Malayalam)", "options": ["opt1", "opt2", "opt3", "opt4"], "answer": "correct_opt"}}]
                """
                response = model.generate_content(quiz_prompt)
                try:
                    json_text = response.text.strip().replace('```json', '').replace('```', '')
                    st.session_state.quiz_data = json.loads(json_text)
                except Exception as e:
                    st.error("ചോദ്യങ്ങൾ ഉണ്ടാക്കുന്നതിൽ സാങ്കേതിക തകരാർ. വീണ്ടും ശ്രമിക്കുക.")
        else:
            st.warning("ദയവായി ഒരു വിഷയം നൽകുക!")

    if st.session_state.quiz_data:
        st.write("---")
        user_answers = {}
        for i, q in enumerate(st.session_state.quiz_data):
            st.subheader(f"ചോദ്യം {i+1}: {q['question']}")
            user_answers[i] = st.radio("ഉത്തരം തിരഞ്ഞെടുക്കുക:", q['options'], key=f"q_{i}")
        
        if st.button("ഉത്തരങ്ങൾ പരിശോധിക്കുക"):
            score = 0
            for i, q in enumerate(st.session_state.quiz_data):
                if user_answers[i] == q['answer']:
                    score += 1
                    st.success(f"ചോദ്യം {i+1}: ശരിയാണ്! (ഉത്തരം: {q['answer']})")
                else:
                    st.error(f"ചോദ്യം {i+1}: തെറ്റി! (ശരിയായ ഉത്തരം: {q['answer']})")
            st.header(f"നിങ്ങളുടെ സ്കോർ: {score}/5")

# ---------------------------------------------------------
# 3. Voice Input
# ---------------------------------------------------------
elif app_mode == "3. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)":
    st.header("🎙️ സംസാരിച്ച് ചോദ്യം ചോദിക്കാം")
    st.write("ടൈപ്പ് ചെയ്യാൻ ബുദ്ധിമുട്ടുണ്ടോ? താഴെയുള്ള മൈക്ക് ബട്ടണിൽ അമർത്തി ചോദ്യം ചോദിക്കുക.")
    
    text = speech_to_text(language='ml-IN', use_container_width=True, just_once=True, key='STT')
    
    if text:
        st.info(f"നിങ്ങൾ ചോദിച്ചത്: **{text}**")
        with st.spinner("ഉത്തരം കണ്ടെത്തുന്നു..."):
            response = model.generate_content(f"Answer this query in Malayalam: {text}")
            st.write(response.text)

# ---------------------------------------------------------
# 4. YouTube Video Summarizer
# ---------------------------------------------------------
elif app_mode == "4. YouTube Video Summarizer":
    st.header("📺 YouTube ക്ലാസ്സ് നോട്ട്സ്")
    st.write("പഠിക്കാൻ ഉപയോഗിക്കുന്ന യുട്യൂബ് ക്ലാസ്സിന്റെ ലിങ്ക് നൽകുക. പ്രധാന കാര്യങ്ങൾ നോട്ട്സ് ആയി ലഭിക്കും.")
    
    yt_url = st.text_input("YouTube Video Link നൽകുക:")
    
    if st.button("Summary തയ്യാറാക്കുക"):
        if yt_url:
            try:
                parsed_url = urllib.parse.urlparse(yt_url)
                if parsed_url.hostname == 'youtu.be':
                    video_id = parsed_url.path[1:]
                else:
                    video_id = urllib.parse.parse_qs(parsed_url.query)['v'][0]
                
                with st.spinner("വീഡിയോയിലെ വിവരങ്ങൾ ശേഖരിക്കുന്നു..."):
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ml'])
                    transcript_text = " ".join([i['text'] for i in transcript])
                    
                    summary_prompt = f"Summarize the following YouTube transcript into bullet points for a 10th-grade student. Please explain it in Malayalam:\n\n{transcript_text[:5000]}"
                    response = model.generate_content(summary_prompt)
                    
                    st.success("✅ വീഡിയോ നോട്ട്സ്:")
                    st.write(response.text)
            except Exception as e:
                st.error("ഈ വീഡിയോയ്ക്ക് സബ്ടൈറ്റിലുകൾ ലഭ്യമല്ല, അല്ലെങ്കിൽ ലിങ്ക് തെറ്റാണ്.")
        else:
            st.warning("ലിങ്ക് നൽകുക!")

# ---------------------------------------------------------
# 5. Chatbot UI
# ---------------------------------------------------------
elif app_mode == "5. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)":
    st.header("💬 AI Study Assistant")
    st.write("നിങ്ങളുടെ സംശയങ്ങൾ താഴെ ചാറ്റ് വഴി ചോദിക്കുക.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("ചോദ്യം ചോദിക്കുക..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("ചിന്തിക്കുന്നു..."):
            response = model.generate_content(prompt)
            
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

# ---------------------------------------------------------
# 6. Study Planner
# ---------------------------------------------------------
elif app_mode == "6. സ്റ്റഡി പ്ലാനർ (Study Planner)":
    st.header("📅 സ്റ്റഡി പ്ലാനർ & ടൈംടേബിൾ")
    
    col1, col2 = st.columns(2)
    with col1:
        days = st.number_input("പരീക്ഷയ്ക്ക് ഇനി എത്ര ദിവസമുണ്ട്?", min_value=1, max_value=365, value=30)
        hours = st.number_input("ദിവസവും എത്ര മണിക്കൂർ പഠിക്കാൻ കഴിയും?", min_value=1, max_value=24, value=3)
    with col2:
        subjects = st.text_area("പഠിക്കാൻ ബാക്കിയുള്ള വിഷയങ്ങൾ (കോമയിട്ട് നൽകുക):", "Physics, Chemistry, Maths, Malayalam")
        
    if st.button("ടൈംടേബിൾ തയ്യാറാക്കുക"):
        with st.spinner("നിങ്ങൾക്കുള്ള പ്ലാൻ തയ്യാറാക്കുന്നു..."):
            plan_prompt = f"""
            Create a structured study timetable in a Markdown table format.
            Days left: {days} days.
            Daily study hours: {hours} hours.
            Subjects to cover: {subjects}.
            Provide the explanation and strategy in Malayalam, but keep the table headings in English. Ensure it's realistic for a 10th-grade student.
            """
            response = model.generate_content(plan_prompt)
            st.markdown(response.text)

# ---------------------------------------------------------
# 7. Flash Cards
# ---------------------------------------------------------
elif app_mode == "7. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)":
    st.header("⚡ ഫ്ലാഷ് കാർഡുകൾ")
    st.write("പരീക്ഷയ്ക്ക് പോകുന്നതിന് മുൻപ് പെട്ടെന്ന് ഓർത്തെടുക്കാനുള്ള കാർഡുകൾ.")
    
    flash_topic = st.text_input("ഏത് വിഷയമാണ് റിവിഷൻ ചെയ്യേണ്ടത്? (ഉദാ: History Years, Physics Formulas)")
    
    if st.button("കാർഡുകൾ തയ്യാറാക്കുക"):
        if flash_topic:
            with st.spinner("കാർഡുകൾ ഉണ്ടാക്കുന്നു..."):
                flash_prompt = f"""
                Create 6 key flashcards for the topic '{flash_topic}' suitable for a 10th-grade student.
                Format the output strictly as a JSON array without markdown like ```json.
                Format: [{{"title": "Formula / Year / Concept", "description": "Short explanation in Malayalam"}}]
                """
                try:
                    response = model.generate_content(flash_prompt)
                    json_text = response.text.strip().replace('```json', '').replace('```', '')
                    cards = json.loads(json_text)
                    
                    cols = st.columns(3)
                    for idx, card in enumerate(cards):
                        with cols[idx % 3]:
                            with st.container(border=True):
                                st.subheader(card['title'])
                                st.write(card['description'])
                except Exception as e:
                    st.error("കാർഡുകൾ ലോഡ് ചെയ്യുന്നതിൽ പിഴവ് സംഭവിച്ചു. വിഷയം കുറച്ചുകൂടി വ്യക്തമായി നൽകുക.")
        else:
            st.warning("ദയവായി വിഷയം നൽകുക!")
