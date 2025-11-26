// Connect to SocketIO
const socket = io();  // assumes socket.io.js is loaded in HTML

// Get current user ID from a data attribute on <body> or other method
const userId = document.body.dataset.userId;

// Currently active room
let currentRoomId = null;

// =====================
// Join personal room for notifications
// =====================
socket.on("connect", () => {
    if (userId) {
        socket.emit("connect"); // triggers server-side handle_connect
    }
});

// =====================
// Handle new matches
// =====================
socket.on("new_match", data => {
    console.log("New match received:", data);
    addMatchToSidebar(data);
});

// =====================
// Handle receiving messages
// =====================
// Listen for incoming messages
socket.on("receive_message", data => {
    appendMessage(data.match_id, data.sender_id, data.message);
});

// Helper to append message to chat box
function appendMessage(matchId, senderId, message) {
    const chatBox = document.getElementById(`chat-box-${matchId}`);
    if (!chatBox) return;

    const messagesDiv = chatBox.querySelector(".messages");
    const messageEl = document.createElement("p");
    messageEl.textContent = `User ${senderId}: ${message}`;
    messagesDiv.appendChild(messageEl);

    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Select all sidebar items and attach click listeners
document.querySelectorAll("#chat-sidebar li").forEach(item => {
    item.addEventListener("click", () => {
        const matchId = item.dataset.roomId;
        joinRoom(matchId);
    });
});

// Attach send button event listeners
document.querySelectorAll(".send-button").forEach(button => {
    button.addEventListener("click", () => {
        const chatBox = button.closest("div");
        const matchId = chatBox.id.replace("chat-box-", "");
        const input = chatBox.querySelector(".message-input");
        const message = input.value.trim();
        if (message) {
            sendMessage(matchId, message);
            input.value = "";
        }
    });
});

// =====================
// Join a chat room when clicking sidebar
// =====================
function joinRoom(matchId) {
    currentRoomId = matchId;
    // Emit event to server
    socket.emit("join_room", { match_id: matchId });

    // Show the chat box for this room
    document.querySelectorAll("#chat-boxes > div").forEach(box => {
        box.style.display = "none"; // hide all
    });

    const chatBox = document.getElementById(`chat-box-${matchId}`);
    if (chatBox) {
        chatBox.style.display = "block"; // show this room
    }
}

// =====================
// Send message to a room
// =====================
function sendMessage(matchId, message) {
    if (!message) return;

    socket.emit("send_message", {
        match_id: matchId,
        sender_id: userId,
        message: message
    });

    // Optionally, append message locally
    appendMessage(matchId, userId, message);
}

// =====================
// Helper: add match to sidebar dynamically
// =====================
function addMatchToSidebar(match) {
    const sidebar = document.querySelector("#chat-sidebar ul");
    if (!sidebar) return;

    // Compute the other user in the match
    const otherUserId = (data.student_user_id == userId)
        ? data.therapist_user_id
        : data.student_user_id;

    // Create new <li> for the sidebar
    const li = document.createElement("li");
    li.dataset.roomId = data.match_id;
    li.textContent = `Chat with user ${otherUserId}`;

    // Attach click listener to join room
    li.addEventListener("click", () => {
        joinRoom(data.match_id);
    });

    // Add the new room to the sidebar
    sidebar.appendChild(li);

    // Optionally, create a hidden chat box for this match
    const chatBoxes = document.getElementById("chat-boxes");
    const newChatBox = document.createElement("div");
    newChatBox.id = `chat-box-${data.match_id}`;
    newChatBox.style.display = "none"; // hidden initially
    chatBoxes.appendChild(newChatBox);
}