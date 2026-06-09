/* =====================================================================
   HarmonyLab interactive prototype — Live-mode UI
   Toggle + token paste + top banner + mode dialog
   ===================================================================== */

const { useState: useStateL, useEffect: useEffectL, useRef: useRefL } = React;

/* ---------------------------------------------------------------------
   LiveBanner — top-of-page banner when live mode is on
   --------------------------------------------------------------------- */
function LiveBanner({ onChangeMode }) {
  const api = hlUseApi();
  if (api.mode !== "live") return null;
  return (
    <div style={{
      background: "linear-gradient(90deg, oklch(.42 .15 25 / .55), oklch(.32 .12 25 / .55))",
      color: "var(--ink-0)",
      padding: "6px 16px",
      display: "flex", alignItems: "center", gap: 12,
      fontFamily: "var(--t-mono)", fontSize: 11, letterSpacing: ".06em",
      borderBottom: "1px solid oklch(.55 .15 25 / .6)",
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--rose)", boxShadow: "0 0 0 3px oklch(.55 .15 25 / .35)" }}></span>
      <span style={{ textTransform: "uppercase" }}>LIVE DATA · READ-ONLY</span>
      <span style={{ color: "oklch(.85 .04 25)" }}>mutations stay local · read-only</span>
      <span style={{ marginLeft: "auto", color: "oklch(.85 .04 25)" }}>{api.base}</span>
      <button className="btn btn--ghost btn--sm" style={{ height: 22, padding: "0 8px", color: "var(--ink-0)" }} onClick={onChangeMode}>change mode</button>
    </div>
  );
}

/* ---------------------------------------------------------------------
   ModeToggle — single button in the topbar, opens ModeDialog
   --------------------------------------------------------------------- */
function ModeToggle({ onOpen }) {
  const api = hlUseApi();
  const isLive = api.mode === "live";
  return (
    <button
      className="btn btn--sm"
      onClick={onOpen}
      style={{
        borderColor: isLive ? "var(--rose)" : "var(--line)",
        color: isLive ? "var(--rose)" : "var(--ink-1)",
        fontFamily: "var(--t-mono)", fontSize: 10, letterSpacing: ".08em", textTransform: "uppercase",
        height: 24, padding: "0 8px",
      }}
      title={isLive ? "Live data mode · click to change" : "Mock data mode · click to switch"}
    >
      <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: isLive ? "var(--rose)" : "var(--green)", marginRight: 6 }}></span>
      {isLive ? "Live" : "Mock"}
    </button>
  );
}

/* ---------------------------------------------------------------------
   ModeDialog — switch modes, paste/clear token, change base URL
   --------------------------------------------------------------------- */
