const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const chat = document.getElementById("chat");

function addMessage(type, text) {
    const div = document.createElement("div");

    div.className = `message ${type}`;
    div.textContent = text;

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function sendQuestion(question) {
    addMessage("user", question);

    try {
        const response = await fetch("http://127.0.0.1:5001/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        if (!response.ok) {
            addMessage("assistant", data.error || "Something went wrong.");
            return;
        }

        addMessage("assistant", data.answer);

    } catch (error) {
        addMessage(
            "assistant",
            "Cannot connect to the Study Agent backend. Make sure the backend is running."
        );
    }
}

form.addEventListener("submit", function(event) {
    event.preventDefault();

    const question = input.value.trim();

    if (!question) {
        return;
    }

    input.value = "";
    sendQuestion(question);
});

function useExample(text) {
    input.value = text;
    input.focus();
}
