import os
import warnings
import sqlite3
import numpy as np
import faiss
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
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


# --- SQLITE DATABASE SETUP (User Registration) ---
def init_db():
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      email TEXT UNIQUE NOT NULL,
                      username TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL)''')
        conn.commit()

init_db()


# --- FAISS VECTOR DATABASE SETUP (Shoe Inventory) ---
sneakers = [
    {"id": "1", "name": "Air Jordan 4 Retro 'Thunder'", "desc": "High-contrast, bold, confident, black and yellow streetwear.", "tags": ["Confident", "High-Contrast"]},
    {"id": "2", "name": "Nike Dunk Low 'Argon'", "desc": "Cool, relaxed, sky blue and white, perfect for styling with dark leather.", "tags": ["Color Match", "Streetwear"]},
    {"id": "3", "name": "Adidas Samba OG", "desc": "Classic, minimalist, white and black leather, old money, understated elegance.", "tags": ["Minimalist", "Heritage"]}
]

embedding_model = 'gemini-embedding-001'
documents = [s["desc"] for s in sneakers]

print("Initializing FAISS Vector Database...")
response = client.models.embed_content(model=embedding_model, contents=documents)
embeddings = np.array([emb.values for emb in response.embeddings], dtype=np.float32)
dimension = embeddings.shape[1] 

vector_index = faiss.IndexFlatL2(dimension)
vector_index.add(embeddings)

metadata_store = {}
for i, s in enumerate(sneakers):
    metadata_store[i] = {"name": s["name"], "desc": s["desc"], "tags": ",".join(s["tags"])}
print("Database ready.")


# --- FLASK ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            return render_template('signup.html', error="Passwords do not match.")

        hashed_pw = generate_password_hash(password)

        try:
            with sqlite3.connect('users.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (name, email, username, password) VALUES (?, ?, ?, ?)",
                          (name, email, username, hashed_pw))
                conn.commit()
            return redirect(url_for('login', msg="Account created! You may now log in."))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error="Username or Email already exists.")

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = request.args.get('msg')
    if request.method == 'POST':
        login_id = request.form.get('login_id') 
        password = request.form.get('password')
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id))
            user = c.fetchone()
            
        if user and check_password_hash(user[4], password):
            session['authenticated'] = True
            session['username'] = user[3]
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Invalid credentials. Access denied.")
            
    return render_template('login.html', message=message)

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
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    user_prompt = data.get('message', '')
    
    if not user_prompt:
        return jsonify({"error": "Empty message"}), 400

    try:
        # 1. FAISS Vector Search 
        query_resp = client.models.embed_content(model=embedding_model, contents=user_prompt)
        query_emb = np.array([query_resp.embeddings[0].values], dtype=np.float32)
        
        distances, indices = vector_index.search(query_emb, 1)
        best_match = metadata_store[indices[0][0]]
        
        sneaker_name = best_match["name"]
        best_match_doc = best_match["desc"]
        tags = best_match["tags"].split(",")
        
        # 2. Advanced Prompt Engineering
        sys_instr = f"""You are a luxury, high-end AI fashion stylist. 
        The user will ask for outfit advice. Provide a comprehensive, structured response breaking down different styling vibes (e.g., Formal, Modern, Smart-Casual) just like an expert stylist would.
        
        You also have access to our specific boutique inventory item:
        - Name: {sneaker_name}
        - Style Profile: {best_match_doc}
        
        CRITICAL RULES:
        1. If the user's input is gibberish, random letters (like "ll", "asdf"), or completely off-topic, politely ask them to describe their outfit or mood, and DO NOT mention or recommend any shoes.
        2. Give a complete, detailed fashion breakdown for their outfit first (suggesting classic footwear types like Oxfords, Loafers, or Boots where appropriate).
        3. Look at our boutique inventory item. If it fits naturally into one of your style categories (like a Smart-Casual sneaker vibe), seamlessly mention it as an excellent choice from our collection! 
        4. If you explicitly recommend this specific boutique sneaker name anywhere in your text, you MUST append the exact text '[SHOW_CARD]' at the very end of your entire response. Otherwise, do not add the tag."""
        
        prompt = f"User Input: {user_prompt}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=sys_instr)
        )
        
        # Define the variables cleanly so they are never unbound
        ai_text = response.text
        card_html = ""
        
        # 3. Check if Gemini explicitly triggered the product display card
        if "[SHOW_CARD]" in ai_text:
            ai_text = ai_text.replace("[SHOW_CARD]", "").strip()
            tags_html = "".join([f"<span class='tag'>{tag}</span>" for tag in tags])
            card_html = f"""
            <div class="sneaker-card">
                <div style="font-size: 0.8rem; color: var(--accent-gold); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">From Our Collection</div>
                <div class="sneaker-name">{sneaker_name}</div>
                <div class="match-tags">{tags_html}</div>
            </div>
            """
        
        return jsonify({"text": ai_text, "html": card_html})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)