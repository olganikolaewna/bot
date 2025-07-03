from flask import Flask

app = Flask(__name__)

@app.route("/pay/<int:user_id>")
def pay(user_id):
    return f"""
    <html>
        <head><title>Фейковая оплата</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h2>Оплата для пользователя {user_id}</h2>
            <p>Это фейковая страница оплаты.</p>
            <p>Нажмите <b>Назад</b> и в Telegram-боте кнопку <b>"Я оплатил"</b>.</p>
        </body>
    </html>
    """

# if __name__ == "_main_":
#     app.run(host="0.0.0.0", port=5005)