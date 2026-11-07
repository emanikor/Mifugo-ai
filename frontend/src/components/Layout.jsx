import React, { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutGrid,
  Radio,
  FileBarChart,
  Settings,
  Info,
  LogOut,
  ArrowUp,
  ArrowDown,
  Minus,
  CloudRain,
  AlertTriangle,
} from "lucide-react";
import { clearToken, getPriceEntries } from "../api/client.js";
import { LookupsProvider, useLookups, shortCode } from "../context/LookupsContext.jsx";

const navItems = [
  { to: "/", label: "Market Terminal", Icon: LayoutGrid, end: true },
  { to: "/entry", label: "Log Entry", Icon: FileBarChart, end: false },
  { to: "/field-report", label: "Field Report", Icon: CloudRain, end: false },
  { to: "/alerts", label: "Alerts", Icon: AlertTriangle, end: false },
  { to: "/chat", label: "Bush Link", Icon: Radio, end: false },
  // "Bush Link" keeps the mockup's own voice for the chat/broadcast page —
  // fits the offline word-of-mouth network concept. "Log Entry" replaces
  // the mockup's "Regional Reports" label, since /entry is actually the
  // price-entry form, not a reports page (no reports feature exists yet).
];

const directionStyles = {
  up: { className: "text-green-400", Icon: ArrowUp },
  down: { className: "text-red-400", Icon: ArrowDown },
  flat: { className: "text-green-600", Icon: Minus },
};

function Sidebar() {
  return (
    <aside className="w-64 shrink-0 bg-green-900 text-green-50 flex flex-col relative">
      <div className="px-6 py-6 border-b border-green-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-green-50 flex items-center justify-center text-green-900 font-black text-sm">
            M
          </div>
          <span className="font-bold tracking-tight text-white">
            Mifugo<span className="text-green-300">Connect</span>
          </span>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 relative">
        <div className="absolute left-7 top-8 bottom-8 w-px bg-green-800" />
        <p className="pl-2 pb-3 text-xs font-semibold uppercase tracking-widest text-green-500">
          Main Menu
        </p>
        <div className="space-y-1">
          {navItems.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                "relative w-full flex items-center gap-3 pl-2 pr-3 py-2.5 rounded-lg text-sm font-medium transition-colors " +
                (isActive
                  ? "bg-green-800 text-white"
                  : "text-green-200 hover:bg-green-800/50 hover:text-white")
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={
                      "flex items-center justify-center w-6 h-6 rounded-full shrink-0 " +
                      (isActive ? "bg-green-400 text-green-950" : "bg-green-900 text-green-400")
                    }
                  >
                    <Icon size={13} strokeWidth={2.5} />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      <SidebarFooter />
    </aside>
  );
}

function SidebarFooter() {
  function handleLogout() {
    clearToken();
    // Full reload keeps this simple: App.jsx re-derives auth state from
    // localStorage on mount, no extra prop drilling needed for the footer.
    window.location.href = "/login";
  }

  return (
    <div className="px-4 py-4 border-t border-green-800 space-y-1">
      <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-green-300 hover:bg-green-800/50 hover:text-white transition-colors">
        <Settings size={16} strokeWidth={2} />
        Settings
      </button>
      <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-green-300 hover:bg-green-800/50 hover:text-white transition-colors">
        <Info size={16} strokeWidth={2} />
        About
      </button>
      <button
        onClick={handleLogout}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-green-300 hover:bg-green-800/50 hover:text-white transition-colors"
      >
        <LogOut size={16} strokeWidth={2} />
        Log out
      </button>
    </div>
  );
}

/**
 * Live ticker of the most recent validated price broadcasts across the
 * whole network — real data, not mock. Renders nothing if there isn't
 * enough data yet, rather than showing an empty scrolling bar.
 *
 * TODO: "direction" (up/down/flat) isn't a field the backend returns today
 * — it's computed here by comparing each entry to the next-most-recent
 * valid entry for the same region+species. If you'd rather this be
 * computed server-side (e.g. added to PriceEntryOut), that's a small
 * addition to backend/app/routers/prices.py.
 */
function TickerStrip() {
  const { regionsById, speciesById, loading: lookupsLoading } = useLookups();
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getPriceEntries({ status_filter: "valid", limit: 30 })
      .then(setEntries)
      .catch((err) => setError(err.message));
  }, []);

  if (lookupsLoading || error || entries.length < 2) return null;

  const withDirection = entries.map((entry, idx) => {
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

  const feed = withDirection.slice(0, 12);
  const doubled = [...feed, ...feed];

  return (
    <div className="bg-green-950 overflow-hidden border-b border-green-900">
      <div className="flex items-center gap-8 px-8 py-2 whitespace-nowrap overflow-x-auto">
        {doubled.map((entry, i) => {
          const d = directionStyles[entry.direction];
          const Icon = d.Icon;
          const region = regionsById[entry.region_id];
          const sp = speciesById[entry.species_id];
          return (
            <div key={`${entry.id}-${i}`} className="flex items-center gap-2 shrink-0">
              <span className="font-mono text-xs font-bold text-green-400">
                {shortCode(region?.name)}·{shortCode(sp?.name, 4)}
              </span>
              <span className="font-mono text-xs text-green-100 tabular-nums">
                {entry.price_kes.toLocaleString()}
              </span>
              <Icon size={11} className={d.className} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Layout() {
  return (
    <LookupsProvider>
      <div className="min-h-screen bg-stone-50 flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TickerStrip />
          <main className="flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </LookupsProvider>
  );
}
