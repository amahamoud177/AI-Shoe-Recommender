import os
import warnings
import numpy as np
import faiss
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# Load Environment Variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
valid_user = os.getenv("APP_USER", "admin")
valid_pass = os.getenv("APP_PASS", "luxury123")

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Gemini Client
if not api_key:
    print("WARNING: Gemini API Key missing from .env")
client = genai.Client(api_key=api_key)


# --- FAISS VECTOR DATABASE SETUP ---

# Demo Inventory
sneakers = [
    {"id": "1", "name": "Air Jordan 4 Retro 'Thunder'", "desc": "High-contrast, bold, confident, black and yellow streetwear.", "tags": ["Confident", "High-Contrast"]},
    {"id": "2", "name": "Nike Dunk Low 'Argon'", "desc": "Cool, relaxed, sky blue and white, perfect for styling with dark leather.", "tags": ["Color Match", "Streetwear"]},
    {"id": "3", "name": "Adidas Samba OG", "desc": "Classic, minimalist, white and black leather, old money, understated elegance.", "tags": ["Minimalist", "Heritage"]}
]

# 1. Embed the sneaker descriptions using Gemini
embedding_model = 'text-embedding-001'
documents = [s["desc"] for s in sneakers]

print("Initializing FAISS Vector Database...")
response = client.models.embed_content(
    model=embedding_model,
    contents=documents
)

# 2. Extract vector values and format them for FAISS (numpy float32 array)
embeddings = np.array([emb.values for emb in response.embeddings], dtype=np.float32)
dimension = embeddings.shape[1] 

# 3. Build the FAISS Index
vector_index = faiss.IndexFlatL2(dimension)
vector_index.add(embeddings)

# 4. Create a metadata store to map the vectors back to the sneaker details
metadata_store = {}
for i, s in enumerate(sneakers):
    metadata_store[i] = {
        "name": s["name"],
        "desc": s["desc"],
        "tags": ",".join(s["tags"])
    }
print("Database ready.")


# --- FLASK ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == valid_user and password == valid_pass:
            session['authenticated'] = True
            session['username'] = username
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Invalid credentials. Access denied.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/chat')
def chat():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('chat.html', username=session.get('username'))

@app.route('/api/message', methods=['POST'])
def api_message():
    """Handles the async AJAX requests from the chat interface."""
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    user_prompt = data.get('message', '')
    
    if not user_prompt:
        return jsonify({"error": "Empty message"}), 400

    try:
        # 1. Embed the user's search query
        query_resp = client.models.embed_content(
            model=embedding_model,
            contents=user_prompt
        )
        query_emb = np.array([query_resp.embeddings[0].values], dtype=np.float32)
        
        # 2. Search the FAISS Vector Database for the closest match
        distances, indices = vector_index.search(query_emb, 1)
        best_idx = indices[0][0]
        best_match = metadata_store[best_idx]
        
        sneaker_name = best_match["name"]
        best_match_doc = best_match["desc"]
        tags = best_match["tags"].split(",")
        
        # 3. Generate the Stylist Response with Gemini 2.5 Flash
        sys_instr = "You are a high-end fashion stylist. Briefly explain why this specific sneaker matches the user's mood. Keep it under 3 sentences. Be elegant and confident."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"User's mood: {user_prompt}\nSneaker chosen: {sneaker_name}\nSneaker profile: {best_match_doc}",
            config=types.GenerateContentConfig(system_instruction=sys_instr)
        )
        
        ai_text = response.text
        tags_html = "".join([f"<span class='tag'>{tag}</span>" for tag in tags])
        card_html = f"""
        <div class="sneaker-card">
            <div class="sneaker-name">{sneaker_name}</div>
            <div class="match-tags">{tags_html}</div>
        </div>
        """
        
        return jsonify({
            "text": ai_text,
            "html": card_html
        }) 
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)