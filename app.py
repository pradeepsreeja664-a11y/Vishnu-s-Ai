import streamlit as st
from google import genai
import os

# വെബ്സൈറ്റിന്റെ തലക്കെട്ട്
st.title("SSLC Study Helper 📚")
st.write("പഠനം ഉഷാറാക്കാം! നിങ്ങളുടെ ചോദ്യങ്ങൾ താഴെ ചോദിക്കൂ.")

# API Key എടുക്കുന്നു (സുരക്ഷയ്ക്കായി Secrets-ൽ നിന്നും)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("API Key സെറ്റ് ചെയ്തിട്ടില്ല!")
else:
    client = genai.Client(api_key=api_key)
    
    user_input = st.text_input("നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യുക:")
    
    if st.button("ഉത്തരം കണ്ടെത്തുക"):
        if user_input:
            prompt = f"Act as an expert Kerala SSLC teacher with strong knowledge of the school syllabus. Use English words that are simple but get full marks if written. Explain the topic in a simple, accurate, and student-friendly way in both ENGLISH and MALAYALAM. Use plain language that is easy to understand for SSLC students. Follow this format for every point: First write the ENGLISH point clearly. Immediately below it, write the MALAYALAM translation of the same point. Keep the explanation well organized, complete, and easy to study. Use short sentences, direct wording, and exam-friendly language. Do not use complex formatting, markdown, tables, symbols, or LaTeX. Do not use unnecessary decoration. Keep everything in plain text so it looks clean in a basic terminal or text editor. If the topic has multiple ideas, explain them point by point in the same pattern: ENGLISH point MALAYALAM point Make sure the meaning stays accurate in both languages. If needed, simplify difficult terms without changing the concept. Focus on clarity, correctness, and student usefulness. Insert the user’s topic here: {user_input}"
            
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
