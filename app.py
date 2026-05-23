import os
import warnings

# Silence Warnings
os.environ["ORT_LOGGING_LEVEL"] = "3"
os.environ["ORT_LOGGING_LEVEL_DEFAULT"] = "3"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from google import genai
from google.genai import types

warnings.filterwarnings("ignore", category=RuntimeWarning)

# Load Environment Variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
valid_user = os.getenv("APP_USER", "admin")
valid_pass = os.getenv("APP_PASS", "luxury123")

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.urandom(24) # Secure key for Flask sessions

# Initialize Gemini
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("WARNING: Gemini API Key missing from .env")

# Initialize ChromaDB Vector Database
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
collection.add(
    documents=[s["desc"] for s in sneakers],
    metadatas=[{"name": s["name"], "tags": ",".join(s["tags"])} for s in sneakers],
    ids=[s["id"] for s in sneakers]
)


# --- FLASK ROUTES ---

@app.route('/')
def index():
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
    return redirect(url_for('index'))

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

    # Query Vector Database
    results = collection.query(query_texts=[user_prompt], n_results=1)
    
    if len(results["ids"][0]) > 0:
        best_match_meta = results["metadatas"][0][0]
        best_match_doc = results["documents"][0][0]
        sneaker_name = best_match_meta["name"]
        tags = best_match_meta["tags"].split(",")
        
        # Query Gemini
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
    else:
        return jsonify({
            "text": "I couldn't find an exact match for that aesthetic in our current archives.",
            "html": ""
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)