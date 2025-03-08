document.addEventListener("DOMContentLoaded", function () {
    if (!username) return;

    let ws;
    const chatBox = document.getElementById("chatBox");
    const messageInput = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");
    const onlineUsersList = document.getElementById("onlineUsersList");
    let lastSender = null;

    function connectWebSocket() {
        ws = new WebSocket(`ws://${window.location.host}/ws/${username}`);

        ws.onopen = () => {
            console.log("WebSocket connected!");
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "message") {
                appendMessage(data.username, data.message);
            } else if (data.type === "online_users") {
                updateOnlineUsers(data.users);
            }
        };

        ws.onclose = () => {
            console.log("WebSocket disconnected, reconnecting...");
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
    }

    function sendMessage() {
        if (ws.readyState === WebSocket.OPEN && messageInput.value.trim() !== "") {
            ws.send(JSON.stringify({ message: messageInput.value.trim() }));
            messageInput.value = "";
        }
    }

    function updateOnlineUsers(users) {
        onlineUsersList.innerHTML = "";
        users.forEach(user => {
            const li = document.createElement("li");
            li.textContent = user;
            onlineUsersList.appendChild(li);
        });
    }

    function appendMessage(sender, message) {
        const messageWrapper = document.createElement("div");
        
        if (sender !== lastSender) {
            messageWrapper.innerHTML = `
                <div class="flex items-center space-x-2 mt-2">
                    <img src="/static/avatars/${sender}.png"
                        onerror="this.src='/static/avatars/default.png';"
                        class="w-8 h-8 rounded-full border border-gray-300">
                    <strong>${sender}</strong>
                </div>
                <div class="ml-10 mb-1 bg-gray-200 rounded-lg px-2 py-1 inline-block">
                    ${message}
                </div>`;
            lastSender = sender;
        } else {
            messageWrapper.innerHTML = `
                <div class="ml-10 mb-1 bg-gray-200 rounded-lg px-2 py-1 inline-block">
                    ${message}
                </div>`;
        }

        chatBox.appendChild(messageWrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    sendButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") sendMessage();
    });

    connectWebSocket();
});

// Scroll to bottom on page load
window.onload = () => {
  const chatBox = document.getElementById("chatBox");
  chatBox.scrollTop = chatBox.scrollHeight;
};
