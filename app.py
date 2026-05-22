import os
import streamlit as st
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Configuration & Security
# Silence ChromaDB telemetry warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Load the secure API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

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
    </style>
""", unsafe_allow_html=True)


# 3. Vector Database Setup & Mock Data
@st.cache_resource
def initialize_vector_db():
    """Initializes ChromaDB and populates it with some demo sneakers."""
    db_client = chromadb.Client()
    
    # Reset collection for the demo to avoid duplicates
    try:
        db_client.delete_collection("luxury_sneakers")
    except Exception:
        pass
        
    collection = db_client.create_collection("luxury_sneakers")
    
    # Demo Inventory - Replace this with your actual dataset later
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

collection = initialize_vector_db()


# 4. App UI & Chat State
st.title("Semantic Sneaker Sourcing")
st.markdown("<p style='text-align: center; color: #8e9590;'>AI-driven curation tailored to your mood and aesthetic.</p>", unsafe_allow_html=True)
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome. Tell me about your current vibe, or what kind of outfit you are styling today."}
    ]

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        if "html" in msg:
            st.markdown(msg["html"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])


# 5. Core RAG Pipeline
if user_prompt := st.chat_input("Describe your mood or fit..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Curating your profile..."):
            
            # Step A: Query the Vector Database based on user's prompt
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
                
                # Step B: Ask Gemini to introduce the shoe like a luxury stylist
                system_instruction = "You are a high-end fashion stylist. Briefly explain why this specific sneaker matches the user's mood. Keep it under 3 sentences. Be elegant and confident."
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"User's mood: {user_prompt}\nSneaker chosen: {sneaker_name}\nSneaker profile: {best_match_doc}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    )
                )
                
                ai_text = response.text
                
                # Step C: Format the Result Card
                tags_html = "".join([f"<span class='tag'>{tag}</span>" for tag in tags])
                card_html = f"""
                <div class="sneaker-card">
                    <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 10px;">{sneaker_name}</div>
                    <div style="margin-bottom: 15px;">{tags_html}</div>
                </div>
                """
                
                st.markdown(ai_text)
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Save to history
                st.session_state.messages.append({"role": "assistant", "content": ai_text, "html": ai_text + card_html})
                
            else:
                fallback_msg = "I couldn't find an exact match for that aesthetic in our current archives. Could you describe your style a bit differently?"
                st.markdown(fallback_msg)
                st.session_state.messages.append({"role": "assistant", "content": fallback_msg})