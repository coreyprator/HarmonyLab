/* =====================================================================
   HarmonyLab — App shell + router (HM44.1 live app)
   Mock mode, PrototypeBanner, ModeDialog removed.
   ===================================================================== */

const { useState: useStateApp, useEffect: useEffectApp, useCallback: useCallbackApp } = React;

function AppShell() {
  const [route, setRoute] = useStateApp(() => hlParseHash() || { name: "library" });
  useEffectApp(() => {
    const onHash = () => setRoute(hlParseHash() || { name: "library" });
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = useCallbackApp((next) => {
    window.location.hash = hlEncodeRoute(next);
  }, []);

  // Load prefs from localStorage (server sync happens inside Settings)
  const [prefs, setPrefsState] = useStateApp(() => {
    const ls = hlLoadState();
    return ls.prefs || {
      chordMode: "jazz",
      keyColors: { ...window.HL_DATA.KEY_COLOR_DEFAULTS },
      debugMode: false,
    };
  });
  const setPrefs = useCallbackApp((p) => { setPrefsState(p); hlSaveState({ prefs: p }); }, []);

  // Live-apply key-center colors
  useEffectApp(() => {
    const map = {
      "C maj":"--k-C", "G maj":"--k-G", "D maj":"--k-D", "A maj":"--k-A",
      "E maj":"--k-E", "B maj":"--k-B", "F# maj":"--k-Fs", "F maj":"--k-F",
      "Bb maj":"--k-Bb", "Eb maj":"--k-Eb", "Ab maj":"--k-Ab", "Db maj":"--k-Db",
    };
    for (const [k, css] of Object.entries(map)) {
      const val = prefs.keyColors?.[k];
      if (val) document.documentElement.style.setProperty(css, val);
    }
  }, [prefs.keyColors]);

  const { items, push, dismiss } = hlUseToasts();

  let view = null;
  switch (route.name) {
    case "library":
      view = <HLLibrary route={route} onNavigate={navigate} prefs={prefs} toast={push} />;
      break;
    case "song":
      view = <SongRoute songId={route.id} route={route} navigate={navigate} prefs={prefs} toast={push} />;
      break;
    case "audit":
      view = <AuditRoute songId={route.id} route={route} navigate={navigate} toast={push} />;
      break;
    case "settings":
      view = <HLSettings route={route} onNavigate={navigate} prefs={prefs} setPrefs={setPrefs} toast={push} />;
      break;
    case "lab":
      view = <HLLab route={route} onNavigate={navigate} toast={push} />;
      break;
    default:
      view = <NotFound onHome={() => navigate({ name: "library" })} message="Unknown route" />;
  }

  return (
    <>
      <div className="staff-edge" aria-hidden="true"></div>
      {view}
      <HLToast items={items} onDismiss={dismiss} />
    </>
  );
}

/* SongRoute — fetch + render */
function SongRoute({ songId, route, navigate, prefs, toast }) {
  const { data: song, loading, error } = hlUseSong(songId);
  if (loading) return <LoadingShell><HLLoadingState what={`song #${songId}`} /></LoadingShell>;
  if (error) return <LoadingShell><HLErrorState error={error} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Song #${songId} not found.`} />;
  return <HLSongDetail song={song} route={route} onNavigate={navigate} toast={toast} prefs={prefs} />;
}

/* AuditRoute — fetch + render */
function AuditRoute({ songId, route, navigate, toast }) {
  const { data: song, loading, error } = hlUseSong(songId);
  if (loading) return <LoadingShell><HLLoadingState what={`audit #${songId}`} /></LoadingShell>;
  if (error) return <LoadingShell><HLErrorState error={error} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Song #${songId} not found.`} />;
  return <HLAudit song={song} route={route} onNavigate={navigate} toast={toast} />;
}

function LoadingShell({ children }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={{ name: "" }} onNavigate={() => {}} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>{children}</div>
    </div>
  );
}

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

/* Mount */
const _root = ReactDOM.createRoot(document.getElementById("root"));
_root.render(<ApiProvider><AppShell /></ApiProvider>);