function ModeDialog({ open, onClose }) {
  const api = hlUseApi();
  const [token, setToken] = useStateL(api.token || "");
  const [base, setBase] = useStateL(api.base || "");
  const [mode, setMode] = useStateL(api.mode);

  useEffectL(() => {
    if (open) {
      setToken(api.token || "");
      setBase(api.base || "");
      setMode(api.mode);
    }
  }, [open, api.token, api.base, api.mode]);

  if (!open) return null;

  const onSave = () => {
    api.setBase(base);
    api.setToken(token.trim());
    api.setMode(mode);
    onClose();
  };
  const onReset = () => {
    api.setToken("");
    api.setMode("mock");
    onClose();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "oklch(0.09 0.005 70 / .78)", zIndex: 900, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={onClose}>
      <div style={{ width: 600, maxHeight: "90vh", overflow: "auto", background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: 8, boxShadow: "var(--sh-3)" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center" }}>
          <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22 }}>Data mode</div>
          <button className="btn btn--ghost btn--sm" style={{ marginLeft: "auto" }} onClick={onClose}>✕</button>
        </div>
        <div style={{ padding: "20px" }}>
          <div className="tiny upper" style={{ color: "var(--ink-3)" }}>Source</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 8 }}>
            <button
              className="btn"
              style={{ height: "auto", padding: "14px", textAlign: "left", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4, borderColor: mode === "mock" ? "var(--amber)" : "var(--line)", background: mode === "mock" ? "oklch(0.79 0.13 75 / .08)" : "var(--bg-2)" }}
              onClick={() => setMode("mock")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)" }}></span>
                <span style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 17, color: "var(--ink-0)" }}>Mock</span>
              </div>
              <div className="tiny" style={{ color: "var(--ink-2)", textTransform: "none", letterSpacing: 0, lineHeight: 1.4 }}>5 hand-curated songs · all writes persist to localStorage · full interaction</div>
            </button>
            <button
              className="btn"
              style={{ height: "auto", padding: "14px", textAlign: "left", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4, borderColor: mode === "live" ? "var(--rose)" : "var(--line)", background: mode === "live" ? "oklch(.55 .15 25 / .12)" : "var(--bg-2)" }}
              onClick={() => setMode("live")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--rose)" }}></span>
                <span style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 17, color: "var(--ink-0)" }}>Live · read-only</span>
              </div>
              <div className="tiny" style={{ color: "var(--ink-2)", textTransform: "none", letterSpacing: 0, lineHeight: 1.4 }}>PL's 42-song library · GET only · writes show "HM44 wires this" toast</div>
            </button>
          </div>

          {mode === "live" && (
            <>
              <div className="tiny upper" style={{ color: "var(--ink-3)", marginTop: 24 }}>Backend origin</div>
              <input
                className="input"
                value={base}
                onChange={(e) => setBase(e.target.value)}
                style={{ width: "100%", marginTop: 6, fontFamily: "var(--t-mono)", fontSize: 12 }}
                placeholder={HL_DEFAULT_BASE}
              />
              <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 4 }}>Default: <code>{HL_DEFAULT_BASE}</code>. Override only if testing against another deployment.</div>
              {api.lastError && (
                <div style={{ marginTop: 12, padding: "8px 12px", border: "1px solid var(--rose)", borderRadius: 4, background: "oklch(.55 .15 25 / .12)", color: "var(--ink-0)", fontSize: 12 }}>
                  <strong style={{ color: "var(--rose)" }}>Last error</strong> · {api.lastError.message}
                  <div className="tiny" style={{ color: "var(--ink-2)", marginTop: 4 }}>path: {api.lastError.path}</div>
                </div>
              )}
            </>
          )}
        </div>
        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-0)" }}>
          <button className="btn btn--ghost btn--sm" onClick={onReset}>Reset to mock</button>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn--primary" onClick={onSave}>
              {mode === "live" ? "Go live" : "Use mock data"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   LoadingState — placeholder shown while live queries are in flight
   --------------------------------------------------------------------- */
function LoadingState({ what }) {
  return (
    <div style={{ padding: 32, textAlign: "center", color: "var(--ink-2)", fontFamily: "var(--t-mono)", fontSize: 12, letterSpacing: ".08em", textTransform: "uppercase" }}>
      <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "var(--amber)", animation: "hl-pulse 1.2s ease-in-out infinite", marginRight: 10, verticalAlign: "middle" }}></span>
      loading {what}…
    </div>
  );
}

/* ---------------------------------------------------------------------
   ErrorState — shown on a fetch failure in live mode
   --------------------------------------------------------------------- */
function ErrorState({ error, onChangeMode, onRetry }) {
  const isAuth = error?.kind === "auth";
  return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div className="tiny upper" style={{ color: "var(--rose)" }}>{isAuth ? "Token rejected" : "Couldn't reach backend"}</div>
      <h3 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 28, margin: "8px 0 12px", fontWeight: 500 }}>
        {isAuth ? "Paste a fresh JWT." : "Network or CORS error."}
      </h3>
      <p style={{ color: "var(--ink-1)", fontSize: 13, maxWidth: 560, margin: "0 auto 16px" }}>
        {error?.message}
      </p>
      <div style={{ display: "flex", justifyContent: "center", gap: 8 }}>
        {onRetry && <button className="btn btn--ghost" onClick={onRetry}>Retry</button>}
        <button className="btn btn--primary" onClick={onChangeMode}>{isAuth ? "Paste new token" : "Change mode"}</button>
      </div>
      {!isAuth && (
        <details style={{ marginTop: 16, textAlign: "left", maxWidth: 560, marginLeft: "auto", marginRight: "auto" }}>
          <summary className="tiny upper" style={{ color: "var(--ink-blue)", cursor: "pointer" }}>Common causes</summary>
          <ul style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.7, paddingLeft: 18 }}>
            <li>CORS not yet allowlisted on the backend for this origin. CC adds <code>{location.origin}</code> to FastAPI <code>allow_origins</code>.</li>
            <li>Backend offline or domain misconfigured. Try <a style={{ color: "var(--ink-blue)" }} href={HL_DEFAULT_BASE + "/health"} target="_blank" rel="noopener">/health</a>.</li>
            <li>Path mismatch with this prototype's expected routes.</li>
          </ul>
        </details>
      )}
    </div>
  );
}

Object.assign(window, {
  HLLiveBanner: LiveBanner,
  HLModeToggle: ModeToggle,
  HLModeDialog: ModeDialog,
  HLLoadingState: LoadingState,
  HLErrorState: ErrorState,
});
