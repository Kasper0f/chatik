from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, send
import sqlite3
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Путь к базе данных
DB_FILE = "chat.db"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Хэширование пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Проверка пароля
def verify_password(stored_password_hash, provided_password):
    return stored_password_hash == hash_password(provided_password)

# Главная страница (перенаправление на вход)
@app.route("/")
def index():
    return redirect(url_for("login"))

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "<h1>Пожалуйста, заполните все поля.</h1>", 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "<h1>Пользователь с таким именем уже существует.</h1>", 400

        password_hash = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Регистрация</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .form-container {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                width: 300px;
                text-align: center;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                width: 100%;
                padding: 10px;
                background-color: #673ab7;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #512da8;
            }
            .link {
                display: block;
                margin-top: 15px;
                color: #673ab7;
                text-decoration: none;
                font-size: 14px;
            }
            .link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1>Регистрация</h1>
            <form method="POST">
                <input type="text" id="username" name="username" placeholder="Имя пользователя" required><br>
                <input type="password" id="password" name="password" placeholder="Пароль" required><br>
                <button type="submit">Зарегистрироваться</button>
            </form>
            <a href="/login" class="link">Уже есть аккаунт? Войти</a>
        </div>
    </body>
    </html>
    """

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "<h1>Пожалуйста, заполните все поля.</h1>", 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and verify_password(user[0], password):
            session['username'] = username
            conn.close()
            return redirect(url_for('chat'))
        else:
            conn.close()
            return "<h1 style='color: red; text-align: center;'>Неверное имя пользователя или пароль.</h1>" + login_page()

    return login_page()

def login_page():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .form-container {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                width: 300px;
                text-align: center;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                width: 100%;
                padding: 10px;
                background-color: #673ab7;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #512da8;
            }
            .link {
                display: block;
                margin-top: 15px;
                color: #673ab7;
                text-decoration: none;
                font-size: 14px;
            }
            .link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1>Вход</h1>
            <form method="POST">
                <input type="text" id="username" name="username" placeholder="Имя пользователя" required><br>
                <input type="password" id="password" name="password" placeholder="Пароль" required><br>
                <button type="submit">Войти</button>
            </form>
            <a href="/register" class="link">Нет аккаунта? Зарегистрироваться</a>
        </div>
    </body>
    </html>
    """

# Чат
@app.route("/chat")
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template_string(CHAT_TEMPLATE)

# Удаление старых сообщений
def delete_old_messages():
    three_days_ago = datetime.now() - timedelta(days=3)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE timestamp < ?", (three_days_ago,))
    conn.commit()
    conn.close()

# Получение всех сообщений из базы данных
def get_messages():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, message, timestamp FROM messages ORDER BY timestamp ASC")
    messages = cursor.fetchall()
    conn.close()
    return messages

# Сохранение нового сообщения в базу данных
def save_message(username, message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)",
                   (username, message, datetime.now()))
    conn.commit()
    conn.close()

# HTML-шаблон для чата
CHAT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чат</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #121212;
            color: white;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            height: 100vh;
        }
        h1 {
            color: #673ab7;
        }
        #chat-box {
            width: 100%;
            max-width: 600px;
            height: 400px;
            border: 1px solid #444;
            overflow-y: scroll;
            background-color: #1e1e1e;
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        #message-input {
            width: 80%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            margin-right: 10px;
        }
        button {
            padding: 10px 20px;
            border: none;
            background-color: #673ab7;
            color: white;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #512da8;
        }
        .message {
            margin: 5px 0;
        }
        .username {
            color: #2196f3;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Простой чат</h1>
    <div id="chat-box"></div>
    <input id="message-input" type="text" placeholder="Введите сообщение...">
    <button onclick="sendMessage()">Отправить</button>

    <script>
        var socket = io.connect('http://' + document.domain + ':' + location.port);
        var chatBox = document.getElementById('chat-box');
        var username = "{{ session['username'] }}";

        socket.on('message', function(data) {
            var newMessage = document.createElement('div');
            newMessage.className = "message";
            newMessage.innerHTML = `<span class="username">${data.username}:</span> ${data.message}`;
            chatBox.appendChild(newMessage);
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        function sendMessage() {
            var messageInput = document.getElementById('message-input');
            var message = messageInput.value;
            if (message.trim() !== '') {
                socket.emit('send_message', { message: message, username: username });
                messageInput.value = '';
            }
        }

        window.onload = function() {
            fetch('/load_messages')
                .then(response => response.json())
                .then(data => {
                    const messages = data.messages || [];
                    messages.forEach(msg => {
                        var newMessage = document.createElement('div');
                        newMessage.className = "message";
                        newMessage.innerHTML = `<span class="username">${msg.username}:</span> ${msg.message}`;
                        chatBox.appendChild(newMessage);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                })
                .catch(error => {
                    console.error("Ошибка при загрузке сообщений:", error);
                });
        }
    </script>
</body>
</html>
"""

@socketio.on('send_message')
def handle_message(data):
    save_message(data['username'], data['message'])
    send({'username': data['username'], 'message': data['message']}, broadcast=True)

@app.route('/load_messages')
def load_messages():
    messages = get_messages()
    return jsonify({'messages': [{'username': msg[0], 'message': msg[1]} for msg in messages]})

if __name__ == "__main__":
    init_db()
    delete_old_messages()
    socketio.run(app, host='0.0.0.0', port=80, debug=True)