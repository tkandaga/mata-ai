from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Halo, ini web Python dari ARRA!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
