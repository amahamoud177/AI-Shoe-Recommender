import os
import warnings

# 1. SILENCE WARNINGS & LOGS
os.environ["ORT_LOGGING_LEVEL"] = "3"
os.environ["ORT_LOGGING_LEVEL_DEFAULT"] = "3"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import streamlit as st
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from google import genai
from google.genai import types

warnings.filterwarnings("ignore", category=RuntimeWarning, module="streamlit.util")

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
valid_user = os.getenv("APP_USER")
valid_pass = os.getenv("APP_PASS")

if not api_key:
    st.error("API Key missing! Please ensure your .env file is set up correctly.")
    st.stop()

# Initialize the Gemini GenAI Client
client = genai.Client(api_key=api_key)

# 2. Page Styling (Heritage Luxury Theme)
st.set_page_config(page_title="Semantic Sneaker", page_icon="👞", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Playfair Display', serif;
        background-color: #050706; /* Onyx Black */
        color: #fdfdfc; /* Clean White */
    }
    
    h1, h2, h3 {
        color: #D4AF37 !important; /* Champagne Gold */
        text-align: center;
    }
    
    .stChatInputContainer {
        border: 1px solid rgba(212, 175, 55, 0.4) !important;
        border-radius: 10px;
    }
    
    /* Result Card Styling */
    .sneaker-card {
        border: 1px solid rgba(212, 175, 55, 0.4);
        padding: 20px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.02);
        text-align: center;
        margin-top: 15px;
    }
    .tag {
        font-size: 0.8rem;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 15px;
        background: rgba(212, 175, 55, 0.1);
        color: #D4AF37;
        border: 1px solid rgba(212, 175, 55, 0.3);
        margin: 2px;
        display: inline-block;
    }
    
    /* Login Form Styling */
    div[data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(212, 175, 55, 0.4);
        padding: 2rem;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)


# 3. Vector Database Setup
@st.cache_resource
def initialize_vector_db():
    """Initializes ChromaDB and populates it with demo sneakers."""
    db_client = chromadb.Client(Settings(anonymized_telemetry=False))
    
    try:
        db_client.delete_collection("luxury_sneakers")
    except Exception:
        pass
        
    collection = db_client.create_collection("luxury_sneakers")
    
    sneakers = [
        {"id": "1", "name": "Air Jordan 4 Retro 'Thunder'", "desc": "High-contrast, bold, confident, black and yellow streetwear.", "tags": ["Confident", "High-Contrast"]},
        {"id": "2", "name": "Nike Dunk Low 'Argon'", "desc": "Cool, relaxed, sky blue and white, perfect for styling with dark leather.", "tags": ["Color Match", "Streetwear"]},
        {"id": "3", "name": "Adidas Samba OG", "desc": "Classic, minimalist, white and black leather, old money, understated elegance.", "tags": ["Minimalist", "Heritage"]}
    ]
    
    ids = [s["id"] for s in sneakers]
    documents = [s["desc"] for s in sneakers]
    metadatas = [{"name": s["name"], "tags": ",".join(s["tags"])} for s in sneakers]
    
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return collection


# 4. Authentication Logic
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login():
    st.title("Client Portal")
    st.markdown("<p style='text-align: center; color: #8e9590;'>Please authenticate to access the curation tool.</p>", unsafe_allow_html=True)
    
    # Create a centered column for the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Authenticate")
            
            if submit:
                if username == valid_user and password == valid_pass:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Access denied.")

def logout():
    st.session_state["authenticated"] = False
    st.rerun()

# 5. Main App Routing
if not st.session_state["authenticated"]:
    # Lock the user out and show login screen
    login()
else:
    # --- The user is authenticated, run the main app ---
    collection = initialize_vector_db()

    # Add a logout button to the sidebar
    with st.sidebar:
        st.write(f"Logged in as: **{valid_user}**")
        st.button("Secure Logout", on_click=logout)

    st.title("Semantic Sneaker Sourcing")
    st.markdown("<p style='text-align: center; color: #8e9590;'>AI-driven curation tailored to your mood and aesthetic.</p>", unsafe_allow_html=True)
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Welcome back, {valid_user}. Tell me about your current vibe, or what kind of outfit you are styling today."}
        ]

    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            if "html" in msg:
                st.markdown(msg["html"], unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])

    if user_prompt := st.chat_input("Describe your mood or fit..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Curating your profile..."):
                
                results = collection.query(
                    query_texts=[user_prompt],
                    n_results=1
                )
                
                match_found = len(results["ids"][0]) > 0
                
                if match_found:
                    best_match_meta = results["metadatas"][0][0]
                    best_match_doc = results["documents"][0][0]
                    sneaker_name = best_match_meta["name"]
                    tags = best_match_meta["tags"].split(",")
                    
                    system_instruction = "You are a high-end fashion stylist. Briefly explain why this specific sneaker matches the user's mood. Keep it under 3 sentences. Be elegant and confident."
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"User's mood: {user_prompt}\nSneaker chosen: {sneaker_name}\nSneaker profile: {best_match_doc}",
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        )
                    )
                    
                    ai_text = response.text
                    
                    tags_html = "".join([f"<span class='tag'>{tag}</span>" for tag in tags])
                    card_html = f"""
                    <div class="sneaker-card">
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 10px;">{sneaker_name}</div>
                        <div style="margin-bottom: 15px;">{tags_html}</div>
                    </div>
                    """
                    
                    st.markdown(ai_text)
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_text, "html": ai_text + card_html})
                    
                else:
                    fallback_msg = "I couldn't find an exact match for that aesthetic in our current archives. Could you describe your style a bit differently?"
                    st.markdown(fallback_msg)
                    st.session_state.messages.append({"role": "assistant", "content": fallback_msg})