# Module Real world AI
| Name | Student ID |
|------|------------|
|Parminder Singh|25351400|
|Amanpreet Singh|25346100|
|Abubakar Mahamoud|25293400|

Link to video showcase: https://youtu.be/YjwZLhN0UQw

# Semantic Sneaker Sourcing Tool 👟✨

An AI-driven luxury fashion curation platform that combines a production-ready **Flask** backend, a high-performance **FAISS Vector Database** for local inventory searching, and **Google Gemini 2.5 Flash** for delivering expert-level, human-like fashion styling advice.

---

## 🌟 Features

*   **Secure User Lifecycle**: Complete user onboarding flow with full Sign Up, Account Creation, and Login authentication powered by an automatic **SQLite** database and secure password hashing.
*   **Dual-Database Intelligence Architecture**:
    *   **SQLite**: Handing relational user credentials and session authentication.
    *   **FAISS (Facebook AI Similarity Search)**: Managing high-dimensional vector searches over localized sneaker inventories using state-of-the-art `gemini-embedding-001` embeddings.
*   **Context-Aware AI Stylist**: Powered by **Gemini 2.5 Flash** with advanced prompt engineering. The agent intelligently handles general style advice, filters out gibberish inputs, and dynamically triggers visual product cards only when an inventory item genuinely matches the user's outfit.
*   **Heritage Luxury Interface**: A modern, responsive front-end crafted with glassmorphism UI principles, custom CSS animations, and real-time asynchronous JavaScript communication.

---

## 📂 Project Structure

```text
ai-shoe-recommender/
│
├── static/
│   ├── logo.png             # The brand identity logo asset
│   ├── styles.css           # Global luxury glassmorphic theme styling
│   └── chat.js              # Asynchronous AJAX chat logic & dynamic card rendering
│
├── templates/
│   ├── index.html           # Landing page featuring onboarding paths
│   ├── login.html           # Secure User authentication interface
│   ├── signup.html          # New user registration form (captures 5 parameters)
│   └── chat.html            # Main premium styling conversational interface
│
├── app.py                   # Core Flask server, routing, SQLite initialization, & FAISS/Gemini RAG pipeline
├── requirements.txt         # Project pinned dependencies
└── users.db                 # Automatically generated local SQLite relational database
```
##🚀 Installation & Setup1. Clone & Navigate to ProjectBashcd ai-shoe-recommender

2. Configure Environment VariablesCreate a .env file in the root directory and securely add your keys:PlaintextGEMINI_API_KEY="your_actual_gemini_api_key"

3. Activate Virtual Environment & Install DependenciesBash# Activate your local virtual environment

source .venv/bin/activate

# Install requirements

pip install -r requirements.txt

4. Boot the Full-Stack ServerBashpython app.py

Once executed, navigate to http://127.0.0.1:5000 in your web browser to interact with the system.

## 🛠️ Technology 

 StackLayer Technology

 Framework  Flask (Python)

Vector DBFAISS (Facebook AI Similarity Search)

Relational DBSQLite3LLM & EmbeddingsGoogle Gemini API (gemini-2.5-flash & gemini-embedding-001)

Front-EndSemantic HTML5, Vanilla JavaScript (ES6+), Custom CSS Grid/Flexbox
