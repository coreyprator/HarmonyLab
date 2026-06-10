/* =====================================================================
   HarmonyLab interactive prototype — API client (mock + live modes)
   ---------------------------------------------------------------------
   Mode persistence:
     localStorage.hl_proto_mode    = "mock" | "live"
     sessionStorage.hl_proto_jwt   = "<token>"            (session-scoped)
     localStorage.hl_proto_base    = "https://..."         (BE origin, editable)

   The hook `useApi()` returns { mode, token, base, setMode, setToken, setBase,
     fetcher, isReady, lastError, clearError }
   The hook `useApiQuery(key, fetch, deps)` is a tiny SWR-lite for GET requests.

   Every component reads through these so it stays mode-agnostic. NEW-BE-only
   UI surfaces are flagged via `useMockBanner(feature)` which yields a banner
   string the component renders when live mode is on.

   Read-only mutations: every write path calls `liveToast()` to short-circuit
   in live mode with a "HM44 wires this PUT/POST" message.
   ===================================================================== */

const { useState: useStateA, useEffect: useEffectA, useMemo: useMemoA, useCallback: useCallbackA, useRef: useRefA, useContext: useContextA, createContext: createContextA } = React;

// HM44 Phase B (B2/B6): In single-service mode the frontend IS the backend.
// Use same-origin (empty base = window.location.origin) so API calls route to
// the same Cloud Run service without a proxy hop.
const DEFAULT_BASE = "";
const TOKEN_KEY = "hl_proto_jwt";
const MODE_KEY = "hl_proto_mode";
const BASE_KEY = "hl_proto_base";

// HM43.2: OAuth removed — stub window.auth so legacy callers get null
if (!window.auth) window.auth = { getToken: () => null };

/* ------------------------------------------------------------------ */
/* Live-data API context                                              */
/* ------------------------------------------------------------------ */
const ApiContext = createContextA(null);

function ApiProvider({ children }) {
  // HM44 Phase B: default to "live" (single-service, no token needed — no auth)
  const [mode, setModeS] = useStateA(() => localStorage.getItem(MODE_KEY) || "live");
  const [token, setTokenS] = useStateA(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [base, setBaseS]  = useStateA(() => localStorage.getItem(BASE_KEY) ?? DEFAULT_BASE);
  const [lastError, setLastError] = useStateA(null);

  const setMode = useCallbackA((m) => { localStorage.setItem(MODE_KEY, m); setModeS(m); setLastError(null); }, []);
  const setToken = useCallbackA((t) => { if (t) sessionStorage.setItem(TOKEN_KEY, t); else sessionStorage.removeItem(TOKEN_KEY); setTokenS(t); setLastError(null); }, []);
  const setBase = useCallbackA((b) => { localStorage.setItem(BASE_KEY, b ?? DEFAULT_BASE); setBaseS(b ?? DEFAULT_BASE); }, []);
  const clearError = useCallbackA(() => setLastError(null), []);

  // HM44 Phase B: no auth → mode=live is always "ready" (no token check)
  const isReady = mode === "mock" || mode === "live";

  const fetcher = useCallbackA(async (path, opts = {}) => {
    if (mode === "mock") {
      throw new Error("fetcher called in mock mode — components should branch on mode");
    }
    // HM44 B6: base="" → same-origin relative URL; base with value → cross-origin
    const url = base ? (base.replace(/\/$/, "") + path) : path;
    const headers = {
      "Accept": "application/json",
      "Content-Type": "application/json",
      // HM44 Phase B: no auth in single-service mode
      ...(opts.headers || {}),
    };
    let res;
    try {
      res = await fetch(url, { ...opts, headers, credentials: "omit" });
    } catch (e) {
      const err = { kind: "network", message: e?.message || "Network error", path };
      setLastError(err);
      throw err;
    }
    if (res.status === 401) {
      const err = { kind: "auth", message: "Token rejected (401). Paste a fresh JWT.", path };
      setLastError(err);
      throw err;
    }
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      const err = { kind: "http", status: res.status, message: `HTTP ${res.status}: ${txt.slice(0, 200)}`, path };
      setLastError(err);
      throw err;
    }
    return res.json();
  }, [mode, token, base]);

  const value = useMemoA(() => ({
    mode, token, base, setMode, setToken, setBase,
    fetcher, isReady, lastError, clearError,
    isLive: mode === "live",
  }), [mode, token, base, setMode, setToken, setBase, fetcher, isReady, lastError, clearError]);

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

function useApi() {
  const ctx = useContextA(ApiContext);
  if (!ctx) throw new Error("useApi must be used inside ApiProvider");
  return ctx;
}

/* ------------------------------------------------------------------ */
/* SWR-lite query hook for GETs                                       */
/* ------------------------------------------------------------------ */
function useApiQuery(keyFn, fetchFn, deps) {
  const [data, setData] = useStateA(null);
  const [loading, setLoading] = useStateA(false);
  const [error, setError] = useStateA(null);
  const reqId = useRefA(0);

  useEffectA(() => {
    let cancelled = false;
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    Promise.resolve(fetchFn())
      .then((d) => { if (!cancelled && id === reqId.current) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled && id === reqId.current) { setError(e); setLoading(false); } });
    return () => { cancelled = true; };
  }, deps);

  return { data, loading, error, refresh: () => { reqId.current++; setData(null); } };
}

