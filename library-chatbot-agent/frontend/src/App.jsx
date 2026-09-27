import { useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);

  const sendMessage = async () => {
    if (!message.trim()) return;

    const userMessage = message;
    setMessages((prev) => [...prev, { sender: "You", text: userMessage }]);
    setMessage("");

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { sender: "Bot", text: data.response },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: "Bot", text: "Could not connect to the library server." },
      ]);
    }
  };

  return (
    <div className="app">
      <h1>📚 College Library Assistant</h1>

      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className="message">
            <strong>{msg.sender}:</strong> {msg.text}
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") sendMessage();
          }}
          placeholder="Ask about books..."
        />

        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;