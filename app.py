import os
from flask import Flask, render_template_string, request, redirect
import sqlite3
import google.generativeai as genai

app = Flask(__name__)

# --- Setup Gemini ---
# We will set the API Key in the Render Dashboard later for security
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, content TEXT)''')
    conn.commit()
    conn.close()

# --- HTML Design ---
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Secret Message</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: white; display: flex; justify-content: center; padding: 40px; }
        .card { background: #1e1e1e; padding: 25px; border-radius: 12px; width: 100%; max-width: 450px; border: 1px solid #333; }
        input, textarea { width: 100%; margin: 10px 0; padding: 12px; background: #2d2d2d; border: 1px solid #444; color: white; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #3d5afe; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .msg-list { margin-top: 20px; border-top: 1px solid #333; padding-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 Ask Gemini & Save</h2>
        <form method="POST" action="/ask">
            <input type="text" name="subject" placeholder="Topic (e.g., Coding Help)" required>
            <textarea name="prompt" placeholder="Ask Gemini something..." required></textarea>
            <button type="submit">Ask AI & Save to DB</button>
        </form>

        <div class="msg-list">
            <h3>Saved Responses</h3>
            {% for m in msgs %}
                <p><strong>{{ m[1] }}:</strong> {{ m[2][:100] }}...</p>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 5")
    msgs = c.fetchall()
    conn.close()
    return render_template_string(HTML, msgs=msgs)

@app.route('/ask', methods=['POST'])
def ask():
    subject = request.form['subject']
    prompt = request.form['prompt']
    
    # Get response from Gemini
    response = model.generate_content(prompt)
    
    # Save to SQLite
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (subject, content) VALUES (?, ?)", (subject, response.text))
    conn.commit()
    conn.close()
    
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)