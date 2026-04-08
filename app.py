import os
import base64
import sqlite3
from flask import Flask, render_template_string, request, send_file, flash, redirect
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Encryption Logic ---
def get_key(password: str):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32,
        salt=b'static_salt_secure', iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

# --- Database ---
def init_db():
    conn = sqlite3.connect('/tmp/vault.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id TEXT PRIMARY KEY, encrypted_body TEXT, filename TEXT, encrypted_file BLOB)''')
    conn.commit()
    conn.close()

# --- Modern UI ---
HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vault v2.0 | Secure A-to-B</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f1f5f9; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); display: flex; justify-content: center; padding: 40px; }
        .container { background: var(--card); padding: 2rem; border-radius: 16px; width: 100%; max-width: 500px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid #334155; }
        h1 { font-size: 1.5rem; text-align: center; color: var(--accent); margin-bottom: 1.5rem; }
        input, textarea { width: 100%; padding: 12px; margin: 8px 0; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: var(--accent); border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { opacity: 0.9; transform: translateY(-1px); }
        .tab-btn { background: #334155; margin-bottom: 20px; }
        .result-box { margin-top: 20px; padding: 15px; background: #0f172a; border-radius: 8px; border-left: 4px solid var(--accent); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Vault v2.0</h1>
        
        <form method="POST" action="/send" enctype="multipart/form-data">
            <input type="text" name="subject" placeholder="Subject (Will be your ID)" required>
            <textarea name="message" placeholder="Type secret message..." required></textarea>
            <div style="font-size: 0.8rem; margin: 5px 0;">📎 Attach Secret File:</div>
            <input type="file" name="file">
            <input type="password" name="password" placeholder="Encryption Password" required>
            <button type="submit">Encrypt & Send</button>
        </form>

        <hr style="border: 0; border-top: 1px solid #334155; margin: 2rem 0;">

        <form method="POST" action="/read">
            <input type="text" name="msg_id" placeholder="Enter Subject/ID" required>
            <input type="password" name="password" placeholder="Enter Password" required>
            <button type="submit" class="tab-btn">Unlock & Download</button>
        </form>

        {% if data %}
            <div class="result-box">
                <strong>Message:</strong><p>{{ data.msg }}</p>
                {% if data.file %}
                <form action="/download" method="POST">
                    <input type="hidden" name="msg_id" value="{{ data.id }}">
                    <input type="hidden" name="password" value="{{ data.pw }}">
                    <button type="submit" style="background: #10b981;">⬇️ Download Decrypted File</button>
                </form>
                {% endif %}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/send', methods=['POST'])
def send():
    subject = secure_filename(request.form['subject'])
    msg = request.form['message']
    pw = request.form['password']
    file = request.files.get('file')
    
    fernet = Fernet(get_key(pw))
    enc_msg = fernet.encrypt(msg.encode()).decode()
    
    enc_file_data = None
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        enc_file_data = fernet.encrypt(file.read())

    conn = sqlite3.connect('/tmp/vault.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?, ?)", (subject, enc_msg, filename, enc_file_data))
    conn.commit()
    conn.close()
    return f"Success! Tell Person B to search for Subject: <b>{subject}</b> <a href='/'>Back</a>"

@app.route('/read', methods=['POST'])
def read():
    msg_id = request.form['msg_id']
    pw = request.form['password']
    
    conn = sqlite3.connect('/tmp/vault.db')
    c = conn.cursor()
    c.execute("SELECT encrypted_body, filename FROM messages WHERE id=?", (msg_id,))
    row = c.fetchone()
    conn.close()

    if row:
        try:
            fernet = Fernet(get_key(pw))
            dec_msg = fernet.decrypt(row[0].encode()).decode()
            return render_template_string(HTML, data={'msg': dec_msg, 'file': row[1], 'id': msg_id, 'pw': pw})
        except:
            return "❌ Decryption failed. Wrong password."
    return "❌ ID not found."

@app.route('/download', methods=['POST'])
def download():
    msg_id = request.form['msg_id']
    pw = request.form['password']
    
    conn = sqlite3.connect('/tmp/vault.db')
    c = conn.cursor()
    c.execute("SELECT filename, encrypted_file FROM messages WHERE id=?", (msg_id,))
    row = c.fetchone()
    conn.close()

    if row and row[1]:
        fernet = Fernet(get_key(pw))
        dec_file = fernet.decrypt(row[1])
        return send_file(io.BytesIO(dec_file), download_name=row[0], as_attachment=True)
    return "File not found."

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
