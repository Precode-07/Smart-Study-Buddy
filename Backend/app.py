from flask import Flask, request, jsonify, render_template
from flask import Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import sqlite3
import random

app = Flask(__name__)
CORS(app)
DATABASE = "database.db"

# ----------------- DATABASE CONNECTION -----------------
def get_conn():
    return sqlite3.connect(DATABASE, timeout=10)

# ----------------- INITIALIZE DATABASE -----------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

#------------------Extract Question --------------------
def extract_correct_option(sentence):
    """
    Extracts the main “correct answer” from a sentence.
    Rules:
    - Remove leading '-' and whitespace
    - If ':' exists, take the part before it
    - If '-' exists inside, take the part before it
    - Otherwise, take first 3 words
    """
    sentence = sentence.strip()
    if sentence.startswith('-'):
        sentence = sentence[1:].strip()
    if ':' in sentence:
        return sentence.split(':')[0].strip()
    elif '-' in sentence:
        return sentence.split('-')[0].strip()
    else:
        return ' '.join(sentence.split()[:3])

# ----------------- FRONTEND ROUTES -----------------
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup_page')
def signup_page():
    return render_template('signup.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

# ----------------- SIGNUP -----------------
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    hashed = generate_password_hash(password)
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username, password) VALUES(?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        return jsonify({"message": "Signup successful"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

# ----------------- LOGIN -----------------
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if row and check_password_hash(row[1], password):
        return jsonify({"message": "Login successful", "user_id": row[0], "username": username})
    return jsonify({"error": "Invalid username or password"}), 401

# ----------------- UPLOAD NOTE -----------------
@app.route('/upload_note', methods=['POST'])
def upload_note():
    data = request.json
    user_id = data.get('user_id')
    title = data.get('title')
    content = data.get('content')

    if not user_id or not title or not content:
        return jsonify({'error': 'All fields required'}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO notes(user_id, title, content) VALUES(?, ?, ?)",
                (user_id, title, content))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Note uploaded successfully'})

# ----------------- GET USER NOTES -----------------
@app.route('/get_user_notes', methods=['POST'])
def get_user_notes():
    user_id = request.json.get('user_id')
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM notes WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()

    notes = [{'id': r[0], 'title': r[1], 'content': r[2]} for r in rows]
    return jsonify(notes)

# ----------------- GENERATE NORMAL QUESTIONS (PLAIN TEXT) -----------------
@app.route('/generate_normal', methods=['POST'])
def generate_normal():
    note_id = request.json.get("note_id")
    
    if not note_id:
        return jsonify({"error": "note_id is required"}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT content, title FROM notes WHERE id=?", (note_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Note not found"}), 404

    content, title = row
    sentences = [s.strip() for s in content.split('.') if s.strip()]

    plain_text = f"Note: {title}\n\n"
    for i, s in enumerate(sentences[:5], start=1):
        # Clean sentence: remove leading '-' or extra whitespace
        question_text = s.strip()
        if question_text.startswith('-'):
            question_text = question_text[1:].strip()

        plain_text += f"Q{i}: {question_text}\n"

    # Return inside JSON so frontend can use res.json()
    return jsonify({"questions": plain_text})

# ----------------- GENERATE MCQs (PLAIN TEXT) -----------------
@app.route('/generate_mcq', methods=['POST'])
def generate_mcq():
    data = request.get_json(force=True, silent=True)
    if not data or 'note_id' not in data:
        return jsonify({"error": "note_id required"}), 400

    note_id = data['note_id']

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT content, title FROM notes WHERE id=?", (note_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Note not found"}), 404

    content, title = row
    sentences = [s.strip().lstrip('-').strip() for s in content.split('.') if s.strip()]
    letters = ['a','b','c','d']

    mcqs = []

    for s in sentences[:5]:  # Take first 5 sentences
        # 1️⃣ Extract correct option: Take main subject or term
        if ':' in s:
            correct = s.split(':')[0].strip()
        else:
            correct = s.split()[0]  # fallback first word

        # 2️⃣ Generate logical distractors
        # Idea: take other key terms from the note or sentence
        words = [w.strip(",.") for w in s.split() if w.lower() != correct.lower() and len(w) > 2]
        distractors = random.sample(words, min(3, len(words))) if words else [f"Option {i}" for i in range(1,4)]

        # 3️⃣ Ensure 4 options total
        options = [correct] + distractors
        while len(options) < 4:
            options.append(f"Option {len(options)}")  # fill if not enough distractors

        random.shuffle(options)
        option_dict = {letters[i]: options[i] for i in range(4)}
        correct_letter = letters[options.index(correct)]

        mcqs.append({
            "question": s,
            "options": option_dict,
            "answer": correct_letter
        })

    return jsonify({"note_title": title, "mcq_questions": mcqs})

# ----------------- RUN APP -----------------
if __name__ == "__main__":
    app.run(debug=True)
