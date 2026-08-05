import json
import urllib.parse
import streamlit as st
import google.generativeai as genai
from PIL import Image
from youtube_transcript_api import YouTubeTranscriptApi
from streamlit_mic_recorder import speech_to_text

# ---------------------------------------------------------
# 1. Page Configuration (Must be the first Streamlit command)
# ---------------------------------------------------------
st.set_page_config(page_title="SSLC AI Study Buddy", page_icon="🎓", layout="wide")

# ---------------------------------------------------------
# 2. API Configuration (Secure & Updated Model)
# ---------------------------------------------------------
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 404 Error ഒഴിവാക്കാൻ ആധുനിക മോഡൽ ഉപയോഗിക്കുന്നു
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("⚠️ Gemini API Key കണ്ടെത്താനായില്ല! Streamlit Cloud Secrets-ൽ 'GEMINI_API_KEY' ഉണ്ടെന്ന് ഉറപ്പാക്കുക.")
    st.stop()

# ---------------------------------------------------------
# 3. Sidebar Navigation
# ---------------------------------------------------------
st.sidebar.title("📌 മെനു")
app_mode = st.sidebar.radio(
    "നിങ്ങൾക്ക് വേണ്ട ഫീച്ചർ തിരഞ്ഞെടുക്കുക:",
    [
        "1. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)",
        "2. AI Mock Test (ക്വിസ്)",
        "3. വോയിസ് ഇൻപുട്ട് (സംസാരിച്ച് ചോദിക്കാം)",
        "4. YouTube Video Summarizer",
        "5. യഥാർത്ഥ ചാറ്റ് (Chatbot UI)",
        "6. സ്റ്റഡി പ്ലാനർ (Study Planner)",
        "7. ഫ്ലാഷ് കാർഡുകൾ (Quick Revision)"
    ]
)

# ---------------------------------------------------------
# 1. Image / Diagram Analysis
# ---------------------------------------------------------
if app_mode == "1. ചിത്രങ്ങൾ നൽകി പഠിക്കാം (Image Analysis)":
    st.header("📷 ചിത്രങ്ങൾ നൽകി പഠിക്കാം")
    st.write("സയൻസ്, മാത്‌സ് പുസ്തകങ്ങളിലെ ചിത്രങ്ങൾ അപ്‌ലോഡ് ചെയ്യുക. AI അത് വിശദീകരിക്കും.")
    
    uploaded_file = st.file_uploader("ഒരു ചിത്രം അപ്‌ലോഡ് ചെയ്യുക (JPG/PNG)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="അപ്‌ലോഡ് ചെയ്ത ചിത്രം", use_container_width=True)
        
        prompt = st.text_input("ഈ ചിത്രത്തെക്കുറിച്ച് എന്താണ് അറിയേണ്ടത്? (ഉദാഹരണത്തിന്: ഇത് വിശദീകരിക്കാമോ?)")
        
        if st.button("വിശദീകരണം കണ്ടെത്തുക"):
            with st.spinner("ചിത്രം പരിശോധിക്കുന്നു..."):
                query = prompt if prompt else "ഈ ചിത്രം വിശദീകരിച്ചു തരുക (മലയാളത്തിൽ)."
                response = model.generate_content([query, image])
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
                try:
                    response = model.generate_content(quiz_prompt)
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
            response = model.generate_content(f"Answer this query in Malayalam for an SSLC student: {text}")
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
                    
                    summary_prompt = f"Summarize the following YouTube transcript into bullet points for a 10th-grade student in Malayalam:\n\n{transcript_text[:5000]}"
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
            Create a structured study timetable in Markdown table format for a 10th-grade student.
            Days left: {days} days.
            Daily study hours: {hours} hours.
            Subjects to cover: {subjects}.
            Provide the explanation and strategy in Malayalam.
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
