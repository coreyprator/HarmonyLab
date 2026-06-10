/* =====================================================================
   HarmonyLab interactive prototype — top-level App + router
   ===================================================================== */

const { useState: useStateApp, useEffect: useEffectApp, useCallback: useCallbackApp } = React;

function AppShell() {
  /* ---- routing (in-memory, also persisted to hash) ---- */
  const [route, setRoute] = useStateApp(() => parseHash() || { name: "library" });
  useEffectApp(() => {
    const onHash = () => setRoute(parseHash() || { name: "library" });
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = useCallbackApp((next) => {
    window.location.hash = encodeRoute(next);
  }, []);

  /* ---- prefs (persisted) ---- */
  const [prefs, setPrefsState] = useStateApp(() => {
    const ls = hlLoadState();
    return ls.prefs || {
      chordMode: "jazz",
      keyColors: { ...window.HL_DATA.KEY_COLOR_DEFAULTS },
      debugMode: false,
    };
  });
  const setPrefs = useCallbackApp((p) => { setPrefsState(p); hlSaveState({ prefs: p }); }, []);

  /* ---- live apply key-color prefs to :root variables ---- */
  useEffectApp(() => {
    const map = {
      "C maj":  "--k-C",  "G maj": "--k-G",  "D maj": "--k-D",  "A maj": "--k-A",
      "E maj":  "--k-E",  "B maj": "--k-B",  "F# maj":"--k-Fs", "F maj": "--k-F",
      "Bb maj": "--k-Bb", "Eb maj":"--k-Eb", "Ab maj":"--k-Ab", "Db maj":"--k-Db",
    };
    for (const [k, css] of Object.entries(map)) {
      const val = prefs.keyColors?.[k];
      if (val) document.documentElement.style.setProperty(css, val);
    }
  }, [prefs.keyColors]);

  /* ---- toasts ---- */
  const { items, push, dismiss } = hlUseToasts();

  /* ---- live mode dialog state ---- */
  const [modeDialogOpen, setModeDialogOpen] = useStateApp(false);
  // HM44 Phase B: no auth — do not force open mode dialog on first load
  const api = hlUseApi();

  /* ---- render route ---- */
  let view = null;
  switch (route.name) {
    case "library":
      view = <HLLibrary route={route} onNavigate={navigate} prefs={prefs} toast={push} onOpenMode={() => setModeDialogOpen(true)} />;
      break;
    case "song":
      view = <SongRoute songId={route.id} route={route} navigate={navigate} prefs={prefs} toast={push} onOpenMode={() => setModeDialogOpen(true)} />;
      break;
    case "audit":
      view = <AuditRoute songId={route.id} route={route} navigate={navigate} toast={push} onOpenMode={() => setModeDialogOpen(true)} />;
      break;
    case "settings":
      view = <HLSettings route={route} onNavigate={navigate} prefs={prefs} setPrefs={setPrefs} toast={push} onOpenMode={() => setModeDialogOpen(true)} />;
      break;
    case "lab":
      view = <HLLab route={route} onNavigate={navigate} toast={push} onOpenMode={() => setModeDialogOpen(true)} />;
      break;
    default:
      view = <NotFound onHome={() => navigate({ name: "library" })} message="Unknown route" />;
  }

  return (
    <>
      <div className="staff-edge" aria-hidden="true"></div>
      <HLLiveBanner onChangeMode={() => setModeDialogOpen(true)} />
      {view}
      <HLToast items={items} onDismiss={dismiss} />
      <PrototypeBanner onOpenMode={() => setModeDialogOpen(true)} />
      <HLModeDialog open={modeDialogOpen} onClose={() => setModeDialogOpen(false)} />
    </>
  );
}

/* ---------------------------------------------------------------------
   SongRoute — fetch + render
   --------------------------------------------------------------------- */
function SongRoute({ songId, route, navigate, prefs, toast, onOpenMode }) {
  const api = hlUseApi();
  const { data: song, loading, error } = hlUseSong(songId);

  if (api.mode === "live" && loading) return <LoadingShell onOpenMode={onOpenMode}><HLLoadingState what={`song #${songId}`} /></LoadingShell>;
  if (api.mode === "live" && error) return <LoadingShell onOpenMode={onOpenMode}><HLErrorState error={error} onChangeMode={onOpenMode} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Song #${songId} not in prototype dataset. Try one of the five hand-curated songs from /library.`} />;
  return <HLSongDetail song={song} route={route} onNavigate={navigate} toast={toast} prefs={prefs} onOpenMode={onOpenMode} />;
}

function AuditRoute({ songId, route, navigate, toast, onOpenMode }) {
  const api = hlUseApi();
  const { data: song, loading, error } = hlUseSong(songId);
  if (api.mode === "live" && loading) return <LoadingShell onOpenMode={onOpenMode}><HLLoadingState what={`audit for #${songId}`} /></LoadingShell>;
  if (api.mode === "live" && error) return <LoadingShell onOpenMode={onOpenMode}><HLErrorState error={error} onChangeMode={onOpenMode} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Audit for song #${songId} not in prototype.`} />;
  // Audit page expects importHistory; live mode populates empty array via transform
  return <HLAudit song={song} route={route} onNavigate={navigate} toast={toast} onOpenMode={onOpenMode} />;
}

function LoadingShell({ onOpenMode, children }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={{ name: "" }} onNavigate={() => {}} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        {children}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   NotFound
   --------------------------------------------------------------------- */
function NotFound({ onHome, message }) {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
      <div className="tiny upper" style={{ color: "var(--amber)" }}>Not found</div>
      <h2 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 36, margin: 0 }}>Lost the thread.</h2>
      <p style={{ color: "var(--ink-2)", fontSize: 14, maxWidth: 480, textAlign: "center" }}>{message}</p>
      <button className="btn btn--primary" onClick={onHome}>← Back to library</button>
    </div>
  );
}

