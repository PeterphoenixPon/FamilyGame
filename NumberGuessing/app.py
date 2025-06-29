# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Game state
secret_number = random.randint(0, 1000)
min_bound = 0
max_bound = 1000
players = {}
turn_order = []
current_turn = 0

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    username = data['username']
    if username not in players:
        players[username] = {'points': 0}
        turn_order.append(username)
    emit('game_state', {
        'message': f"{username} joined the game.",
        'hint': f"Guess a number between {min_bound} and {max_bound}",
        'players': players,
        'current_player': turn_order[current_turn]
    }, broadcast=True)

RESET_PASSWORD = "admin"  # You can change this to anything secret
@socketio.on('reset_game')
def handle_reset(data):
    global secret_number, min_bound, max_bound, players, turn_order, current_turn
    
    if data.get('password') != RESET_PASSWORD:
        emit('error', {'message': "Incorrect reset password."})
        return

    secret_number = random.randint(0, 1000)
    min_bound = 0
    max_bound = 1000
    players.clear()
    turn_order.clear()
    current_turn = 0

    emit('game_state', {
        'message': "Game has been reset. Everyone must rejoin.",
        'hint': "Guess a number between 0 and 1000",
        'players': {},
        'current_player': None
    }, broadcast=True)


@socketio.on('guess')
def handle_guess(data):
    global min_bound, max_bound, secret_number, current_turn

    username = data['username']
    guess = int(data['guess'])

    if username != turn_order[current_turn]:
        emit('error', {'message': f"Not your turn, {username}!"})
        return

    if guess == secret_number:
        players[username]['points'] += 1
        emit('game_state', {
            'message': f"{username} guessed the number {secret_number} and wins the round!",
            'players': players,
            'hint': "Starting new round...",
            'current_player': None
        }, broadcast=True)

        # Reset round
        secret_number = random.randint(0, 1000)
        min_bound = 0
        max_bound = 1000
        current_turn = (current_turn + 1) % len(turn_order)

        socketio.sleep(2)
        emit('game_state', {
            'message': "New round started!",
            'hint': f"Guess a number between {min_bound} and {max_bound}",
            'current_player': turn_order[current_turn]
        }, broadcast=True)
    else:
        if guess < secret_number:
            min_bound = max(min_bound, guess)
        else:
            max_bound = min(max_bound, guess)

        current_turn = (current_turn + 1) % len(turn_order)
        emit('game_state', {
            'message': f"{username} guessed {guess}.",
            'hint': f"Guess a number between {min_bound} and {max_bound}",
            'players': players,
            'current_player': turn_order[current_turn]
        }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5002)
