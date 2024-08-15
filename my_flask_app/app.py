from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import mysql.connector
import random
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Kết nối cơ sở dữ liệu
db_connection = mysql.connector.connect(
    host="localhost",
    user="flaskuser",
    password="your_password",
    database="sensor_data"
)
cursor = db_connection.cursor()

# Hàm giả lập cảm biến DHT11
def read_dht11():
    humidity = random.uniform(20.0, 80.0)
    temperature = random.uniform(15.0, 30.0)
    return humidity, temperature

# Hàm cập nhật dữ liệu vào cơ sở dữ liệu và phát sự kiện qua WebSocket
def update_data_periodically():
    while True:
        humidity, temperature = read_dht11()
        cursor.execute("INSERT INTO dht11_data (temperature, humidity, led_status) VALUES (%s, %s, %s)",
                       (temperature, humidity, False))
        db_connection.commit()
        # Phát sự kiện mới qua WebSocket mà không dùng broadcast=True
        socketio.emit('update_data', {
            'temperature': temperature,
            'humidity': humidity
        })
        time.sleep(3)  # Chờ 3 giây trước khi cập nhật lần tiếp theo

# Bắt đầu thread để cập nhật dữ liệu định kỳ
thread = threading.Thread(target=update_data_periodically)
thread.daemon = True
thread.start()

@app.route('/')
def index():
    cursor.execute("SELECT * FROM dht11_data ORDER BY id DESC LIMIT 1")
    last_data = cursor.fetchone()

    cursor.execute("SELECT temperature, humidity, timestamp FROM dht11_data ORDER BY id DESC LIMIT 20")
    chart_data = list(cursor.fetchall())  # Chuyển đổi generator thành danh sách

    return render_template('index.html', last_data=last_data, chart_data=chart_data)

@app.route('/toggle_led')
def toggle_led():
    cursor.execute("SELECT led_status FROM dht11_data ORDER BY id DESC LIMIT 1")
    last_status = cursor.fetchone()[0]
    new_status = not last_status
    cursor.execute("INSERT INTO dht11_data (temperature, humidity, led_status) VALUES (%s, %s, %s)",
                   (None, None, new_status))
    db_connection.commit()
    
    # Phát sự kiện LED Status qua WebSocket mà không dùng broadcast=True
    socketio.emit('led_status', {'led_status': new_status})
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
