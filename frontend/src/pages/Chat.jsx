import React, { useState } from "react";
import { Radio, Send } from "lucide-react";
import { askQuestion } from "../api/client.js";

export default function Chat() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // {role, text, supportingData?}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim()) return;

    const userMessage = { role: "user", text: question };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion(userMessage.text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.answer,
          supportingData: response.supporting_data,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col min-h-full">
      <header className="flex items-center justify-between px-8 py-5 border-b border-green-100 bg-white">
        <div>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Radio size={18} className="text-green-600" />
            Bush Link
          </h1>
          <p className="text-xs text-gray-500">
            Ask about market prices — answered from validated local data, fully offline
          </p>
        </div>
      </header>

      <main className="flex-1 p-6 md:p-8 flex flex-col">
        <div className="max-w-2xl w-full mx-auto flex-1 flex flex-col">
          <p className="text-sm text-gray-400 italic mb-4">
            e.g. "What is the average price of a camel in Lodwar this week?"
          </p>

          <div className="flex-1 flex flex-col gap-3 mb-4 min-h-52">
            {messages.length === 0 && !loading && (
              <div className="flex-1 flex items-center justify-center text-sm text-gray-400 border border-dashed border-gray-200 rounded-xl">
                No questions asked yet — try one above.
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  "max-w-[80%] rounded-xl px-4 py-3 text-sm " +
                  (m.role === "user"
                    ? "self-end bg-green-700 text-white"
                    : "self-start bg-white border border-green-100 text-gray-800")
                }
              >
                <p>{m.text}</p>
                {m.supportingData && m.supportingData.length > 0 && (
                  <details className="mt-2 text-xs text-gray-500">
                    <summary className="cursor-pointer font-medium">
                      Based on {m.supportingData.length} price record(s)
                    </summary>
                    <ul className="mt-1.5 space-y-0.5 font-mono tabular-nums">
                      {m.supportingData.map((row) => (
                        <li key={row.id}>
                          {row.market_date}: {row.price_kes.toLocaleString()} KES
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}

            {loading && (
              <div className="self-start bg-white border border-green-100 rounded-xl px-4 py-3 text-sm italic text-gray-400">
                Thinking... (the local AI model can take a moment on modest hardware)
              </div>
            )}
          </div>

          {error && (
            <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Type your question..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white font-semibold px-4 py-2.5 rounded-lg text-sm transition-colors"
            >
              <Send size={15} />
              Send
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
