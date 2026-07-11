import React, { useState } from "react";
import { CloudRain, Bug, Send } from "lucide-react";
import { createClimateBulletin, createDiseaseReport } from "../api/client.js";
import { useLookups } from "../context/LookupsContext.jsx";

const todayISO = () => new Date().toISOString().slice(0, 10);

const droughtLevels = ["normal", "alert", "alarm", "emergency"];
const droughtButtonStyles = {
  normal: "bg-green-700 border-green-700 text-white",
  alert: "bg-amber-600 border-amber-600 text-white",
  alarm: "bg-orange-600 border-orange-600 text-white",
  emergency: "bg-red-700 border-red-700 text-white",
};
const severityLevels = ["low", "medium", "high", "critical"];
const severityButtonStyles = {
  low: "bg-green-700 border-green-700 text-white",
  medium: "bg-amber-600 border-amber-600 text-white",
  high: "bg-orange-600 border-orange-600 text-white",
  critical: "bg-red-700 border-red-700 text-white",
};

function LevelToggle({ levels, value, onChange, styles }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {levels.map((level) => (
        <button
          key={level}
          type="button"
          onClick={() => onChange(level)}
          className={
            "py-2 rounded-lg text-xs font-semibold border transition-colors capitalize " +
            (value === level
              ? styles[level]
              : "bg-white border-gray-300 text-gray-600 hover:bg-gray-50")
          }
        >
          {level}
        </button>
      ))}
    </div>
  );
}