/* ------------------------------------------------------------------ */
/* Backend → prototype shape transforms                               */
/* The redesign's data model is richer than the raw BE; these         */
/* transforms project canonical BE rows onto prototype shape.          */
/* ------------------------------------------------------------------ */

/* Map BE Songs row to a library row */
function beSongToLibraryRow(row) {
  return {
    id: row.id,
    title: row.title || "(untitled)",
    composer: row.composer || "—",
    genre: row.genre || "—",
    key: row.original_key || row.detected_key || "C maj",  // best-effort
    form: row.form_override || row.form || "—",
    measureCount: row.measure_count || 0,
    chordCount: row.chord_count || row.total_chords || 0,
    importedAt: (row.created_at || row.imported_at || "").slice(0, 16).replace("T", " "),
    fsModifiedAt: (row.fs_modified_at || "").slice(0, 16).replace("T", " ") || null,
    hasXml: !!(row.has_raw_xml ?? row.raw_xml),
    hasNotes: !!row.has_note_data,
    hasLyrics: !!row.has_lyrics,
    overrideCount: row.override_count || 0,
  };
}

/* Split a roman string like "V7♭9" → { roman: "V", superscript: "7♭9", romanCase } */
function splitRoman(s) {
  if (!s) return { roman: "", superscript: "", romanCase: "major" };
  const m = String(s).match(/^([ivxIVX♭♯#b]+)(.*)$/);
  if (!m) return { roman: s, superscript: "", romanCase: /[A-Z]/.test(s) ? "major" : "minor" };
  const base = m[1];
  const sup = m[2];
  // Roman case from base letters (V vs v)
  const isLower = /^[ivx♭♯#b]+$/.test(base);
  return {
    roman: base,
    superscript: sup,
    romanCase: isLower ? "minor" : "major",
  };
}

/* Find the key center active at a given measure number */
function keyCenterForMeasure(keyRegions, measureNumber) {
  for (const r of keyRegions || []) {
    if (measureNumber >= r.startMeasure && measureNumber <= r.endMeasure) return r.key;
  }
  return keyRegions?.[0]?.key || "C maj";
}

/* Normalize BE key center strings to our prototype's "X maj" / "X min" form */
function normKeyCenter(k) {
  if (!k) return "C maj";
  const s = String(k).trim();
  if (/maj$|major$/i.test(s)) return s.replace(/\s*(major|maj)$/i, " maj").replace(/\s+/g, " ").trim();
  if (/min$|minor$/i.test(s)) return s.replace(/\s*(minor|min)$/i, " min").replace(/\s+/g, " ").trim();
  return s + " maj";  // BE often returns just "Bb" — assume major
}

/* Build full song-shape from BE /songs/{id} + /analysis/songs/{id} responses */
function beAnalysisToSong(songRow, analysis, keyCenters, exchanges, overrides) {
  // Build keyRegions (normalised)
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

  // Build sections → measures → chords from analysis payload
  // Expected analysis shape (best effort from inventory):
  //   { sections: [{ id, name, section_order, measures: [{ id, measure_number, chords: [...] }] }] }
  // or as separate arrays. We try multiple paths.
  const sections = [];
  const rawSections = analysis?.sections || [];
  const rawMeasures = analysis?.measures || [];
  const rawChords = analysis?.chords || [];
  const overrideMap = new Map();
  for (const o of overrides || []) overrideMap.set(o.chord_index ?? o.chord_id, o);

  if (rawSections.length && rawSections[0]?.measures) {
    // nested form
    for (const sec of rawSections) {
      sections.push({
        id: sec.id,
        name: sec.name,
        subtitle: sec.notes || "",
        measures: (sec.measures || []).map(m => ({
          id: m.id,
          number: m.measure_number ?? m.number,
          chords: (m.chords || []).map((c, i) => transformChord(c, m.measure_number ?? m.number, keyRegions, overrideMap)),
        })),
      });
    }
  } else if (rawMeasures.length) {
    // separate-array form: group by section_id
    const bySection = new Map();
    for (const m of rawMeasures) {
      const sid = m.section_id;
      if (!bySection.has(sid)) bySection.set(sid, []);
      bySection.get(sid).push(m);
    }
    for (const sec of rawSections) {
      const ms = (bySection.get(sec.id) || []).sort((a, b) => (a.measure_number ?? 0) - (b.measure_number ?? 0));
      sections.push({
        id: sec.id, name: sec.name, subtitle: sec.notes || "",
        measures: ms.map(m => ({
          id: m.id, number: m.measure_number,
          chords: rawChords.filter(c => c.measure_id === m.id).map((c) => transformChord(c, m.measure_number, keyRegions, overrideMap)),
        })),
      });
    }
  } else if (rawChords.length) {
    // last resort: synthesize one section, one measure per chord
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
    detectedKey: normKeyCenter(analysis?.detected_key || songRow.detected_key || songRow.original_key),
    manualKeyOverride: analysis?.manual_key_override || null,
    confidence: analysis?.confidence ?? 0,
    hasXml: !!(songRow.has_raw_xml ?? songRow.raw_xml),
    hasNotes: !!songRow.has_note_data,
    hasLyrics: !!songRow.has_lyrics,
    measureCount: songRow.measure_count || sections.reduce((a, s) => a + s.measures.length, 0),
    chordCount: songRow.chord_count || sections.reduce((a, s) => a + s.measures.reduce((b, m) => b + m.chords.length, 0), 0),
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
    importHistory: [],   // populated on Audit page if needed
  };
}

function transformChord(c, measureNumber, keyRegions, overrideMap) {
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
    voicing: "",                            // NEW-BE column
    comment: c.comments || "",
    isInferred: false,                      // NEW-BE column
    isManualEdit: !!c.is_manual_edit,
    hasOverride: !!ov,
    confidence: c.confidence || 0,
    beat: c.beat_position || 1.0,
    chordIndex: c.chord_index ?? 0,
    measureNumber,
  };
}

/* ------------------------------------------------------------------ */
/* Higher-level data hooks — components read these                    */
/* ------------------------------------------------------------------ */

function useLibraryRows() {
  const api = useApi();
  return useApiQuery(
    "library:" + api.mode,
    async () => {
      if (api.mode === "mock") return window.HL_DATA.ALL_LIBRARY_ROWS;
      const data = await api.fetcher("/api/v1/songs/?limit=200");
      const rows = Array.isArray(data) ? data : (data.songs || data.results || []);
      return rows.map(beSongToLibraryRow);
    },
    [api.mode, api.token, api.base]
  );
}

function useSong(songId) {
  const api = useApi();
  return useApiQuery(
    `song:${songId}:${api.mode}`,
    async () => {
      if (api.mode === "mock") return window.HL_DATA.SONGS.find(s => s.id === songId);
      const [songRow, analysis, keyCenters, exchanges, overrides] = await Promise.all([
        api.fetcher(`/api/v1/songs/${songId}`),
        api.fetcher(`/api/v1/analysis/songs/${songId}`).catch(() => ({})),
        api.fetcher(`/api/v1/analysis/songs/${songId}/key-centers`).catch(() => null),
        api.fetcher(`/api/v1/analysis/songs/${songId}/exchanges`).catch(() => []),
        api.fetcher(`/api/v1/analysis/songs/${songId}/overrides`).catch(() => []),
      ]);
      return beAnalysisToSong(songRow, analysis, keyCenters, exchanges, overrides);
    },
    [api.mode, api.token, api.base, songId]
  );
}

function useChordVocabulary() {
  const api = useApi();
  return useApiQuery(
    `vocab:${api.mode}`,
    async () => {
      if (api.mode === "mock") return window.HL_DATA.CHORD_QUALITIES;
      const data = await api.fetcher("/api/v1/vocabulary/chord-symbols");
      // Transform to prototype shape if needed
      return Array.isArray(data) ? data : (data.qualities || data.results || window.HL_DATA.CHORD_QUALITIES);
    },
    [api.mode, api.token, api.base]
  );
}

/* ------------------------------------------------------------------ */
/* Helper for write paths: short-circuit in live mode                 */
/* ------------------------------------------------------------------ */
function liveToastFor(api, toast, endpoint, body) {
  if (api.mode !== "live") return false;
  toast("Live mode is read-only", { meta: `${endpoint} · would write in HM44`, kind: "info" });
  return true;
}

/* ------------------------------------------------------------------ */
/* exports                                                            */
/* ------------------------------------------------------------------ */
Object.assign(window, {
  HLApiProvider: ApiProvider,
  hlUseApi: useApi,
  hlUseApiQuery: useApiQuery,
  hlUseLibraryRows: useLibraryRows,
  hlUseSong: useSong,
  hlUseChordVocabulary: useChordVocabulary,
  hlLiveToastFor: liveToastFor,
  HL_DEFAULT_BASE: DEFAULT_BASE,
});
