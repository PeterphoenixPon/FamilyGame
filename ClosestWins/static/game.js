let socket = io();
let myName = "";
let isPaused = false;

function togglePause() {
    if (!isPaused) {
        socket.emit('pause_game');
    } else {
        socket.emit('resume_game');
    }
}

function joinGame() {
    myName = document.getElementById("nameInput").value;
    socket.emit('join', { name: myName });
}

function sendReady() {
    socket.emit('ready', { name: myName });
}

function submitGuess() {
    const input = document.getElementById("guessInput");  // declare input here
    let num = parseInt(input.value, 10);

    if (isNaN(num) || num < 0 || num > 100) {
        alert("Please enter a number between 0 and 100.");
        return;
    }

    socket.emit('submit', { name: myName, number: num });

    // Disable input and submit button
    input.disabled = true;
    document.querySelector("button[onclick='submitGuess()']").disabled = true;

    // Show waiting message
    document.getElementById("submitMessage").innerText = "You have submitted, now waiting for other players...";
}


socket.on('joined', data => {
    localStorage.setItem('myName', myName);
    document.getElementById("rules").style.display = "none";  // 
    document.getElementById("lobby").style.display = "block";
    renderPlayersList(data.players);
});

socket.on('ready_update', data => {
    renderPlayersList(data.ready_players);
});

socket.on('game_start', () => {
    document.getElementById("lobby").style.display = "none";
    document.getElementById("gameArea").style.display = "block";
    document.getElementById("main_screen").style.display = "none"; 
});


socket.on('round_result', data => {
    console.log("Round result received:", data); 

    const resultsDiv = document.getElementById("results");
    const playerScoresDiv = document.getElementById("playerScores");

    // Show target and submissions
    let html = `<strong>Target:</strong> ${data.target}<br><br>`;
    html += `<strong>Player submissions:</strong><br>`;
    for (let [player, number] of Object.entries(data.submissions)) {
        html += `${player}: ${number}<br>`;
    }
    if (data.winners && data.winners.length > 0) {
        const winnerText = data.winners.length === 1 ? "Winner" : "Winners";
        html += `<br><strong> ${winnerText}:</strong> ${data.winners.join(', ')}`;
    }
    if (data.win_reason) {
        html += `<br><em>(${data.win_reason})</em>`;
    }
    resultsDiv.innerHTML = html;
    // Build score table
    let scoreHTML = `<strong>Current Scores & Last Input:</strong><ul>`;
    for (let [player, pts] of Object.entries(data.players)) {
        const lastInput = data.submissions?.[player] ?? "¡ª";
        scoreHTML += `<li>${player}: ${pts} points (last: ${lastInput})</li>`;
    }
    scoreHTML += `</ul>`;

    // Update the HTML
    playerScoresDiv.innerHTML = scoreHTML;

    // Show my points separately
    document.getElementById("points").innerText =
        `Your Points: ${data.players[myName]}`;
});


socket.on('new_round', data => {
    document.getElementById("roundCounter").innerText =
        `Now you are in round ${data.round_number}`;

    // Reset input and submit button
    const input = document.getElementById("guessInput");
    input.disabled = false;
    input.value = "";

    const submitBtn = document.querySelector("button[onclick='submitGuess()']");
    submitBtn.disabled = false;

    // Clear waiting message
    document.getElementById("submitMessage").innerText = "";

    // Optionally clear previous results
    // document.getElementById("results").innerText = "";
});


socket.on('game_paused', () => {
    isPaused = true;
    document.getElementById("pauseMessage").innerText = "Game is paused";
    document.getElementById("pauseButton").innerText = "Resume";
});

socket.on('game_resumed', () => {
    isPaused = false;
    document.getElementById("pauseMessage").innerText = "";
    document.getElementById("pauseButton").innerText = "Pause";
});


socket.on('game_over', data => {
    document.getElementById("gameOverMessage").innerText = `Game Over! Winner is ${data.winner}`;
    document.getElementById("gameOverArea").style.display = "block";
    document.getElementById("gameArea").style.display = "none";
});

//function updatePlayerList(players) {
//    let list = document.getElementById("playerList");
//    list.innerHTML = "";
//    players.forEach(p => {
//        let li = document.createElement("li");
//        li.innerText = p;
//        list.appendChild(li);
//    });
//}
socket.on("updatePlayerList", data => {
    renderPlayersList(data.players);
});

function restartGame() {
    socket.emit('restart_game'); // Ask server to reset
    socket.emit('join', { name: localStorage.getItem('myName') });
    document.getElementById("lobby").style.display = "block";
    location.reload(); // Refresh page to reset client state
}

function renderPlayersList(players) {
    const playersListDiv = document.getElementById("playersList");
    if (!playersListDiv) return; // Exit if div isn't found

    playersListDiv.innerHTML = "";  // Clear existing

    players.forEach(player => {
        const playerDiv = document.createElement("div");
        playerDiv.style.marginBottom = "5px";
        playerDiv.style.display = "inline-flex";   // inline-flex so it hugs content
        playerDiv.style.alignItems = "right";     // Vertically center text & button
        playerDiv.style.justifyContent = "space-between"; // keeps space balanced

        const nameSpan = document.createElement("span");
        nameSpan.innerText = player;

        const removeBtn = document.createElement("button");
        removeBtn.innerText = "x";                   // Use a small '¡Á' instead of "Remove"
        removeBtn.title = "Remove player";           // Tooltip on hover
        removeBtn.style.marginLeft = "5px";       // small space from name
        removeBtn.style.marginRight = "20px";       // small space from name
        removeBtn.style.padding = "0";         // Smaller padding
        removeBtn.style.fontSize = "0.5em";          // Smaller font
        removeBtn.style.cursor = "pointer";
        removeBtn.style.border = "1px solid #ccc";
        removeBtn.style.borderRadius = "50%";  // makes button round
        removeBtn.style.width = "20px";
        removeBtn.style.height = "20px";
        removeBtn.style.background = "#f8f8f8";
        removeBtn.style.lineHeight = "10px";
        removeBtn.style.textAlign = "top";

        // Attach event to emit remove request
        removeBtn.onclick = () => {
            if (confirm(`Remove player "${player}"?`)) {
                socket.emit("remove_player", { name: player });
            }
        };

        playerDiv.appendChild(nameSpan);
        playerDiv.appendChild(removeBtn);

        playersListDiv.appendChild(playerDiv);
    });
}

socket.on('error', data => {
    const errDiv = document.getElementById("errorMessage");
    errDiv.innerText = data.message;
    errDiv.style.display = "block";  // make sure the div is visible
});

function restartGameWithPassword() {
    const password = prompt("Enter admin password to restart the game:");
    if (!password) return;

    socket.emit('restart_game', { password: password });
}

socket.on('restart_response', data => {
    alert(data.message);
    if (data.success) {
        // Optional: reload page or reset UI
        location.reload();
    }
});