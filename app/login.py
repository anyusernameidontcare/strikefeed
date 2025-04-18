from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    print("✅ Route / was hit!")
    return "<h1>✅ Flask is working</h1>"

if __name__ == "__main__":
    print("🚀 Starting Flask...")
    app.run(debug=True)
