import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time

current_round_id = 0
round_active = False
is_paused = False
round_number = 0

app = Flask(__name__)
socketio = SocketIO(app)

players = {}
submissions = {}
ready_players = set()
game_started = False

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    global game_started
    name = data['name']

    if game_started:
        emit('error', {'message': 'Game already in progress'})
        return

    if name in players:
        emit('error', {'message': 'Name already taken'})
        return

    players[name] = {'points': 10, 'ready': False}
    emit('joined', {'name': name, 'players': list(players.keys())}, broadcast=True)
        # Emit updated player list
    socketio.emit("updatePlayerList", {"players": list(players.keys())})
    
    # Get client IP address
    ip = request.remote_addr

    # Print join info in server console (CMD window)
    print(f"Player '{name}' joined from IP: {ip}")

    emit('joined', {'name': name, 'players': list(players.keys())}, broadcast=True)
    socketio.emit("updatePlayerList", {"players": list(players.keys())})


@socketio.on('ready')
def handle_ready(data):
    name = data['name']
    players[name]['ready'] = True
    ready_players.add(name)
    emit('ready_update', {'ready_players': list(ready_players)}, broadcast=True)

    if len(ready_players) == len(players):
        start_game()
        
@socketio.on('pause_game')
def pause_game():
    global is_paused
    is_paused = True
    socketio.emit('game_paused')

@socketio.on('resume_game')
def resume_game():
    global is_paused
    if is_paused:
        is_paused = False
        socketio.emit('game_resumed')
        start_round()


@socketio.on('restart_game')
def handle_restart(data=None):
    global players, submissions, round_active, game_started, round_number, ready_players
    
    ADMIN_PASSWORD = "admin"
    
    # If password is required, check it
    if data is not None:
        if data.get('password') != ADMIN_PASSWORD:
            emit('restart_response', {'success': False, 'message': 'Incorrect password or missing password.'})
            return
    # Reset all game state
    players = {}
    ready_players.clear()
    submissions = {}
    round_active = False
    game_started = False
    round_number = 0
    
    socketio.emit('ready_update', {'ready_players': []})
    socketio.emit('updatePlayerList', {'players': []})
    # Notify all clients that the game has reset
    socketio.emit('game_reset', {
        'message': 'Game has been reset. Please re-join.'
    })
    
@socketio.on("remove_player")
def handle_remove_player(data):
    name = data.get("name")
    if name in players:
        del players[name]
        # Broadcast updated player list
        socketio.emit("updatePlayerList", {"players": list(players.keys())})


def start_game():
    global game_started
    game_started = True
    socketio.emit('game_start')
    for p in players:
        players[p]['ready'] = False

    socketio.emit('game_start')
    start_round()

def start_round():
    global current_round_id, round_active, submissions, round_number, is_paused

    if is_paused:
        return

    submissions = {}
    current_round_id += 1
    round_number += 1
    round_id = current_round_id
    round_active = True

    socketio.emit('new_round', {
        'players': list(players.keys()),
        'round_number': round_number
    })

@socketio.on('submit')
def handle_submission(data):
    global submissions

    if not round_active:
        return  # Round ended early

    name = data['name']
    number = int(data['number'])

    if name not in submissions:
        submissions[name] = number

    if len(submissions) == len(players):
        process_round()

def process_round():
    global submissions, round_active

    if not round_active:
        return  # Timer or submit race — ignore

    round_active = False  # Lock the round
    
    win_reason = None  # Optional explanation

    if not submissions:
        socketio.emit('round_result', {'message': 'No submissions this round.'})
        return
    # Special case: 2 players, one submits 0 and one submits 100
    if len(submissions) == 2:
        values = list(submissions.values())
        if sorted(values) == [0, 100]:
            winners = [p for p, v in submissions.items() if v == 100]
            win_reason = "Special Rule: 100 beats 0 in 1v1"
        else:
            winners = None
    else:
        winners = None

    # If not already assigned by special rule, use other rule sets
    if winners is None:
        from collections import Counter
        value_counts = Counter(submissions.values())
        has_duplicates = any(count > 1 for count in value_counts.values())
        has_100 = 100 in submissions.values()

        values_ex_100 = [v for v in submissions.values() if v != 100]
        value_counts_ex_100 = Counter(values_ex_100)
        has_duplicates_ex_100 = any(count > 1 for count in value_counts_ex_100.values())
        count_100 = list(submissions.values()).count(100)

        if len(submissions) > 2 and count_100 == 1 and has_duplicates_ex_100:
            winners = [p for p, v in submissions.items() if v == 100]
            win_reason = "Special Rule: Sole 100 wins when others have duplicates"
        else:
            avg = sum(submissions.values()) / len(submissions)
            target = avg * 0.8
            closest_diff = min(abs(v - target) for v in submissions.values())
            winners = [p for p, v in submissions.items() if abs(v - target) == closest_diff]
            
    # Deduct points from non-winners
    for name in list(players.keys()):
        if name not in winners:
            players[name]['points'] -= 1

    # Eliminate players with 0 or fewer points
    eliminated = [p for p, info in players.items() if info['points'] <= 0]
    for p in eliminated:
        del players[p]

    # Send round result to all players
    avg = sum(submissions.values()) / len(submissions)
    target = avg * 0.8
    socketio.emit('round_result', {
        'target': round(target, 2),
        'winners': winners,
        'players': {p: players[p]['points'] for p in players},
        'submissions': submissions,
        'eliminated': eliminated,
        'win_reason': win_reason
    })

    submissions = {}

    if len(players) == 1:
        winner = list(players.keys())[0]
        socketio.emit('game_over', {'winner': winner})
        
        # Reset game state directly here
        players.clear()
        ready_players.clear()
        submissions.clear()
        round_active = False
        game_started = False
        round_number = 0
        # Optionally notify clients that the game has fully reset
        socketio.emit('updatePlayerList', {"players": []})
    else:
        start_round()


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
