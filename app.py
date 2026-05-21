import os
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types
import chromadb  
from dotenv import load_dotenv

# Load your custom environment file right at startup
load_dotenv(dotenv_path="key.env")

# =====================================================================
# BACKEND, API, & VECTOR DATABASE CONFIGURATION
# =====================================================================

def get_gemini_client():
    """Initializes the official Gemini API client securely from environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Error: GEMINI_API_KEY not found. Please check your key.env file.")
        st.stop()
    return genai.Client(api_key=api_key)

def get_embedding(client, text: str):
    """Generates mathematical vector embeddings for RAG search."""
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    return response.embeddings[0].values

@st.cache_resource
def initialize_vector_db():
    """
    Creates an in-memory database and populates it with your shoe catalog.
    Using @st.cache_resource stops it from recreating the database every click.
    """
    client = get_gemini_client()
    chroma_client = chromadb.EphemeralClient()
    collection = chroma_client.create_collection(name="shoe_catalog")
    
    # Your project's shoe inventory
    catalog = [
        {"id": "s1", "text": "Black Leather Oxford Shoes: Perfect for formal suits, tuxedos, and smart business wear."},
        {"id": "s2", "text": "Classic White Sneakers: Clean, low-top leather shoes ideal for casual jeans, shorts, and summer street style."},
        {"id": "s3", "text": "Tan Suede Chelsea Boots: Great for smart-casual layers, chinos, and autumn fashion looks."},
        {"id": "s4", "text": "Neon Athletic Runners: High-performance gym shoes built for sportswear, tracksuits, and active running looks."}
    ]
    
    for item in catalog:
        vector = get_embedding(client, item["text"])
        collection.add(
            ids=[item["id"]],
            embeddings=[vector],
            documents=[item["text"]]
        )
    return collection

# =====================================================================
# PROMPT ENGINEERING & LLM CHAINING
# =====================================================================

def analyze_outfit_image(client, image):
    """
    CHAIN 1: Multimodal LLM call. Looks at the image and extracts style keywords.
    Also handles safety/edge-case filtering.
    """
    system_instruction = (
        "You are an AI Stylist. Analyze the user's outfit image.\n"
        "1. Describe the clothing type and color palette in one short sentence.\n"
        "2. Provide 3 simple search keywords matching this style (e.g., 'formal business', 'casual street').\n"
        "3. If the image contains NO clothing or human outfit, reply strictly with: 'INVALID: No outfit detected.'"
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image, "Analyze this image for footwear matching."],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2
        )
    )
    return response.text

def get_final_chat_response(client, outfit_description, matched_shoe, user_message=""):
    """
    CHAIN 2: Synthesis Call. 
    Dynamically adjusts its prompt so it doesn't repeat old context on follow-up questions.
    """
    # CASE 1: This is the very first recommendation after the image upload
    if not user_message:
        prompt = (
            f"You are a helpful customer service chatbot for a shoe store.\n"
            f"The customer is wearing: {outfit_description}.\n"
            f"From our store inventory, we retrieved this match: {matched_shoe}.\n\n"
            f"Craft a friendly initial chat response welcoming them and telling them why this "
            f"specific shoe completes their look."
        )
    
    # CASE 2: The user is asking a follow-up question in the chat box
    else:
        prompt = (
            f"You are a helpful customer service chatbot for a shoe store.\n"
            f"BACKGROUND CONTEXT:\n"
            f"- The customer's outfit: {outfit_description}\n"
            f"- Our recommended inventory match: {matched_shoe}\n\n"
            f"CURRENT USER QUESTION: {user_message}\n\n"
            f"INSTRUCTION: Do not re-introduce yourself or repeat the initial recommendation. "
            f"Directly answer the user's current question naturally using the background context if relevant."
        )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

# =====================================================================
# STREAMLIT UI & INTERACTIVE CHAT INTERFACE
# =====================================================================

def main():
    st.set_page_config(page_title="AI Shoe Recommender", page_icon="👟")
    st.title("👟 AI Shoe Recommender Agent")
    st.caption("SQ4014 Real World AI Coursework Prototype")
    
    client = get_gemini_client()
    
    # Setup Vector DB once at startup
    if "vector_db" not in st.session_state:
        st.session_state.vector_db = initialize_vector_db()
        
    # Maintain session state memory for our chatbot interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "outfit_context" not in st.session_state:
        st.session_state.outfit_context = None
    if "shoe_context" not in st.session_state:
        st.session_state.shoe_context = None

    # Image upload section
    uploaded_file = st.file_uploader("Step 1: Upload your outfit picture", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Your Outfit Look", use_container_width=True)
        
        # Only show the initial analysis button if we haven't processed this image context yet
        if st.session_state.outfit_context is None:
            if st.button("Analyze My Outfit & Suggest Shoes ✨"):
                with st.spinner("Agent analyzing outfit and checking Vector DB..."):
                    
                    # Call Chain 1: Image Analysis
                    raw_analysis = analyze_outfit_image(client, image)
                    
                    # Safety check
                    if "INVALID" in raw_analysis:
                        st.warning("⚠️ The agent thinks this isn't an outfit. Please upload a picture of clothing.")
                        return
                    
                    st.session_state.outfit_context = raw_analysis
                    
                    # Vector DB Retrieval: Match keywords to inventory
                    query_vector = get_embedding(client, raw_analysis)
                    db_results = st.session_state.vector_db.query(
                        query_embeddings=[query_vector],
                        n_results=1
                    )
                    st.session_state.shoe_context = db_results['documents'][0][0]
                    
                    # Call Chain 2: Initial Synthesis Message
                    initial_reply = get_final_chat_response(
                        client, st.session_state.outfit_context, st.session_state.shoe_context
                    )
                    st.session_state.messages.append({"role": "assistant", "content": initial_reply})
                    st.rerun()

        # If context is found, permanently render the chat window independent of button states
        if st.session_state.outfit_context is not None:
            st.write("---")
            st.subheader("💬 Chat with your AI Stylist")
            
            # Render chat logs dynamically from session history
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            # Allow user follow-up questions (Outcome 3: Customer Service Chatbot)
            if user_query := st.chat_input("Ask me anything else about this style..."):
                st.session_state.messages.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.write(user_query)
                    
                with st.spinner("Thinking..."):
                    chat_reply = get_final_chat_response(
                        client, 
                        st.session_state.outfit_context, 
                        st.session_state.shoe_context, 
                        user_message=user_query
                    )
                st.session_state.messages.append({"role": "assistant", "content": chat_reply})
                st.rerun()

if __name__ == "__main__":
    main()