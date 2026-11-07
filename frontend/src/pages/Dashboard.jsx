import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowUp,
  ArrowDown,
  Minus,
  Pencil,
  Trash2,
  Signal,
  TrendingUp,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getPriceEntries, reviewPriceEntry } from "../api/client.js";
import { useLookups, shortCode } from "../context/LookupsContext.jsx";

const directionStyles = {
  up: { className: "text-green-700 bg-green-50", Icon: ArrowUp },
  down: { className: "text-red-700 bg-red-50", Icon: ArrowDown },
  flat: { className: "text-gray-500 bg-gray-100", Icon: Minus },
};

const STATUS_LABELS = {
  valid: "Valid",
  flagged: "Flagged",
  rejected: "Rejected",
};

function BroadcastWatchBadge() {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
      </span>
      Live market watch
    </div>
  );
}

function PriceAnalyticsCard({ regions, species }) {
  const [regionId, setRegionId] = useState("");
  const [speciesId, setSpeciesId] = useState("");
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  // Default to the first region/species once lookups load.
  useEffect(() => {
    if (regions.length && !regionId) setRegionId(String(regions[0].id));
  }, [regions, regionId]);
  useEffect(() => {
    if (species.length && !speciesId) setSpeciesId(String(species[0].id));
  }, [species, speciesId]);

  useEffect(() => {
    if (!regionId || !speciesId) return;
    getPriceEntries({
      region_id: regionId,
      species_id: speciesId,
      status_filter: "valid",
      limit: 30,
    })
      .then((rows) => {
        // API returns most-recent-first; chart reads left-to-right in time.
        const ascending = [...rows].reverse();
        setHistory(
          ascending.map((r) => ({ day: r.market_date, price: r.price_kes }))
        );
      })
      .catch((err) => setError(err.message));
  }, [regionId, speciesId]);

  const regionName = regions.find((r) => String(r.id) === regionId)?.name;
  const speciesName = species.find((s) => String(s.id) === speciesId)?.name;

  const prices = history.map((h) => h.price);
  const yDomain =
    prices.length > 0
      ? [Math.min(...prices) * 0.95, Math.max(...prices) * 1.05]
      : ["auto", "auto"];

  return (
    <div className="bg-white rounded-xl border border-green-100 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
            Price Analytics
          </p>
          <h2 className="text-base font-bold text-gray-900 font-mono tabular-nums">
            {shortCode(speciesName, 4) || "—"} · {shortCode(regionName) || "—"}{" "}
            <span className="text-gray-400 font-sans font-normal text-sm">
              — recent trend
            </span>
          </h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full">
          <Signal size={12} />
          Live
        </span>
      </div>

      <div className="flex flex-wrap gap-3 mt-3 mb-4">
        <select
          value={regionId}
          onChange={(e) => setRegionId(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {regions.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <select
          value={speciesId}
          onChange={(e) => setSpeciesId(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {species.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="text-sm text-red-700 mb-2">{error}</div>}

      {history.length === 0 ? (
        <div className="h-56 flex items-center justify-center text-sm text-gray-400">
          No validated price history yet for this region/species.
        </div>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#16a34a" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ecfdf5" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11, fill: "#9ca3af", fontFamily: "monospace" }}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#9ca3af", fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                domain={yDomain}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #d1fae5",
                  fontSize: 12,
                  fontFamily: "monospace",
                }}
                formatter={(value) => [`${value.toLocaleString()} KES`, "Price"]}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#16a34a"
                strokeWidth={2.5}
                fill="url(#priceFill)"
                dot={{ r: 3.5, fill: "#16a34a", strokeWidth: 0 }}
                activeDot={{ r: 5.5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function NetworkUpdatesTable({ regionsById, speciesById }) {
  const [entries, setEntries] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter ? { status_filter: statusFilter } : {};
      const data = await getPriceEntries(params);
      setEntries(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  // Direction is derived client-side (see TODO in Layout.jsx's TickerStrip)
  // by comparing each entry to the next-older entry for the same
  // region+species within the currently loaded page of entries.
  const withDirection = useMemo(() => {
    return entries.map((entry, idx) => {
      const olderMatch = entries
        .slice(idx + 1)
        .find(
          (e) => e.region_id === entry.region_id && e.species_id === entry.species_id
        );
      let direction = "flat";
      if (olderMatch) {
        if (entry.price_kes > olderMatch.price_kes) direction = "up";
        else if (entry.price_kes < olderMatch.price_kes) direction = "down";
      }
      return { ...entry, direction };
    });
  }, [entries]);

  async function handleReview(entryId, newStatus) {
    try {
      await reviewPriceEntry(entryId, newStatus);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-green-100 p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-1">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
            Network Feed
          </p>
          <h2 className="text-base font-bold text-gray-900">Latest Updates</h2>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="">All</option>
          <option value="valid">Valid</option>
          <option value="flagged">Flagged</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {error && <div className="text-sm text-red-700 mt-2">{error}</div>}
      {loading && <div className="text-sm text-gray-400 mt-4">Loading...</div>}
      {!loading && entries.length === 0 && (
        <div className="text-sm text-gray-400 mt-4">No price entries found.</div>
      )}

      {!loading && entries.length > 0 && (
        <div className="overflow-x-auto -mx-6 px-6 flex-1 mt-3">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-widest text-gray-400 border-b border-gray-200">
                <th className="pb-3 pr-4 font-semibold">Hub</th>
                <th className="pb-3 pr-4 font-semibold">Livestock</th>
                <th className="pb-3 pr-4 font-semibold">Price</th>
                <th className="pb-3 pr-4 font-semibold">Move</th>
                <th className="pb-3 pr-4 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {withDirection.map((row) => {
                const d = directionStyles[row.direction];
                const Icon = d.Icon;
                const region = regionsById[row.region_id];
                const sp = speciesById[row.species_id];
                return (
                  <tr key={row.id} className="border-b border-gray-100 last:border-0">
                    <td className="py-3 pr-4">
                      <span className="font-mono text-xs font-bold text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
                        {shortCode(region?.name)}
                      </span>
                      <span className="ml-2 text-gray-500 text-xs hidden sm:inline">
                        {region?.name || "—"}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-700 capitalize">
                      {sp?.name || "—"}
                    </td>
                    <td className="py-3 pr-4 font-mono tabular-nums font-semibold text-gray-900">
                      {row.price_kes.toLocaleString()}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={
                          "inline-flex items-center justify-center w-6 h-6 rounded-full " +
                          d.className
                        }
                      >
                        <Icon size={13} strokeWidth={2.5} />
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={
                          "text-xs font-medium px-2 py-0.5 rounded-full " +
                          (row.outlier_status === "valid"
                            ? "bg-green-50 text-green-700"
                            : row.outlier_status === "flagged"
                            ? "bg-amber-50 text-amber-700"
                            : "bg-red-50 text-red-700")
                        }
                      >
                        {STATUS_LABELS[row.outlier_status]}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {row.outlier_status !== "valid" && (
                          <button
                            onClick={() => handleReview(row.id, "valid")}
                            className="p-1.5 rounded-md text-gray-400 hover:text-green-700 hover:bg-green-50 transition-colors"
                            aria-label={`Mark ${sp?.name || "entry"} at ${region?.name || ""} valid`}
                          >
                            <Pencil size={14} />
                          </button>
                        )}
                        {row.outlier_status !== "rejected" && (
                          <button
                            onClick={() => handleReview(row.id, "rejected")}
                            className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            aria-label={`Reject ${sp?.name || "entry"} at ${region?.name || ""}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { regions, species, regionsById, speciesById, loading } = useLookups();

  return (
    <div className="flex flex-col min-h-full">
      <header className="flex items-center justify-between px-8 py-5 border-b border-green-100 bg-white">
        <div>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <TrendingUp size={18} className="text-green-600" />
            Market Terminal
          </h1>
          <p className="text-xs text-gray-500">Turkana livestock market intelligence</p>
        </div>
        <BroadcastWatchBadge />
      </header>

      <main className="flex-1 p-6 md:p-8 space-y-6">
        {loading ? (
          <div className="text-sm text-gray-400">Loading market data...</div>
        ) : (
          <>
            <PriceAnalyticsCard regions={regions} species={species} />
            <NetworkUpdatesTable regionsById={regionsById} speciesById={speciesById} />
          </>
        )}
      </main>
    </div>
  );
}
