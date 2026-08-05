import streamlit as st
from google import genai
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

# 2. Themes Palette (20 Premium Themes)
THEMES = {
    "1. Ultra Dark Premium": {"bg": "#0B0F19", "card": "#111827", "text": "#F9FAFB", "accent": "#6366F1", "border": "#1F2937"},
    "2. Glassmorphism Navy": {"bg": "#0F172A", "card": "#1E293B", "text": "#F8FAFC", "accent": "#38BDF8", "border": "#334155"},
    "3. Neon Cyberpunk": {"bg": "#0D0221", "card": "#1A0836", "text": "#00F5D4", "accent": "#FF007F", "border": "#7B2CBF"},
    "8. Classic Light": {"bg": "#F8FAFC", "card": "#FFFFFF", "text": "#0F172A", "accent": "#2563EB", "border": "#E2E8F0"},
    # Add your other themes here... (kept short for brevity)
}

# --- Sidebar: Settings & Chat History ---
st.sidebar.title("⚙️ Settings & History")

# User Login / Email for History
user_email = st.sidebar.text_input("📧 ജിമെയിൽ ഐഡി നൽകുക (History Save ചെയ്യാൻ):", placeholder="example@gmail.com")

with st.sidebar.expander("🎨 Appearance (Theme)"):
    selected_theme_name = st.selectbox("തീം തിരഞ്ഞെടുക്കുക:", list(THEMES.keys()))
    current_theme = THEMES[selected_theme_name]

# Chat History Section
st.sidebar.markdown("### 🕒 പഴയ ചാറ്റുകൾ")
if user_email:
    past_chats = get_history(user_email)
    if past_chats:
        for chat in past_chats:
            with st.sidebar.expander(f"📝 {chat[1][:25]}..."):
                st.caption("ചോദ്യം:")
                st.write(chat[2][:100] + "...")
                # Option to load this chat into the main view could be added here
    else:
        st.sidebar.caption("പഴയ ചാറ്റുകൾ ലഭ്യമല്ല.")
else:
    st.sidebar.caption("ഹിസ്റ്ററി കാണാൻ ഇമെയിൽ നൽകുക.")

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
    /* Making text area resizable easily at the bottom right */
    textarea {{
        resize: vertical !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Main UI Header
st.markdown(f"<h1 style='text-align: center; color: {current_theme['accent']};'>SSLC AI Master 🎓</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; opacity: 0.8;'>നോട്ട്സ് നൽകുക, പഠിക്കുക, കേൾക്കുക!</p>", unsafe_allow_html=True)

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    return "".join([page.extract_text() or "" for page in reader.pages])

def download_gdrive_pdf(url):
    try:
        # Extract File ID from Google Drive URL
        file_id_match = re.search(r'[/=]([-\w]{25,})', url)
        if not file_id_match:
            return None, "Invalid Google Drive URL"
        file_id = file_id_match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        if response.status_code == 200:
            return BytesIO(response.content), "Success"
        else:
            return None, "Failed to download from Drive. Ensure link is 'Anyone with the link can view'."
    except Exception as e:
        return None, str(e)

def create_docx(text):
    doc = docx.Document()
    doc.add_heading('SSLC Study Notes', 0)
    doc.add_paragraph(text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# Improved Text to Speech using edge-tts (Natural Malayalam Voice)
def create_audio_improved(text):
    async def _generate():
        # ml-IN-SobhanaNeural is a highly natural Malayalam female voice
        communicate = edge_tts.Communicate(text, "ml-IN-SobhanaNeural")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    
    audio_file_path = asyncio.run(_generate())
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(audio_file_path) # Cleanup
    return audio_bytes

# API Key Validation
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ API Key സെറ്റ് ചെയ്തിട്ടില്ല! ദയവായി GEMINI_API_KEY നൽകുക.")
else:
    client = genai.Client(api_key=api_key)
    
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    
    # Context Input (File or Drive Link)
    pdf_text = ""
    upload_method = st.radio("എങ്ങനെയാണ് നോട്ട്സ് നൽകുന്നത്?", ("PDF അപ്‌ലോഡ് ചെയ്യുക", "Google Drive ലിങ്ക് നൽകുക", "വേണ്ട (ചോദ്യം മാത്രം)"))
    
    if upload_method == "PDF അപ്‌ലോഡ് ചെയ്യുക":
        uploaded_pdf = st.file_uploader("📄 പാഠപുസ്തകം അല്ലെങ്കിൽ നോട്ട്സ് (PDF):", type=["pdf"])
        if uploaded_pdf is not None:
            pdf_text = extract_text_from_pdf(uploaded_pdf)
            st.success("✅ PDF വിജയകരമായി വായിച്ചെടുത്തു!")
            
    elif upload_method == "Google Drive ലിങ്ക് നൽകുക":
        gdrive_url = st.text_input("🔗 ഗൂഗിൾ ഡ്രൈവ് ലിങ്ക് ഇവിടെ പേസ്റ്റ് ചെയ്യുക (Ensure link access is 'Public'):")
        if gdrive_url:
            with st.spinner("ഡ്രൈവിൽ നിന്നും ഡൗൺലോഡ് ചെയ്യുന്നു..."):
                pdf_bytes, status = download_gdrive_pdf(gdrive_url)
                if pdf_bytes:
                    pdf_text = extract_text_from_pdf(pdf_bytes)
                    st.success("✅ ഗൂഗിൾ ഡ്രൈവിൽ നിന്നും PDF വിജയകരമായി വായിച്ചെടുത്തു!")
                else:
                    st.error(f"Error: {status}")

    # Main Typing Box (Resizable corner at bottom-right)
    user_input = st.text_area("നിങ്ങളുടെ ചോദ്യം അല്ലെങ്കിൽ വിഷയം ഇവിടെ നൽകുക:", 
                              placeholder="ഉദാഹരണത്തിന്: എന്താണ് Photosynthesis?", 
                              height=120) 
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
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    
                    # Save to History if email is provided
                    if user_email:
                        save_chat(user_email, user_input if user_input else "PDF Analysis", combined_input, response.text)
                    
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
                        
                        # High-Quality Audio Feature
                        if st.button("🎧 ഈ ഉത്തരം കേൾക്കാം (High Quality)"):
                            with st.spinner("ഓഡിയോ തയ്യാറാക്കുന്നു (കുറച്ചു സമയം എടുക്കാം)..."):
                                audio_bytes = create_audio_improved(response.text)
                                st.audio(audio_bytes, format='audio/mp3')
                                
                    with col2:
                        with st.expander("📝 ഉത്തരം കോപ്പി ചെയ്യാൻ ഇവിടെ ക്ലിക്ക് ചെയ്യുക"):
                            st.code(response.text, language='text')
                            
                except Exception as e:
                    st.error(f"ഒരു പ്രശ്നമുണ്ട്: {e}")
        else:
            st.warning("ദയവായി ചോദ്യം ടൈപ്പ് ചെയ്യുകയോ PDF നൽകുകയോ ചെയ്യുക!")
