from flask import Flask
from routes import init_routes
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "cellprotege_secret_key"
app.permanent_session_lifetime = timedelta(minutes=40)

init_routes(app)

if __name__ == "__main__":
    app.run(debug=True)