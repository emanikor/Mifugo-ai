import React, { createContext, useContext, useEffect, useState } from "react";
import { getRegions, getSpecies } from "../api/client.js";

const LookupsContext = createContext(null);

/**
 * Ticker-style short codes derived from real names, not hardcoded — so
 * this keeps working as regions/species are added via the backend without
 * needing a frontend code change.
 *   "Lodwar" -> "LDW", "Lokichogio" -> "LOK"
 *   "goat" -> "GOAT", "cattle" -> "CATT"
 */
export function shortCode(name, length = 3) {
  return name ? name.slice(0, length).toUpperCase() : "";
}

export function LookupsProvider({ children }) {
  const [regions, setRegions] = useState([]);
  const [species, setSpecies] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getRegions(), getSpecies()])
      .then(([r, s]) => {
        setRegions(r);
        setSpecies(s);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const regionsById = Object.fromEntries(regions.map((r) => [r.id, r]));
  const speciesById = Object.fromEntries(species.map((s) => [s.id, s]));

  return (
    <LookupsContext.Provider
      value={{ regions, species, regionsById, speciesById, loading, error }}
    >
      {children}
    </LookupsContext.Provider>
  );
}

export function useLookups() {
  const ctx = useContext(LookupsContext);
  if (!ctx) {
    throw new Error("useLookups must be used inside a LookupsProvider");
  }
  return ctx;
}
