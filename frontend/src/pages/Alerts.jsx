import React, { useEffect, useState } from "react";
import { CloudRain, Bug, ShieldCheck, RefreshCw } from "lucide-react";
import { getAlerts } from "../api/client.js";

const severityStyles = {
  emergency: "bg-red-50 border-red-200 text-red-800",
  critical: "bg-red-50 border-red-200 text-red-800",
  alarm: "bg-orange-50 border-orange-200 text-orange-800",
  high: "bg-orange-50 border-orange-200 text-orange-800",
  alert: "bg-amber-50 border-amber-200 text-amber-800",
  medium: "bg-amber-50 border-amber-200 text-amber-800",
  low: "bg-green-50 border-green-200 text-green-800",
  normal: "bg-green-50 border-green-200 text-green-800",
};

const typeIcon = { drought: CloudRain, disease: Bug };

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAlerts();
      setAlerts(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col min-h-full">
      <header className="flex items-center justify-between px-8 py-5 border-b border-green-100 bg-white">
        <div>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <CloudRain size={18} className="text-green-600" />
            Alerts
          </h1>
          <p className="text-xs text-gray-500">
            Active drought status and unresolved disease reports, offline-synced
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 px-3 py-1.5 rounded-full hover:bg-green-100 transition-colors"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </header>

      <main className="flex-1 p-6 md:p-8">
        {error && (
          <div className="text-sm bg-red-50 text-red-800 border border-red-100 rounded-lg px-3 py-2 mb-4">
            {error}
          </div>
        )}

        {loading && <p className="text-sm text-gray-400">Loading alerts...</p>}

        {!loading && alerts.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center gap-2 text-center py-16 bg-white border border-green-100 rounded-xl">
            <ShieldCheck size={28} className="text-green-600" />
            <p className="text-sm font-medium text-gray-700">No active alerts</p>
            <p className="text-xs text-gray-400">
              No drought conditions or unresolved disease reports on record.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {alerts.map((alert, i) => {
            const Icon = typeIcon[alert.type] || CloudRain;
            const style = severityStyles[alert.severity] || severityStyles.medium;
            return (
              <div
                key={i}
                className={`flex items-start gap-3 rounded-xl border p-4 ${style}`}
              >
                <Icon size={18} className="shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-sm">{alert.title}</p>
                    <span className="text-xs font-mono font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-white/60">
                      {alert.region_name}
                    </span>
                  </div>
                  <p className="text-sm mt-0.5 opacity-90">{alert.detail}</p>
                  <p className="text-xs mt-1 opacity-60 font-mono">{alert.date}</p>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
