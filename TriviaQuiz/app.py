# app.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Load and shuffle questions
with open('questions.json') as f:
    all_questions = json.load(f)
questions = random.sample(all_questions, 20)  # Select 20 random questions

# Game state
players = {}  # {username: {score: 0, current_q: 0}}
admin_password = "admin"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    icon = data.get('icon', '😀')  # default icon if none sent
    if username not in players:
        players[username] = {'score': 0, 'current_q': 0, 'icon': icon}
    else:
        players[username]['icon'] = icon  # update icon if player re-joins
    send_game_state(f"{username} joined the game.")

@socketio.on('answer')
def handle_answer(data):
    username = data['username']
    answer = data['answer']
    player = players.get(username)

    if player is None:
        return

    q_index = player['current_q']
    if q_index >= len(questions):
        return

    correct_answer = questions[q_index]['answer']
    if answer == correct_answer:
        player['score'] += 1

    player['current_q'] += 1
    send_game_state(f"{username} answered question {q_index + 1}.")

@socketio.on('reset_game')
def reset_game(data):
    global questions
    if data.get('password') != admin_password:
        emit('error', {'message': 'Incorrect reset password.'})
        return

    questions = random.sample(all_questions, 20)
    players.clear()  # remove all players completely
    send_game_state("Game has been reset by admin.")


def send_game_state(message):
    socketio.emit('game_state', {
        'message': message,
        'players': players,
        'questions': questions
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5003)
