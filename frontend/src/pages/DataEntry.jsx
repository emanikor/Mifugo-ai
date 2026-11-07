import React, { useState } from "react";
import { Radio, Plus, TrendingUp } from "lucide-react";
import { createPriceEntry } from "../api/client.js";
import { useLookups } from "../context/LookupsContext.jsx";

const todayISO = () => new Date().toISOString().slice(0, 10);

const resultStyles = {
  valid: "bg-green-50 text-green-800 border border-green-100",
  flagged: "bg-amber-50 text-amber-800 border border-amber-100",
  rejected: "bg-red-50 text-red-800 border border-red-100",
};

export default function DataEntry() {
  const { regions, species, loading: lookupsLoading, error: lookupsError } = useLookups();

  const [form, setForm] = useState({
    region_id: "",
    species_id: "",
    price_kes: "",
    market_date: todayISO(),
    notes: "",
  });
  // NOTE: "Market Demand" is part of the visual design but isn't a field
  // in the backend schema (PriceEntryCreate only has region/species/price/
  // date/notes). Rather than silently dropping it from the UI, it's folded
  // into the free-text `notes` field on submit below. If you want this as
  // a first-class, queryable field, it needs adding to:
  //   backend/migrations/schema.sql (price_entries table)
  //   backend/app/models.py (PriceEntry)
  //   backend/app/schemas.py (PriceEntryCreate / PriceEntryOut)
  const [demand, setDemand] = useState("Medium");

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const combinedNotes = [form.notes.trim(), `Market demand: ${demand}`]
        .filter(Boolean)
        .join(" | ");

      const entry = await createPriceEntry({
        region_id: Number(form.region_id),
        species_id: Number(form.species_id),
        price_kes: Number(form.price_kes),
        market_date: form.market_date,
        notes: combinedNotes,
      });
      setResult(entry);
      setForm((prev) => ({ ...prev, price_kes: "", notes: "" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col min-h-full">
      <header className="flex items-center justify-between px-8 py-5 border-b border-green-100 bg-white">
        <div>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Plus size={18} className="text-green-600" />
            Log Transaction
          </h1>
          <p className="text-xs text-gray-500">
            Enter a price observed at market — validated automatically against
            recent history
          </p>
        </div>
      </header>

      <main className="flex-1 p-6 md:p-8">
        <div className="max-w-md">
          <div className="bg-white rounded-xl border border-green-100 p-6">
            {lookupsError && (
              <div className="text-sm text-red-700 mb-4">{lookupsError}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    Livestock
                  </label>
                  <select
                    value={form.species_id}
                    onChange={(e) => updateField("species_id", e.target.value)}
                    disabled={lookupsLoading}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {species.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">
                    Market
                  </label>
                  <select
                    value={form.region_id}
                    onChange={(e) => updateField("region_id", e.target.value)}
                    disabled={lookupsLoading}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {regions.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                  Price (KES)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs font-mono">
                    KES
                  </span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min="1"
                    placeholder="0"
                    value={form.price_kes}
                    onChange={(e) => updateField("price_kes", e.target.value)}
                    required
                    className="w-full border border-gray-300 rounded-lg pl-12 pr-3 py-2 text-sm font-mono tabular-nums text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                  Date observed at market
                </label>
                <input
                  type="date"
                  value={form.market_date}
                  onChange={(e) => updateField("market_date", e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                  Market Demand
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {["High", "Medium", "Low"].map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setDemand(level)}
                      className={
                        "py-2 rounded-lg text-sm font-medium border transition-colors " +
                        (demand === level
                          ? "bg-green-700 border-green-700 text-white"
                          : "bg-white border-gray-300 text-gray-600 hover:bg-gray-50")
                      }
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                  Notes (optional)
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => updateField("notes", e.target.value)}
                  placeholder="e.g. animal age/condition, seller context"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  rows={2}
                />
              </div>

              {error && (
                <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting || lookupsLoading}
                className="w-full flex items-center justify-center gap-2 bg-green-700 hover:bg-green-800 disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
              >
                <Radio size={16} />
                {submitting ? "Broadcasting..." : "Broadcast to Network"}
              </button>
            </form>
          </div>

          {result && (
            <div className={`mt-4 rounded-xl p-4 text-sm ${resultStyles[result.outlier_status]}`}>
              {result.outlier_status === "valid" && (
                <p className="flex items-center gap-1.5 font-medium">
                  <TrendingUp size={14} /> Saved — consistent with recent market data.
                </p>
              )}
              {result.outlier_status === "flagged" && (
                <>
                  <p className="font-medium">Saved, but flagged for review.</p>
                  <p className="mt-1 opacity-90">{result.outlier_reason}</p>
                </>
              )}
              {result.outlier_status === "rejected" && (
                <>
                  <p className="font-medium">Rejected as a likely error.</p>
                  <p className="mt-1 opacity-90">{result.outlier_reason}</p>
                  <p className="mt-1 opacity-90">
                    It has been saved, not deleted — an official can review and
                    override it.
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
