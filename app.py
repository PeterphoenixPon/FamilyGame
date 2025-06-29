import socket
from flask import Flask, render_template

app = Flask(__name__)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

@app.route('/')
def index():
    local_ip = get_local_ip()
    return render_template('index.html', ip=local_ip)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