function ClimateForm({ regions }) {
  const [form, setForm] = useState({
    region_id: "",
    bulletin_date: todayISO(),
    drought_status: "normal",
    rainfall_mm: "",
    temperature_c: "",
    source: "Field observation",
    notes: "",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const bulletin = await createClimateBulletin({
        region_id: Number(form.region_id),
        bulletin_date: form.bulletin_date,
        drought_status: form.drought_status,
        rainfall_mm: form.rainfall_mm ? Number(form.rainfall_mm) : null,
        temperature_c: form.temperature_c ? Number(form.temperature_c) : null,
        source: form.source,
        notes: form.notes || null,
      });
      setResult(bulletin);
      setForm((prev) => ({ ...prev, rainfall_mm: "", temperature_c: "", notes: "" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Region</label>
        <select
          value={form.region_id}
          onChange={(e) => update("region_id", e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        >
          <option value="" disabled>Select</option>
          {regions.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Date observed</label>
        <input
          type="date"
          value={form.bulletin_date}
          onChange={(e) => update("bulletin_date", e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Drought status</label>
        <LevelToggle
          levels={droughtLevels}
          value={form.drought_status}
          onChange={(v) => update("drought_status", v)}
          styles={droughtButtonStyles}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Rainfall (mm)</label>
          <input
            type="number"
            value={form.rainfall_mm}
            onChange={(e) => update("rainfall_mm", e.target.value)}
            placeholder="optional"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono tabular-nums text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Temp (°C)</label>
          <input
            type="number"
            value={form.temperature_c}
            onChange={(e) => update("temperature_c", e.target.value)}
            placeholder="optional"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono tabular-nums text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Source</label>
        <input
          type="text"
          value={form.source}
          onChange={(e) => update("source", e.target.value)}
          placeholder="e.g. Field observation, or NDMA Turkana Bulletin June 2026"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Notes (optional)</label>
        <textarea
          value={form.notes}
          onChange={(e) => update("notes", e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      {error && (
        <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full flex items-center justify-center gap-2 bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        <Send size={16} />
        {submitting ? "Saving..." : "Log Climate Bulletin"}
      </button>

      {result && (
        <div className="rounded-xl p-4 text-sm bg-green-50 text-green-800 border border-green-100">
          Saved — {result.drought_status.toUpperCase()} status logged for{" "}
          {regions.find((r) => r.id === result.region_id)?.name}.
        </div>
      )}
    </form>
  );
}

function DiseaseForm({ regions, species }) {
  const [form, setForm] = useState({
    region_id: "",
    species_id: "",
    report_date: todayISO(),
    disease_name: "",
    symptoms: "",
    affected_count: "",
    severity: "medium",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const report = await createDiseaseReport({
        region_id: Number(form.region_id),
        species_id: Number(form.species_id),
        report_date: form.report_date,
        disease_name: form.disease_name,
        symptoms: form.symptoms || null,
        affected_count: form.affected_count ? Number(form.affected_count) : null,
        severity: form.severity,
      });
      setResult(report);
      setForm((prev) => ({ ...prev, disease_name: "", symptoms: "", affected_count: "" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Livestock</label>
          <select
            value={form.species_id}
            onChange={(e) => update("species_id", e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="" disabled>Select</option>
            {species.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">Region</label>
          <select
            value={form.region_id}
            onChange={(e) => update("region_id", e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="" disabled>Select</option>
            {regions.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Date observed</label>
        <input
          type="date"
          value={form.report_date}
          onChange={(e) => update("report_date", e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          Suspected disease (or "Unknown")
        </label>
        <input
          type="text"
          value={form.disease_name}
          onChange={(e) => update("disease_name", e.target.value)}
          required
          placeholder="e.g. Foot and Mouth Disease"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Symptoms</label>
        <textarea
          value={form.symptoms}
          onChange={(e) => update("symptoms", e.target.value)}
          rows={2}
          placeholder="What did you observe?"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          Animals affected (optional)
        </label>
        <input
          type="number"
          min="0"
          value={form.affected_count}
          onChange={(e) => update("affected_count", e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono tabular-nums text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">Severity</label>
        <LevelToggle
          levels={severityLevels}
          value={form.severity}
          onChange={(v) => update("severity", v)}
          styles={severityButtonStyles}
        />
      </div>

      {error && (
        <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full flex items-center justify-center gap-2 bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        <Send size={16} />
        {submitting ? "Saving..." : "Submit Disease Report"}
      </button>

      {result && (
        <div className="rounded-xl p-4 text-sm bg-amber-50 text-amber-800 border border-amber-100">
          Saved as <strong>unverified</strong> — an official will review and
          confirm or dismiss this report. It has not been removed either way.
        </div>
      )}
    </form>
  );
}

export default function FieldReport() {
  const { regions, species, loading } = useLookups();
  const [tab, setTab] = useState("climate");

  return (
    <div className="flex flex-col min-h-full">
      <header className="flex items-center justify-between px-8 py-5 border-b border-green-100 bg-white">
        <div>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <CloudRain size={18} className="text-green-600" />
            Field Report
          </h1>
          <p className="text-xs text-gray-500">
            Log a climate observation or a suspected disease outbreak
          </p>
        </div>
      </header>

      <main className="flex-1 p-6 md:p-8">
        <div className="max-w-md">
          <div className="grid grid-cols-2 gap-2 mb-4">
            <button
              onClick={() => setTab("climate")}
              className={
                "flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium border transition-colors " +
                (tab === "climate"
                  ? "bg-green-700 border-green-700 text-white"
                  : "bg-white border-gray-300 text-gray-600 hover:bg-gray-50")
              }
            >
              <CloudRain size={14} /> Climate
            </button>
            <button
              onClick={() => setTab("disease")}
              className={
                "flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium border transition-colors " +
                (tab === "disease"
                  ? "bg-green-700 border-green-700 text-white"
                  : "bg-white border-gray-300 text-gray-600 hover:bg-gray-50")
              }
            >
              <Bug size={14} /> Disease
            </button>
          </div>

          <div className="bg-white rounded-xl border border-green-100 p-6">
            {loading ? (
              <p className="text-sm text-gray-400">Loading form...</p>
            ) : tab === "climate" ? (
              <ClimateForm regions={regions} />
            ) : (
              <DiseaseForm regions={regions} species={species} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