/* ---------------------------------------------------------------------
   Floating banner labeling this as a prototype
   --------------------------------------------------------------------- */
function PrototypeBanner({ onOpenMode }) {
  const [open, setOpen] = useStateApp(true);
  const api = hlUseApi();
  if (!open) return null;
  return (
    <div style={{
      position: "fixed", right: 16, bottom: 16, zIndex: 50,
      background: "var(--bg-2)", border: "1px solid var(--line-2)",
      borderRadius: 6, padding: "10px 14px", boxShadow: "var(--sh-2)",
      fontSize: 12, color: "var(--ink-1)", maxWidth: 340, lineHeight: 1.5,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4, gap: 8 }}>
        <span className="tiny upper" style={{ color: "var(--amber)" }}>Prototype · for CAI handoff</span>
        <HLModeToggle onOpen={onOpenMode} />
        <button className="btn btn--ghost btn--sm" style={{ padding: "0 6px", height: 18 }} onClick={() => setOpen(false)}>✕</button>
      </div>
      {api.mode === "mock"
        ? <>Click any chord cell to edit. ✎ key to override. Inferred chords (Corcovado m.1–2) accept-on-click.</>
        : <>Read-only against {api.base}. Writes show "HM44 wires this" toasts. NEW-BE-flagged UI keeps mock behavior.</>
      }
      <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 6, fontFamily: "var(--t-mono)" }}>
        Edits persist to localStorage · clear via ⌃⇧K
      </div>
    </div>
  );
}

/* keyboard: clear localStorage on Ctrl+Shift+K */
window.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "k") {
    if (confirm("Clear prototype state? (resets all chord edits + prefs)")) {
      localStorage.removeItem("harmonylab_prototype_state_v1");
      location.reload();
    }
  }
});

/* ---------------------------------------------------------------------
   route helpers
   --------------------------------------------------------------------- */
function parseHash() {
  const h = location.hash.replace(/^#\/?/, "");
  if (!h) return null;
  const [name, ...rest] = h.split("/");
  const id = rest[0] ? parseInt(rest[0], 10) : undefined;
  return { name, id };
}
function encodeRoute(r) {
  if (r.id != null) return `#/${r.name}/${r.id}`;
  return `#/${r.name}`;
}

/* ---------------------------------------------------------------------
   mount
   --------------------------------------------------------------------- */
function App() {
  return (
    <HLApiProvider>
      <AppShell />
    </HLApiProvider>
  );
}
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
