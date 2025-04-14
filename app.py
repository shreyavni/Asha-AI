# app.py
from flask import Flask, request, jsonify, render_template, session
from assistant import chatbot_logic
import config
import os
# import json # Not needed here anymore

app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = config.FLASK_SECRET_KEY
if not app.secret_key:
    print("FATAL: FLASK_SECRET_KEY is not set.")
    exit()

@app.route('/')
def index():
    """Serves the main chat page."""
    if 'chat_history' not in session:
        session['chat_history'] = []
        print("Initialized new chat history in session.")
    if not isinstance(session.get('chat_history'), list):
         session['chat_history'] = []
         print("Corrected non-list chat history in session.")
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chatbot requests, managing history via session."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "Missing 'message' key"}), 400

    chat_history = session.get('chat_history', [])
    if not isinstance(chat_history, list):
        print(f"Warning: Invalid chat_history type in session ({type(chat_history)}), resetting.")
        chat_history = []

    # Process message - NOW receives session_data=None (or remove param)
    # AND returns suggestions
    response_message, suggestions, updated_history = chatbot_logic.process_message(
        user_input=user_message,
        chat_history=chat_history
        # session_data=None # Pass None or remove if function signature updated
    )

    session['chat_history'] = updated_history
    session.modified = True

    # *** CHANGE: Return both response and suggestions ***
    return jsonify({
        "response": response_message,
        "suggestions": suggestions # Add suggestions list to response
        })

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Endpoint to clear the chat history from the session."""
    session.pop('chat_history', None)
    print("Chat history cleared.")
    return jsonify({"status": "History cleared"})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)