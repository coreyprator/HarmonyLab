/* =====================================================================
   HarmonyLab — App shell + router (HM44.1 live app)
   Mock mode, PrototypeBanner, ModeDialog removed.
   ===================================================================== */

import React from 'react';
import { ApiProvider, parseHash, encodeRoute, useSong, hlUseToasts, hlLoadState, hlSaveState } from './api.jsx';
import { KEY_COLOR_DEFAULTS } from './data.jsx';
import { Toast, Topbar } from './components.jsx';
import { Library, Settings, Lab, Audit } from './views.jsx';
import { SongDetail } from './song.jsx';

/* Inline loading/error states */
function LoadingState({ what }) {
  return <div style={{ color: 'var(--ink-2)', fontSize: 14, padding: '24px 0' }}>Loading {what}…</div>;
}
function ErrorState({ error }) {
  return <div style={{ color: 'var(--rose)', fontSize: 14, padding: '24px 0' }}>Error: {error?.message || String(error)}</div>;
}

const { useState: useStateApp, useEffect: useEffectApp, useCallback: useCallbackApp } = React;

export function AppShell() {
  const [route, setRoute] = useStateApp(() => parseHash() || { name: "library" });
  useEffectApp(() => {
    const onHash = () => setRoute(parseHash() || { name: "library" });
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const navigate = useCallbackApp((next) => {
    window.location.hash = encodeRoute(next);
  }, []);

  // Load prefs from localStorage (server sync happens inside Settings)
  const [prefs, setPrefsState] = useStateApp(() => {
    const ls = hlLoadState();
    return ls.prefs || {
      chordMode: "jazz",
      keyColors: { ...KEY_COLOR_DEFAULTS },
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
      view = <Library route={route} onNavigate={navigate} prefs={prefs} toast={push} />;
      break;
    case "song":
      view = <SongRoute songId={route.id} route={route} navigate={navigate} prefs={prefs} toast={push} />;
      break;
    case "audit":
      view = <AuditRoute songId={route.id} route={route} navigate={navigate} toast={push} />;
      break;
    case "settings":
      view = <Settings route={route} onNavigate={navigate} prefs={prefs} setPrefs={setPrefs} toast={push} />;
      break;
    case "lab":
      view = <Lab route={route} onNavigate={navigate} toast={push} />;
      break;
    default:
      view = <NotFound onHome={() => navigate({ name: "library" })} message="Unknown route" />;
  }

  return (
    <>
      <div className="staff-edge" aria-hidden="true"></div>
      {view}
      <Toast items={items} onDismiss={dismiss} />
    </>
  );
}

/* SongRoute — fetch + render */
function SongRoute({ songId, route, navigate, prefs, toast }) {
  const { data: song, loading, error } = useSong(songId);
  if (loading) return <LoadingShell><LoadingState what={`song #${songId}`} /></LoadingShell>;
  if (error) return <LoadingShell><ErrorState error={error} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Song #${songId} not found.`} />;
  return <SongDetail song={song} route={route} onNavigate={navigate} toast={toast} prefs={prefs} />;
}

/* AuditRoute — fetch + render */
function AuditRoute({ songId, route, navigate, toast }) {
  const { data: song, loading, error } = useSong(songId);
  if (loading) return <LoadingShell><LoadingState what={`audit #${songId}`} /></LoadingShell>;
  if (error) return <LoadingShell><ErrorState error={error} /></LoadingShell>;
  if (!song) return <NotFound onHome={() => navigate({ name: "library" })} message={`Song #${songId} not found.`} />;
  return <Audit song={song} route={route} onNavigate={navigate} toast={toast} />;
}

function LoadingShell({ children }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <Topbar route={{ name: "" }} onNavigate={() => {}} />
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

