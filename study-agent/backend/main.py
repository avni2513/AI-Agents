from flask import Flask, request, jsonify
from flask_cors import CORS

from agent import answer

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agent": "Study Assistant Agent"
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "error": "Question is required"
        }), 400

    response = answer(question)

    return jsonify({
        "question": question,
        "answer": response
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
