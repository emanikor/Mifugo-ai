import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { login, setToken } from "../api/client.js";

export default function Login({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await login(username, password);
      setToken(result.access_token);
      onLoggedIn();
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-white rounded-xl border border-green-100 p-8"
      >
        <div className="flex items-center gap-2.5 mb-1">
          <div className="w-8 h-8 rounded bg-green-900 flex items-center justify-center text-white font-black text-sm">
            M
          </div>
          <span className="font-bold tracking-tight text-gray-900">
            Mifugo<span className="text-green-700">Connect</span>
          </span>
        </div>
        <p className="text-xs text-gray-500 mb-6">
          Livestock market intelligence — Turkana County
        </p>

        <label htmlFor="username" className="block text-xs font-medium text-gray-500 mb-1.5">
          Username
        </label>
        <input
          id="username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 mb-4 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />

        <label htmlFor="password" className="block text-xs font-medium text-gray-500 mb-1.5">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 mb-4 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />

        {error && (
          <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2 mb-4">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
        >
          <LogIn size={16} />
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>
    </div>
  );
}
