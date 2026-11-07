import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import DataEntry from "./pages/DataEntry.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Chat from "./pages/Chat.jsx";
import Alerts from "./pages/Alerts.jsx";
import FieldReport from "./pages/FieldReport.jsx";
import { getToken } from "./api/client.js";

// Auth state is just "does a token exist" — the token itself is verified
// backend-side on every request. Good enough for a local, single-user-at-a-
// time field laptop; not meant to be a hardened multi-tenant auth system.
function useAuth() {
  const [isAuthed, setIsAuthed] = useState(() => !!getToken());
  useEffect(() => {
    const onStorage = () => setIsAuthed(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  return [isAuthed, setIsAuthed];
}

function RequireAuth({ isAuthed, children }) {
  if (!isAuthed) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const [isAuthed, setIsAuthed] = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<Login onLoggedIn={() => setIsAuthed(true)} />} />
      <Route
        path="/"
        element={
          <RequireAuth isAuthed={isAuthed}>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="entry" element={<DataEntry />} />
        <Route path="chat" element={<Chat />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="field-report" element={<FieldReport />} />
      </Route>
    </Routes>
  );
}
