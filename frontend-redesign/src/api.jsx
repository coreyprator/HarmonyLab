/* =====================================================================
   HarmonyLab — API client (live-only, cookie-auth)
   HM44.1: No mock mode. All requests use credentials:"include" to send
   the hl_session cookie. Redirects to /login on 401.
   ===================================================================== */

import React from 'react';
import { CHORD_QUALITIES } from './data.jsx';

const { useState: useStateA, useEffect: useEffectA, useMemo: useMemoA,
        useCallback: useCallbackA, useRef: useRefA,
        useContext: useContextA, createContext: createContextA } = React;

const ApiContext = createContextA(null);

export function ApiProvider({ children }) {
  const [lastError, setLastError] = useStateA(null);
  const clearError = useCallbackA(() => setLastError(null), []);

  const fetcher = useCallbackA(async (path, opts = {}) => {
    const headers = { "Accept": "application/json" };
    // Only set Content-Type for non-FormData bodies
    if (opts.body && !(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    Object.assign(headers, opts.headers || {});

    let res;
    try {
      res = await fetch(path, { ...opts, headers, credentials: "include" });
    } catch (e) {
      const err = { kind: "network", message: e?.message || "Network error", path };
      setLastError(err);
      throw err;
    }
    if (res.status === 401) {
      window.location.href = "/login";
      throw { kind: "auth", message: "Unauthenticated", path };
    }
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      const err = { kind: "http", status: res.status, message: `HTTP ${res.status}: ${txt.slice(0, 200)}`, path };
      setLastError(err);
      throw err;
    }
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json();
    // blob for downloads
    return res.blob();
  }, []);

  const value = useMemoA(() => ({
    fetcher, lastError, clearError,
    mode: "live", isLive: true, isReady: true,
  }), [fetcher, lastError, clearError]);

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApi() {
  const ctx = useContextA(ApiContext);
  if (!ctx) throw new Error("useApi must be inside ApiProvider");
  return ctx;
}
// global shorthand for proto compatibility
window.hlUseApi = useApi;

/* ------------------------------------------------------------------ */
/* SWR-lite                                                            */
/* ------------------------------------------------------------------ */
export function useApiQuery(keyFn, fetchFn, deps) {
  const [data, setData] = useStateA(null);
  const [loading, setLoading] = useStateA(false);
  const [error, setError] = useStateA(null);
  const reqId = useRefA(0);
  useEffectA(() => {
    let cancelled = false;
    const id = ++reqId.current;
    setLoading(true); setError(null);
    Promise.resolve(fetchFn())
      .then(d => { if (!cancelled && id === reqId.current) { setData(d); setLoading(false); } })
      .catch(e => { if (!cancelled && id === reqId.current) { setError(e); setLoading(false); } });
    return () => { cancelled = true; };
  }, deps);
  return { data, loading, error, refresh: () => { reqId.current++; setData(null); } };
}
window.hlUseApiQuery = useApiQuery;

/* ------------------------------------------------------------------ */
/* Transforms                                                         */
/* ------------------------------------------------------------------ */
export function beSongToLibraryRow(row) {
  return {
    id: row.id,
    title: row.title || "(untitled)",
    composer: row.composer || "—",
    genre: row.genre || "—",
    key: row.original_key || row.detected_key || "C maj",
    form: row.form_override || row.form || "—",
    measureCount: row.measure_count || 0,
    chordCount: row.chord_count || row.total_chords || 0,
    importedAt: (row.created_at || "").slice(0, 16).replace("T", " "),
    fsModifiedAt: (row.fs_modified_at || "").slice(0, 16).replace("T", " ") || null,
    hasXml: !!(row.has_raw_xml ?? row.raw_xml),
    hasNotes: !!row.has_note_data,
    hasLyrics: !!row.has_lyrics,
    overrideCount: row.override_count || 0,
  };
}
window.hlBeSongToLibraryRow = beSongToLibraryRow;

export function splitRoman(s) {
  if (!s) return { roman: "", superscript: "", romanCase: "major" };
  const m = String(s).match(/^([ivxIVX♭♯#b]+)(.*)/);
  if (!m) return { roman: s, superscript: "", romanCase: /[A-Z]/.test(s) ? "major" : "minor" };
  return { roman: m[1], superscript: m[2], romanCase: /^[ivx♭♯#b]+$/.test(m[1]) ? "minor" : "major" };
}

export function normKeyCenter(k) {
  if (!k) return "C maj";
  const s = String(k).trim();
  if (/maj$|major$/i.test(s)) return s.replace(/\s*(major|maj)$/i, " maj").replace(/\s+/g, " ").trim();
  if (/min$|minor$/i.test(s)) return s.replace(/\s*(minor|min)$/i, " min").replace(/\s+/g, " ").trim();
  return s + " maj";
}
window.hlNormKeyCenter = normKeyCenter;

export function keyCenterForMeasure(keyRegions, measureNumber) {
  for (const r of keyRegions || []) {
    if (measureNumber >= r.startMeasure && measureNumber <= r.endMeasure) return r.key;
  }
  return keyRegions?.[0]?.key || "C maj";
}

export function transformChord(c, measureNumber, keyRegions, overrideMap) {
  const ov = overrideMap.get(c.chord_index) || overrideMap.get(c.id);
  const rawRoman = ov?.roman_override || c.roman_numeral || "";
  const split = splitRoman(rawRoman);
  return {
    id: c.id,
    symbol: c.chord_symbol_override || c.chord_symbol || "?",
    roman: split.roman,
    superscript: split.superscript,
    romanCase: split.romanCase,
    function: ov?.function_override || c.function_label || "—",
    keyCenter: normKeyCenter(c.key_center) || keyCenterForMeasure(keyRegions, measureNumber),
    voicing: c.voicing_notation || "",
    comment: c.comments || "",
    isInferred: !!(c.is_inferred),
    isManualEdit: !!c.is_manual_edit,
    hasOverride: !!ov,
    confidence: c.confidence || 0,
    beat: c.beat_position || 1.0,
    chordIndex: c.chord_index ?? 0,
    measureNumber,
  };
}

export function beAnalysisToSong(songRow, analysis, keyCenters, exchanges, overrides) {
  const keyRegions = (keyCenters?.regions || keyCenters || analysis?.key_regions || []).map(r => ({
    startMeasure: r.start_measure ?? r.startMeasure,
    endMeasure: r.end_measure ?? r.endMeasure,
    key: normKeyCenter(r.key_center ?? r.key),
    weight: (r.end_measure ?? r.endMeasure) - (r.start_measure ?? r.startMeasure) + 1,
    isUserDefined: !!(r.is_user_defined ?? r.isUserDefined),
  }));
  if (keyRegions.length === 0) {
    keyRegions.push({ startMeasure: 1, endMeasure: songRow.measure_count || 32, key: normKeyCenter(songRow.original_key), weight: songRow.measure_count || 32, isUserDefined: false });
  }

  const sections = [];
  const rawSections = analysis?.sections || [];
  const rawMeasures = analysis?.measures || [];
  const rawChords = analysis?.chords || [];
  const overrideMap = new Map();
  for (const o of overrides || []) overrideMap.set(o.chord_index ?? o.chord_id, o);

  if (rawSections.length && rawSections[0]?.measures) {
    for (const sec of rawSections) {
      sections.push({
        id: sec.id, name: sec.name, subtitle: sec.notes || "",
        measures: (sec.measures || []).map(m => ({
          id: m.id, number: m.measure_number ?? m.number,
          chords: (m.chords || []).map(c => transformChord(c, m.measure_number ?? m.number, keyRegions, overrideMap)),
        })),
      });
    }
  } else if (rawMeasures.length) {
    const bySection = new Map();
    for (const m of rawMeasures) {
      if (!bySection.has(m.section_id)) bySection.set(m.section_id, []);
      bySection.get(m.section_id).push(m);
    }
    for (const sec of rawSections) {
      const ms = (bySection.get(sec.id) || []).sort((a, b) => (a.measure_number ?? 0) - (b.measure_number ?? 0));
      sections.push({
        id: sec.id, name: sec.name, subtitle: sec.notes || "",
        measures: ms.map(m => ({
          id: m.id, number: m.measure_number,
          chords: rawChords.filter(c => c.measure_id === m.id).map(c => transformChord(c, m.measure_number, keyRegions, overrideMap)),
        })),
      });
    }
  } else if (rawChords.length) {
    sections.push({
      id: 1, name: "A", subtitle: "(flat)",
      measures: rawChords.map((c, i) => ({
        id: i, number: i + 1,
        chords: [transformChord(c, i + 1, keyRegions, overrideMap)],
      })),
    });
  }

  return {
    id: songRow.id,
    title: songRow.title,
    composer: songRow.composer || "—",
    year: songRow.year_composed || "",
    genre: songRow.genre || "—",
    originalKey: normKeyCenter(songRow.original_key),
    tempo: songRow.tempo_marking || "",
    timeSig: songRow.time_signature || "4/4",
    form: songRow.form_override || "—",
    detectedKey: normKeyCenter(analysis?.detected_key || songRow.original_key),
    manualKeyOverride: analysis?.manual_key_override || null,
    confidence: analysis?.confidence ?? 0,
    hasXml: !!(songRow.has_raw_xml ?? songRow.raw_xml),
    hasNotes: !!songRow.has_note_data,
    hasLyrics: !!songRow.has_lyrics,
    measureCount: songRow.measure_count || sections.reduce((a, s) => a + s.measures.length, 0),
    chordCount: sections.reduce((a, s) => a + s.measures.reduce((b, m) => b + m.chords.length, 0), 0),
    importedAt: (songRow.created_at || "").slice(0, 16).replace("T", " "),
    fsModifiedAt: (songRow.fs_modified_at || "").slice(0, 16).replace("T", " ") || null,
    sourceFileName: songRow.source_file_name || "",
    sourceFileType: songRow.source_file_type || "",
    overrideCount: (overrides || []).length,
    sections,
    keyRegions,
    patterns: analysis?.patterns || [],
    phrases: analysis?.phrases || [],
    aiExchanges: (exchanges || []).map(ex => ({
      date: (ex.exchange_at || "").slice(0, 10),
      question: ex.user_comment || "(no question)",
      outcome: ex.outcome || "pending",
      rejectionReason: ex.rejection_reason || null,
    })),
    importHistory: [],
  };
}

/* ------------------------------------------------------------------ */
/* Data hooks                                                         */
/* ------------------------------------------------------------------ */
export function useLibraryRows() {
  const api = useApi();
  return useApiQuery("library", async () => {
    const data = await api.fetcher("/api/v1/songs/?limit=200");
    const rows = Array.isArray(data) ? data : (data.songs || data.results || []);
    return rows.map(beSongToLibraryRow);
  }, []);
}
window.hlUseLibraryRows = useLibraryRows;

export function useSong(songId) {
  const api = useApi();
  return useApiQuery(`song:${songId}`, async () => {
    const [songRow, analysis, keyCenters, exchanges, overrides] = await Promise.all([
      api.fetcher(`/api/v1/songs/${songId}`),
      api.fetcher(`/api/v1/analysis/songs/${songId}`).catch(() => ({})),
      api.fetcher(`/api/v1/analysis/songs/${songId}/key-centers`).catch(() => null),
      api.fetcher(`/api/v1/analysis/songs/${songId}/exchanges`).catch(() => []),
      api.fetcher(`/api/v1/analysis/songs/${songId}/overrides`).catch(() => []),
    ]);
    return beAnalysisToSong(songRow, analysis, keyCenters, exchanges, overrides);
  }, [songId]);
}
window.hlUseSong = useSong;

export function usePreferences() {
  const api = useApi();
  return useApiQuery("prefs", () => api.fetcher("/api/v1/preferences"), []);
}
window.hlUsePreferences = usePreferences;

export function useChordVocabulary() {
  const api = useApi();
  return useApiQuery("vocab", async () => {
    const data = await api.fetcher("/api/v1/vocabulary/chord-symbols");
    if (Array.isArray(data) && data[0]?.suffix !== undefined) return data;
    if (Array.isArray(data)) return data.map(d => ({
      suffix: d.symbol || d.suffix || d.name || "",
      displayJazz: d.jazz_notation || d.display || d.symbol || "",
      displayPlain: d.plain_notation || d.display || d.symbol || "",
      type: d.quality || d.type || "",
      intervals: d.intervals || "",
      aliases: d.aliases || [],
    }));
    return CHORD_QUALITIES;
  }, []);
}
window.hlUseChordVocabulary = useChordVocabulary;

export function useAuditData(songId) {
  const api = useApi();
  return useApiQuery(`audit:${songId}`, async () => {
    const [song, audit] = await Promise.all([
      api.fetcher(`/api/v1/songs/${songId}`),
      api.fetcher(`/api/v1/songs/${songId}/audit`).catch(() => null),
    ]);
    return { song, audit };
  }, [songId]);
}
window.hlUseAuditData = useAuditData;

/* ------------------------------------------------------------------ */
/* Misc helpers                                                        */
/* ------------------------------------------------------------------ */
export function hlFlattenChords(song) {
  const out = [];
  for (const sec of (song.sections || [])) {
    for (const meas of (sec.measures || [])) {
      for (const ch of (meas.chords || [])) {
        out.push({ ...ch, measureNumber: meas.number });
      }
    }
  }
  return out;
}
window.hlFlattenChords = hlFlattenChords;

export function hlMergeKeyRegion(regions, startM, endM, key) {
  const next = regions.filter(r => !(r.startMeasure >= startM && r.endMeasure <= endM));
  next.push({ startMeasure: startM, endMeasure: endM, key, weight: endM - startM + 1, isUserDefined: true });
  return next.sort((a, b) => a.startMeasure - b.startMeasure);
}
window.hlMergeKeyRegion = hlMergeKeyRegion;

// Key CSS class helper
const KEY_CSS_MAP = {
  "C": "k-C", "C#": "k-Cs", "Db": "k-Db", "D": "k-D", "D#": "k-Ds", "Eb": "k-Eb",
  "E": "k-E", "F": "k-F", "F#": "k-Fs", "Gb": "k-Gb", "G": "k-G", "G#": "k-Gs",
  "Ab": "k-Ab", "A": "k-A", "A#": "k-As", "Bb": "k-Bb", "B": "k-B",
};
export function hlKeyCss(keyStr) {
  if (!keyStr) return "k-C";
  const root = keyStr.replace(/\s*(maj|min|major|minor)\s*$/i, "").trim();
  return KEY_CSS_MAP[root] || "k-C";
}
window.hlKeyCss = hlKeyCss;

// Toast hook
export function hlUseToasts() {
  const [items, setItems] = useStateA([]);
  let _id = 0;
  const push = useCallbackA((msg, opts = {}) => {
    const id = ++_id;
    setItems(prev => [...prev.slice(-4), { id, msg, ...opts }]);
    setTimeout(() => setItems(prev => prev.filter(t => t.id !== id)), opts.duration || 4000);
  }, []);
  const dismiss = useCallbackA((id) => setItems(prev => prev.filter(t => t.id !== id)), []);
  return { items, push, dismiss };
}
window.hlUseToasts = hlUseToasts;

// State persistence (localStorage)
export function hlLoadState() {
  try { return JSON.parse(localStorage.getItem("hl_app_state") || "{}"); }
  catch { return {}; }
}
export function hlSaveState(patch) {
  const cur = hlLoadState();
  localStorage.setItem("hl_app_state", JSON.stringify({ ...cur, ...patch }));
}
window.hlLoadState = hlLoadState;
window.hlSaveState = hlSaveState;

// Route helpers
export function parseHash() {
  const h = window.location.hash.replace("#", "");
  if (!h) return null;
  if (h.startsWith("/song/")) return { name: "song", id: parseInt(h.split("/")[2]) };
  if (h.startsWith("/audit/")) return { name: "audit", id: parseInt(h.split("/")[2]) };
  if (h === "/settings") return { name: "settings" };
  if (h === "/lab") return { name: "lab" };
  return { name: "library" };
}
export function encodeRoute(r) {
  if (r.name === "song") return `#/song/${r.id}`;
  if (r.name === "audit") return `#/audit/${r.id}`;
  if (r.name === "settings") return "#/settings";
  if (r.name === "lab") return "#/lab";
  return "#/";
}
window.hlParseHash = parseHash;
window.hlEncodeRoute = encodeRoute;

// Provide as top-level too (proto compat)
window.HL_DATA = window.HL_DATA || {};
