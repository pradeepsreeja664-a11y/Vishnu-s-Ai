import streamlit as st
from google import genai
import os
import pypdf

# 1. Page Configuration
st.set_page_config(page_title="SSLC Study Helper 📚", page_icon="📚", layout="centered")

# 2. 20 Ultra Premium Themes Palette
THEMES = {
    "1. Ultra Dark Premium": {"bg": "#0B0F19", "card": "#111827", "text": "#F9FAFB", "accent": "#6366F1", "border": "#1F2937"},
    "2. Glassmorphism Navy": {"bg": "#0F172A", "card": "#1E293B", "text": "#F8FAFC", "accent": "#38BDF8", "border": "#334155"},
    "3. Neon Cyberpunk": {"bg": "#0D0221", "card": "#1A0836", "text": "#00F5D4", "accent": "#FF007F", "border": "#7B2CBF"},
    "4. Sunset Gold": {"bg": "#1C1917", "card": "#292524", "text": "#FDE68A", "accent": "#F59E0B", "border": "#44403C"},
    "5. Emerald Nature": {"bg": "#064E3B", "card": "#047857", "text": "#ECFDF5", "accent": "#10B981", "border": "#065F46"},
    "6. Ocean Breeze": {"bg": "#0C4A6E", "card": "#075985", "text": "#E0F2FE", "accent": "#38BDF8", "border": "#0369A1"},
    "7. Midnight Purple": {"bg": "#2E1065", "card": "#3B0764", "text": "#F3E8FF", "accent": "#A855F7", "border": "#581C87"},
    "8. Classic Light": {"bg": "#F8FAFC", "card": "#FFFFFF", "text": "#0F172A", "accent": "#2563EB", "border": "#E2E8F0"},
    "9. Rose Gold": {"bg": "#1F1116", "card": "#2D1922", "text": "#FFE4E6", "accent": "#FB7185", "border": "#4C2434"},
    "10. Dracula Dark": {"bg": "#282A36", "card": "#44475A", "text": "#F8F8F2", "accent": "#BD93F9", "border": "#6272A4"},
    "11. Monokai Pro": {"bg": "#2D2A2E", "card": "#403E41", "text": "#FCFCFA", "accent": "#FFD866", "border": "#5B585C"},
    "12. Nord Ice": {"bg": "#2E3440", "card": "#3B4252", "text": "#ECEFF4", "accent": "#88C0D0", "border": "#434C5E"},
    "13. Solarized Dark": {"bg": "#002B36", "card": "#073642", "text": "#93A1A1", "accent": "#2AA198", "border": "#586E75"},
    "14. Royal Velvet": {"bg": "#18002E", "card": "#2A004F", "text": "#E9D5FF", "accent": "#C084FC", "border": "#3B006B"},
    "15. Coffee Warmth": {"bg": "#1C1412", "card": "#2C201C", "text": "#EFEBE9", "accent": "#D7CCC8", "border": "#3E2723"},
    "16. Synthwave 84": {"bg": "#1A1B26", "card": "#24283B", "text": "#7AA2F7", "accent": "#BB9AF7", "border": "#414868"},
    "17. Crimson Red": {"bg": "#1A0505", "card": "#2D0A0A", "text": "#FEE2E2", "accent": "#EF4444", "border": "#450A0A"},
    "18. Galaxy Nebula": {"bg": "#0B021C", "card": "#170B38", "text": "#E0E7FF", "accent": "#818CF8", "border": "#2E1B6B"},
    "19. Mint Fresh": {"bg": "#022C22", "card": "#064E3B", "text": "#D1FAE5", "accent": "#34D399", "border": "#065F46"},
    "20. Slate Steel": {"bg": "#1E293B", "card": "#334155", "text": "#F1F5F9", "accent": "#94A3B8", "border": "#475569"}
}

# 3. Sidebar Theme Selection
st.sidebar.title("🎨 Theme Selector")
selected_theme_name = st.sidebar.selectbox("20 പ്രീമിയം തീമുകളിൽ നിന്ന് ഒന്ന് തിരഞ്ഞെടുക്കുക:", list(THEMES.keys()))
current_theme = THEMES[selected_theme_name]

