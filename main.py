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
            /* Стили для формы */
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
            /* Стили для формы */
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

    return render_template_string(CHAT_TEMPLATE, username=session['username'], is_admin=session['username'] == "Kasper")

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
    cursor.execute("SELECT id, username, message, timestamp FROM messages ORDER BY timestamp ASC")
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

# Обновление сообщения в базе данных
def update_message(message_id, new_message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET message = ? WHERE id = ?", (new_message, message_id))
    conn.commit()
    conn.close()

# Удаление сообщения по ID
def delete_message(message_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

# Обновление имени пользователя в базе данных
def update_username(old_username, new_username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, old_username))
        cursor.execute("UPDATE messages SET username = ? WHERE username = ?", (new_username, old_username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении имени: {e}")
        return False
    finally:
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
            display: flex;
            align-items: center;
        }
        .username {
            color: #2196f3;
            font-weight: bold;
            margin-right: 10px;
        }
        .delete-button, .edit-button {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            margin-left: 10px;
        }
        .edit-button {
            background-color: #3498db;
        }
        .delete-button:hover, .edit-button:hover {
            opacity: 0.8;
        }
        .message-actions {
            display: none;
            margin-left: auto;
        }
        .message:hover .message-actions {
            display: flex;
        }
        /* Модальное окно профиля */
        .modal {
            display: none;
            position: fixed;
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 20px;
            border-radius: 10px;
            width: 300px;
            text-align: center;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }
        .close:hover, .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Простой чат</h1>
    <button id="profile-button">Профиль</button>
    <div id="chat-box"></div>
    <input id="message-input" type="text" placeholder="Введите сообщение...">
    <button onclick="sendMessage()">Отправить</button>

    <!-- Модальное окно профиля -->
    <div id="profile-modal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>Настройки профиля</h2>
            <form id="update-username-form">
                <label for="new-username">Новое имя:</label><br>
                <input type="text" id="new-username" name="new-username" required><br><br>
                <button type="submit">Обновить имя</button>
            </form>
        </div>
    </div>

    <script>
        var socket = io.connect('http://' + document.domain + ':' + location.port);
        var chatBox = document.getElementById('chat-box');
        var username = "{{ username }}";
        var isAdmin = {{ is_admin | tojson }};

        // При получении нового сообщения от сервера
        socket.on('message', function(data) {
            addMessage(data.id, data.username, data.message, username, isAdmin);
        });

        // Функция для отправки сообщения
        function sendMessage() {
            var messageInput = document.getElementById('message-input');
            var message = messageInput.value;
            if (message.trim() !== '') {
                socket.emit('send_message', { message: message, username: username });
                messageInput.value = '';
            }
        }

        // Добавление сообщения в чат
        function addMessage(id, username, message, current_username, isAdmin) {
            var newMessage = document.createElement('div');
            newMessage.className = "message";
            newMessage.dataset.id = id;

            var messageContent = document.createElement('span');
            messageContent.innerHTML = `<span class="username">${username}:</span> ${message}`;
            newMessage.appendChild(messageContent);

            var actionsDiv = document.createElement('div');
            actionsDiv.className = "message-actions";

            // Кнопка "Изменить" доступна только автору сообщения
            if (username === current_username) {
                var editButton = document.createElement('button');
                editButton.className = "edit-button";
                editButton.textContent = "Изменить";
                editButton.onclick = function() {
                    var newMessageText = prompt("Введите новое сообщение:", message);
                    if (newMessageText && newMessageText.trim() !== '') {
                        fetch(`/update_message/${id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: newMessageText })
                        }).then(response => response.json())
                          .then(data => {
                              if (data.success) {
                                  messageContent.textContent = `${username}: ${newMessageText}`;
                              }
                          });
                    }
                };
                actionsDiv.appendChild(editButton);
            }

            // Кнопка "Удалить" доступна автору сообщения или администратору
            if (username === current_username || isAdmin) {
                var deleteButton = document.createElement('button');
                deleteButton.className = "delete-button";
                deleteButton.textContent = "Удалить";
                deleteButton.onclick = function() {
                    fetch(`/delete_message/${id}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                newMessage.remove();
                            }
                        });
                };
                actionsDiv.appendChild(deleteButton);
            }

            newMessage.appendChild(actionsDiv);
            chatBox.appendChild(newMessage);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        // Загрузка сообщений при загрузке страницы
        window.onload = function() {
            fetch('/load_messages')
                .then(response => response.json())
                .then(data => {
                    const messages = data.messages || [];
                    messages.forEach(msg => {
                        addMessage(msg.id, msg.username, msg.message, username, isAdmin);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                })
                .catch(error => {
                    console.error("Ошибка при загрузке сообщений:", error);
                });

            // Открытие модального окна профиля
            var modal = document.getElementById('profile-modal');
            var profileButton = document.getElementById('profile-button');
            var span = document.getElementsByClassName('close')[0];

            profileButton.onclick = function() {
                modal.style.display = "block";
            };

            span.onclick = function() {
                modal.style.display = "none";
            };

            window.onclick = function(event) {
                if (event.target == modal) {
                    modal.style.display = "none";
                }
            };

            // Обновление имени пользователя
            document.getElementById('update-username-form').addEventListener('submit', function(event) {
                event.preventDefault();
                var newUsername = document.getElementById('new-username').value.trim();
                if (newUsername === '') {
                    alert("Имя не может быть пустым.");
                    return;
                }

                fetch('/update_username', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_username: newUsername })
                }).then(response => response.json())
                  .then(data => {
                      if (data.success) {
                          username = newUsername; // Обновляем имя в клиентской части
                          modal.style.display = "none"; // Закрываем модальное окно
                          alert("Имя успешно изменено!");
                      } else {
                          alert(data.message);
                      }
                  });
            });
        }
    </script>
</body>
</html>
"""

@socketio.on('send_message')
def handle_message(data):
    save_message(data['username'], data['message'])
    send({'id': get_last_message_id(), 'username': data['username'], 'message': data['message'], 'current_username': data['username']}, broadcast=True)

def get_last_message_id():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT last_insert_rowid()")
    message_id = cursor.fetchone()[0]
    conn.close()
    return message_id

@app.route('/load_messages')
def load_messages():
    messages = get_messages()
    return jsonify({'messages': [{'id': msg[0], 'username': msg[1], 'message': msg[2]} for msg in messages]})

@app.route('/delete_message/<int:message_id>', methods=['DELETE'])
def delete_message_route(message_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': "Вы не авторизованы."}), 401

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM messages WHERE id = ?", (message_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'success': False, 'message': "Сообщение не найдено."}), 404

    message_author = result[0]

    # Администратор может удалять любые сообщения
    if message_author != session['username'] and session['username'] != "Kasper":
        conn.close()
        return jsonify({'success': False, 'message': "Вы не являетесь автором этого сообщения."}), 403

    delete_message(message_id)
    conn.close()
    return jsonify({'success': True, 'message': "Сообщение успешно удалено."})

@app.route('/update_message/<int:message_id>', methods=['PUT'])
def update_message_route(message_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': "Вы не авторизованы."}), 401

    data = request.json
    new_message = data.get('message')

    if not new_message or new_message.strip() == '':
        return jsonify({'success': False, 'message': "Новое сообщение не может быть пустым."}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM messages WHERE id = ?", (message_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'success': False, 'message': "Сообщение не найдено."}), 404

    message_author = result[0]

    # Только автор сообщения может его редактировать
    if message_author != session['username']:
        conn.close()
        return jsonify({'success': False, 'message': "Вы не являетесь автором этого сообщения."}), 403

    update_message(message_id, new_message)
    conn.close()
    return jsonify({'success': True, 'message': "Сообщение успешно обновлено."})

@app.route('/update_username', methods=['POST'])
def update_username():
    if 'username' not in session:
        return jsonify({'success': False, 'message': "Вы не авторизованы."}), 401

    data = request.json
    new_username = data.get('new_username')

    if not new_username or new_username.strip() == '':
        return jsonify({'success': False, 'message': "Новое имя не может быть пустым."}), 400

    old_username = session['username']

    # Проверяем, что новое имя не занято
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (new_username,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return jsonify({'success': False, 'message': "Имя уже занято."}), 400

    # Обновляем имя в базе данных
    success = update_username(old_username, new_username)
    if success:
        session['username'] = new_username  # Обновляем имя в сессии
        return jsonify({'success': True, 'message': "Имя успешно обновлено."})
    else:
        return jsonify({'success': False, 'message': "Не удалось обновить имя."}), 500

if __name__ == "__main__":
    init_db()
    delete_old_messages()
    socketio.run(app, host='0.0.0.0', port=80, debug=True)