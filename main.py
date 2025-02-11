from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

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
        var username = "{{ session['username'] }}"; // Получаем имя пользователя из сессии

        // При получении нового сообщения от сервера
        socket.on('message', function(data) {
            var newMessage = document.createElement('div');
            newMessage.className = "message";
            newMessage.innerHTML = `<span class="username">${data.username}:</span> ${data.message}`;
            chatBox.appendChild(newMessage);
            chatBox.scrollTop = chatBox.scrollHeight; // Прокрутка вниз
        });

        // Функция для отправки сообщения
        function sendMessage() {
            var messageInput = document.getElementById('message-input');
            var message = messageInput.value;
            if (message.trim() !== '') {
                socket.emit('send_message', { message: message, username: username }); // Отправляем сообщение на сервер
                messageInput.value = ''; // Очищаем поле ввода
            }
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        username = request.form.get("username")
        if username and username.strip():
            session['username'] = username.strip()
            return render_template_string(CHAT_TEMPLATE)
        else:
            return "<h1>Пожалуйста, введите ваше имя.</h1>", 400

    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход в чат</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #121212;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            form {
                text-align: center;
            }
            input {
                padding: 10px;
                width: 200px;
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
        </style>
    </head>
    <body>
        <form method="POST">
            <h1>Введите ваше имя:</h1>
            <input type="text" name="username" required>
            <button type="submit">Войти в чат</button>
        </form>
    </body>
    </html>
    """

@socketio.on('send_message')
def handle_message(data):
    print(f"Получено сообщение от {data['username']}: {data['message']}")
    send({'username': data['username'], 'message': data['message']}, broadcast=True)  # Отправляем всем участникам

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=80, debug=True)