# Dynamic CSS Injection for Ultra Premium UI
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {current_theme['bg']} !important;
        color: {current_theme['text']} !important;
    }}
    .stApp, p, span, div, label, h1, h2, h3, h4 {{
        color: {current_theme['text']} !important;
    }}
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
        width: 100%;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 5px 15px {current_theme['accent']}80;
    }}
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
        background-color: {current_theme['card']} !important;
        color: {current_theme['text']} !important;
        border: 1px solid {current_theme['border']} !important;
        border-radius: 10px !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Main UI Header
st.markdown(f"<h1 style='text-align: center; color: {current_theme['accent']};'>SSLC Study Helper 📚</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; opacity: 0.8;'>പഠനം ഉഷാറാക്കാം! നിങ്ങളുടെ ചോദ്യങ്ങൾ ചോദിക്കുക അല്ലെങ്കിൽ നോട്ട്സ് PDF അപ്‌ലോഡ് ചെയ്യുക.</p>", unsafe_allow_html=True)

# Helper Function for PDF Processing
def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""
    return extracted_text

# API Key Validation
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ API Key സെറ്റ് ചെയ്തിട്ടില്ല! Secrets-ൽ GEMINI_API_KEY ചേർക്കുക.")
else:
    client = genai.Client(api_key=api_key)

    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    
    # PDF Upload Input
    uploaded_pdf = st.file_uploader("📄 പാഠപുസ്തകം അല്ലെങ്കിൽ നോട്ട്സ് (PDF) അപ്‌ലോഡ് ചെയ്യാം (Optional):", type=["pdf"])
    
    pdf_text = ""
    if uploaded_pdf is not None:
        try:
            pdf_text = extract_text_from_pdf(uploaded_pdf)
            st.success("✅ PDF വിജയകരമായി വായിച്ചെടുത്തു!")
        except Exception as e:
            st.error(f"PDF വായിക്കുന്നതിൽ തടസ്സം: {e}")

    # Text Input
    user_input = st.text_area("നിങ്ങളുടെ ചോദ്യം അല്ലെങ്കിൽ വിഷയം ഇവിടെ നൽകുക:", placeholder="ഉദാഹരണത്തിന്: Photosynthesis എന്നാൽ എന്ത്?")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("ഉത്തരം കണ്ടെത്തുക 🚀"):
        if user_input or pdf_text:
            combined_input = user_input
            if pdf_text:
                combined_input += f"\n\nContext from Uploaded PDF Content:\n{pdf_text[:4000]}" # Passing extracted PDF text context

            prompt = f"Act as an expert Kerala SSLC teacher with strong knowledge of the school syllabus. Use English words that are simple but get full marks if written. Explain the topic in a simple, accurate, and student-friendly way in both ENGLISH and MALAYALAM. Use plain language that is easy to understand for SSLC students. Follow this format for every point: First write the ENGLISH point clearly. Immediately below it, write the MALAYALAM translation of the same point. Keep the explanation well organized, complete, and easy to study. Use short sentences, direct wording, and exam-friendly language. Do not use complex formatting, markdown, tables, symbols, or LaTeX. Do not use unnecessary decoration. Keep everything in plain text so it looks clean in basic text output. If the topic has multiple ideas, explain them point by point in the same pattern: ENGLISH point MALAYALAM point Make sure the meaning stays accurate in both languages. If needed, simplify difficult terms without changing the concept. Focus on clarity, correctness, and student usefulness. Insert the user’s topic and PDF context here: {combined_input}"

            with st.spinner('ഉത്തരം തയ്യാറാക്കുന്നു...'):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    st.success("ഉത്തരം ലഭിച്ചു!")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"ഒരു പ്രശ്നമുണ്ട്. കാരണം ഇതാണ്: {e}")
        else:
            st.warning("ദയവായി ചോദ്യം ടൈപ്പ് ചെയ്യുകയോ PDF അപ്‌ലോഡ് ചെയ്യുകയോ ചെയ്യുക!")
