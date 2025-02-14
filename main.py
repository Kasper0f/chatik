from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, send
import sqlite3
from datetime import datetime
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
    # Создание таблицы messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')
    # Создание таблицы users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            blocked INTEGER DEFAULT 0
        )
    ''')

    # Проверка наличия столбца blocked в таблице users
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'blocked' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0")

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
        <link rel="stylesheet" href="/static/styles.css">
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
        cursor.execute("SELECT password_hash, blocked FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and verify_password(user[0], password):
            if user[1]:  # Проверяем, заблокирован ли пользователь
                conn.close()
                return "<h1 style='color: red;'>Ваш аккаунт заблокирован.</h1>"
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
        <link rel="stylesheet" href="/static/styles.css">
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
    message_id = cursor.lastrowid  # Получаем ID только что добавленного сообщения
    conn.close()
    return message_id

# Обновление сообщения в базе данных
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

    cursor.execute("UPDATE messages SET message = ? WHERE id = ?", (new_message, message_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': "Сообщение успешно обновлено."})

# Удаление сообщения по ID
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

    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': "Сообщение успешно удалено."})

# Панель администратора
@app.route("/admin")
def admin_panel():
    if 'username' not in session or session['username'] != "Kasper":
        return "<h1 style='color: red;'>Доступ запрещен.</h1>", 403

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, blocked FROM users ORDER BY id ASC")
    users = cursor.fetchall()
    conn.close()

    return render_template_string(ADMIN_PANEL_TEMPLATE, users=users)

# Блокировка/разблокировка пользователя
@app.route('/admin/toggle_block/<int:user_id>', methods=['POST'])
def toggle_block_user(user_id):
    if 'username' not in session or session['username'] != "Kasper":
        return jsonify({'success': False, 'message': "Доступ запрещен."}), 403

    data = request.json
    action = data.get('action')

    if action not in ['block', 'unblock']:
        return jsonify({'success': False, 'message': "Неверное действие."}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET blocked = ? WHERE id = ?", (1 if action == 'block' else 0, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f"Пользователь успешно {'заблокирован' if action == 'block' else 'разблокирован'}."})

# WebSocket: Обработка отправки сообщений
@socketio.on('send_message')
def handle_message(data):
    username = data.get('username')
    message = data.get('message')

    if not username or not message:
        print("Получено пустое сообщение.")  # Логирование
        return

    print(f"Получено сообщение от {username}: {message}")  # Логирование
    message_id = save_message(username, message)
    send({'id': message_id, 'username': username, 'message': message}, broadcast=True)

# Загрузка сообщений
@app.route('/load_messages')
def load_messages():
    messages = get_messages()
    print(f"Загружено сообщений: {len(messages)}")  # Логирование
    return jsonify({'messages': [{'id': msg[0], 'username': msg[1], 'message': msg[2]} for msg in messages]})

# HTML-шаблон для чата
CHAT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Чат</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div id="chat-container">
        <h1>Простой чат</h1>
        {% if is_admin %}
            <a href="/admin" class="admin-button">Панель администратора</a>
        {% endif %}
        <div id="chat-box"></div>
        <input id="message-input" type="text" placeholder="Введите сообщение...">
        <button onclick="sendMessage()">Отправить</button>
    </div>

    <script>
        var socket = io.connect('http://' + document.domain + ':' + location.port);
        var chatBox = document.getElementById('chat-box');
        var username = "{{ username }}";
        var isAdmin = {{ is_admin | tojson }};

        // При получении нового сообщения от сервера
        socket.on('message', function(data) {
            console.log("Получено новое сообщение:", data);  // Логирование
            addMessage(data.id, data.username, data.message, username, isAdmin);
        });

        // Отправка сообщения
        function sendMessage() {
            var messageInput = document.getElementById('message-input');
            var message = messageInput.value.trim();

            if (message === '') {
                alert("Сообщение не может быть пустым.");
                return;
            }

            console.log("Отправка сообщения:", { message: message, username: username });  // Логирование
            socket.emit('send_message', { message: message, username: username });
            messageInput.value = ''; // Очищаем поле ввода
        }

        // Добавление сообщения в чат
        function addMessage(id, msgUsername, message, current_username, isAdmin) {
            var newMessage = document.createElement('div');
            newMessage.className = "message";
            newMessage.dataset.id = id;

            var messageContent = document.createElement('span');
            messageContent.innerHTML = `<span class="username">${msgUsername}:</span> ${message}`;
            newMessage.appendChild(messageContent);

            var actionsDiv = document.createElement('div');
            actionsDiv.className = "message-actions";

            // Кнопка "Изменить" доступна автору сообщения
            if (msgUsername === current_username) {
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
                                  messageContent.textContent = `${msgUsername}: ${newMessageText}`;
                              } else {
                                  alert(data.message);
                              }
                          });
                    }
                };
                actionsDiv.appendChild(editButton);
            }

            // Кнопка "Удалить" доступна автору сообщения или администратору
            if (msgUsername === current_username || isAdmin) {
                var deleteButton = document.createElement('button');
                deleteButton.className = "delete-button";
                deleteButton.textContent = "Удалить";
                deleteButton.onclick = function() {
                    fetch(`/delete_message/${id}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                newMessage.remove();
                            } else {
                                alert(data.message);
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
                    console.log("Загружены сообщения:", data);  // Логирование
                    const messages = data.messages || [];
                    messages.forEach(msg => {
                        addMessage(msg.id, msg.username, msg.message, username, isAdmin);
                    });
                    chatBox.scrollTop = chatBox.scrollHeight;
                })
                .catch(error => {
                    console.error("Ошибка при загрузке сообщений:", error);
                });
        };
    </script>
</body>
</html>
"""

# HTML-шаблон для панели администратора
ADMIN_PANEL_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель администратора</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div id="admin-container">
        <h1>Панель администратора</h1>
        <h2>Список пользователей</h2>
        <ul>
            {% for user in users %}
                <li>
                    {{ user[1] }} ({{ "Заблокирован" if user[2] else "Активен" }})
                    <button onclick="toggleBlockUser({{ user[0] }}, {{ user[2] }})">
                        {{ "Разблокировать" if user[2] else "Заблокировать" }}
                    </button>
                </li>
            {% endfor %}
        </ul>
        <a href="/chat">Вернуться в чат</a>
    </div>

    <script>
        // Функция для блокировки/разблокировки пользователя
        function toggleBlockUser(userId, isBlocked) {
            const action = isBlocked ? "unblock" : "block";
            fetch(`/admin/toggle_block/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      alert(`Пользователь ${action === "block" ? "заблокирован" : "разблокирован"}.`);
                      location.reload(); // Обновляем страницу
                  } else {
                      alert(data.message);
                  }
              });
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    init_db()
    socketio.run(app, host='0.0.0.0', port=80, debug=True)