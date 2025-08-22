import { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const inputRef = useRef();
  const outputRef = useRef();

  // Auto-scroll chat box when messages update
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle sending user message and streaming AI response
  const sendMessage = async () => {
    const userMessage = inputRef.current.value.trim();
    if (!userMessage) return;

    // Add user message to UI
    setMessages((prev) => [...prev, { sender: "user", text: userMessage }]);
    inputRef.current.value = "";

    const inputData = {
      threadId: "thread-123",
      runId: "run-abc",
      state: {},
      messages: [{ id: "1234", role: "user", content: userMessage }],
      tools: [],
      context: [{ description: "session", value: "test-run" }],
      forwardedProps: {}
    };

    try {
      const response = await fetch("http://localhost:8000/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          accept: "text/event-stream"
        },
        body: JSON.stringify(inputData)
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop(); // keep incomplete

        for (const part of parts) {
          if (part.startsWith("data:")) {
            try {
              const jsonStr = part.replace(/^data:\s*/, "");
              const event = JSON.parse(jsonStr);
              handleEvent(event);
            } catch (err) {
              console.error("Parse error", err, part);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Handle AI / system events
  const handleEvent = (event) => {
    switch (event.type) {
      case "RUN_STARTED":
        setMessages((prev) => [
          ...prev,
          {
            sender: "system",
            text: `✅ Run started (thread ${event.threadId}, run ${event.runId})`
          }
        ]);
        break;

      case "TEXT_MESSAGE_CONTENT":
        setMessages((prev) => [...prev, { sender: "ai", text: event.delta }]);
        break;

      case "TOOL_CALL_CHUNK":
        setMessages((prev) => [
            ...prev,
            { sender: "ai", component: <WeatherCard location={event.delta} themeColor="rgb(34, 34, 34)" /> }
          ]);
        break;

      case "RUN_FINISHED":
        setMessages((prev) => [
          ...prev,
          {
            sender: "system",
            text: `🏁 Run finished (thread ${event.threadId}, run ${event.runId})`
          }
        ]);
        break;

      default:
        setMessages((prev) => [
          ...prev,
          { sender: "system", text: `📦 Unknown event: ${JSON.stringify(event)}` }
        ]);
    }
  };

  return (
    <div className="chat-container">
      <h1>OCI Agent</h1>
      <div ref={outputRef} className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.sender}`}>
            {msg.component ? (
              msg.component
            ) : (
              <>
                <b>
                  {msg.sender === "user"
                    ? "You"
                    : msg.sender === "ai"
                      ? "AI"
                      : "System"}
                  :
                </b>{" "}
                {msg.text}
              </>
            )}
          </div>
        ))}
      </div>
      <div className="input-container">
        <input
          ref={inputRef}
          type="text"
          placeholder="Type a message..."
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

// Example task card component
function TaskCard({ task }) {
  return (
    <div className="bg-blue-600 text-white p-3 rounded-xl shadow-md">
      📝 {task}
    </div>
  );
}

// Example weather card component
function WeatherCard({ location, themeColor }) {
  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl p-4 text-white shadow-lg"
    >
      <h4>{location}</h4>
      <p>Current Weather: 70°, Clear skies</p>
    </div>
  );
}

export default App;
