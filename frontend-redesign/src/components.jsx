/* =====================================================================
   HarmonyLab interactive prototype — shared components
   Reuses redesign.css classes; no inline styles object collisions.
   ===================================================================== */

const { useState, useEffect, useRef, useMemo, useCallback } = React;

/* ---------------------------------------------------------------------
   Toast — bottom centre, dismisses after 4s
   --------------------------------------------------------------------- */
function Toast({ items, onDismiss }) {
  return (
    <div style={{ position: "fixed", left: "50%", transform: "translateX(-50%)", bottom: 28, zIndex: 1000, display: "flex", flexDirection: "column", gap: 8, pointerEvents: "none" }}>
      {items.map((t) =>
      <div key={t.id} className="float-toast" style={{ position: "static", transform: "none", pointerEvents: "auto", minWidth: 320 }}>
          <span className="dot" style={{ background: t.kind === "error" ? "var(--rose)" : "var(--green)" }}></span>
          <span>{t.text}</span>
          {t.meta && <span className="tiny" style={{ marginLeft: 8, color: "var(--ink-3)" }}>{t.meta}</span>}
          <button className="btn btn--ghost btn--sm" style={{ marginLeft: 8, padding: "0 6px" }} onClick={() => onDismiss(t.id)}>✕</button>
        </div>
      )}
    </div>);

}

/* toast hook */
let __toastId = 0;
function useToasts() {
  const [items, setItems] = useState([]);
  const push = useCallback((text, opts = {}) => {
    const id = ++__toastId;
    setItems((xs) => [...xs, { id, text, ...opts }]);
    setTimeout(() => setItems((xs) => xs.filter((t) => t.id !== id)), opts.duration || 4500);
  }, []);
  const dismiss = useCallback((id) => setItems((xs) => xs.filter((t) => t.id !== id)), []);
  return { items, push, dismiss };
}

/* ---------------------------------------------------------------------
   ChordCell — the central editable primitive
   --------------------------------------------------------------------- */
function ChordCell({ chord, mode, selected, onClick, onPromoteInferred }) {
  // mode: "chords" | "analysis"
  const k = hlKeyCss(chord.keyCenter);
  const classes = [
  "chord-cell",
  k,
  chord.isInferred && "is-inferred",
  chord.isManualEdit && "is-edited",
  chord.comment && "has-comment",
  selected && "is-selected"].
  filter(Boolean).join(" ");

  if (mode === "analysis") {
    return (
      <div className={classes} onClick={onClick} style={{ padding: "14px 14px 16px" }}>
        <div className="key-strip"></div>
        <div className="meas">m.{chord.measureNumber}{chord.isInferred ? " inf" : ""}</div>
        <div style={{ fontFamily: "var(--t-roman)", fontStyle: "italic", fontSize: 26, color: chord.isInferred ? "var(--ink-1)" : "var(--ink-0)", textTransform: chord.romanCase === "minor" ? "lowercase" : "uppercase" }}>
          {chord.roman}{chord.superscript && <sup>{chord.superscript}</sup>}
        </div>
        <div style={{ fontFamily: "var(--t-chord)", fontSize: 14, color: "var(--ink-2)", marginTop: 2 }}>{chord.symbol}</div>
        <div style={{ marginTop: "auto" }}>
          <span className="pill" style={{ fontSize: 10, padding: "2px 6px", color: chord.isInferred ? "var(--ink-3)" : "var(--ink-1)" }}>{chord.function}</span>
        </div>
      </div>);

  }

  return (
    <div className={classes} onClick={onClick}>
      <div className="key-strip"></div>
      <div className="meas">m.{chord.measureNumber}{chord.isInferred ? " · pickup" : ""}</div>
      <div className="sym">{chord.symbol}</div>
      <div className={"roman " + chord.romanCase}>
        {chord.roman}{chord.superscript && <sup>{chord.superscript}</sup>}
      </div>
      {chord.voicing && <div className="voicing">{chord.voicing}</div>}
      <div className="func">{chord.function}</div>
      {chord.isInferred && onPromoteInferred &&
      <button
        className="btn btn--sm"
        style={{ position: "absolute", right: 8, bottom: 8, height: 20, padding: "0 6px", fontSize: 10, color: "var(--ink-blue)", borderColor: "var(--ink-blue)" }}
        onClick={(e) => {e.stopPropagation();onPromoteInferred(chord);}}
        title="Accept as composer-written">
        accept ↩</button>
      }
    </div>);

}

/* ---------------------------------------------------------------------
   ChordPicker — root × quality dropdown from /vocabulary/chord-symbols
   - filterable search field
   - virtual list (~510 combinations, but visible subset)
   - keyboard nav
   --------------------------------------------------------------------- */
function ChordPicker({ value, onChange, onCommit, invalid }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [hi, setHi] = useState(0);
  const wrapRef = useRef(null);
  const listRef = useRef(null);

  // parse value into root + suffix for matching
  const parsed = useMemo(() => {
    const m = value.match(/^([A-G][♯♭#b]?)(.*)$/);
    return m ? { root: m[1], suffix: m[2] } : { root: "C", suffix: "" };
  }, [value]);

  // build the candidate list — root × quality combinations
  // filter strategy: if "Cm7" typed, match by root+suffix; if "m7" typed, match by suffix only
  const candidates = useMemo(() => {
    const qs = window.HL_DATA.CHORD_QUALITIES;
    const roots = window.HL_DATA.ROOT_NOTES;
    const out = [];
    for (const r of roots) {
      for (const q of qs) {
        const sym = r + q.displayJazz;
        out.push({ symbol: sym, root: r, quality: q });
      }
    }
    if (!filter.trim()) {
      // sort by relevance to current value
      out.sort((a, b) => {
        const aMatch = a.root === parsed.root ? 0 : a.root.startsWith(parsed.root) ? 1 : 2;
        const bMatch = b.root === parsed.root ? 0 : b.root.startsWith(parsed.root) ? 1 : 2;
        return aMatch - bMatch;
      });
      return out;
    }
    const f = filter.toLowerCase().replace(/♯/g,"#").replace(/♭/g,"b");
    return out.filter(c => {
      const s = c.symbol.toLowerCase().replace(/♯/g,"#").replace(/♭/g,"b");
      if (s.startsWith(f)) return true;
      // also match by quality aliases
      const aliasHit = c.quality.aliases.some(a => (c.root + a).toLowerCase().startsWith(f) || a.toLowerCase().startsWith(f));
      return aliasHit;
    }).slice(0, 80);
  }, [filter, parsed]);

  // close on outside click
  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const pick = (cand) => {
    onChange(cand.symbol);
    setOpen(false);
    setFilter("");
  };

  const onKey = (e) => {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true); e.preventDefault(); return;
    }
    if (open) {
      if (e.key === "ArrowDown") { e.preventDefault(); setHi(h => Math.min(h + 1, candidates.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setHi(h => Math.max(h - 1, 0)); }
      else if (e.key === "Enter") {
        e.preventDefault();
        if (candidates[hi]) pick(candidates[hi]);
        else if (onCommit) onCommit();
      }
      else if (e.key === "Escape") { setOpen(false); e.preventDefault(); }
    }
  };

  // scroll highlighted into view
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-hi="${hi}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }, [hi, open]);

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      <div
        className="input"
        style={{
          display: "flex", alignItems: "center", gap: 6,
          fontFamily: "var(--t-chord)", fontSize: 16,
          borderColor: invalid ? "var(--rose)" : (open ? "var(--amber)" : ""),
          cursor: "pointer", padding: "0 8px",
        }}
        tabIndex={0}
        onClick={() => setOpen(o => !o)}
        onKeyDown={onKey}
      >
        <span style={{ flex: 1 }}>{value}</span>
        <span className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>▾</span>
      </div>
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0,
          zIndex: 20,
          background: "var(--bg-2)",
          border: "1px solid var(--line-2)",
          borderRadius: 4,
          boxShadow: "var(--sh-3)",
          padding: 6,
        }}>
          <input
            autoFocus
            className="input"
            placeholder="Type a chord (Cm7, F♯7♭9, …)"
            value={filter}
            onChange={e => { setFilter(e.target.value); setHi(0); }}
            onKeyDown={onKey}
            style={{ width: "100%", height: 26, fontFamily: "var(--t-chord)", fontSize: 14 }}
          />
          <div ref={listRef} style={{ maxHeight: 220, overflow: "auto", marginTop: 6 }}>
            {candidates.length === 0 && (
              <div className="tiny" style={{ color: "var(--ink-3)", padding: 12, textAlign: "center" }}>No matches in ChordVocabulary</div>
            )}
            {candidates.map((c, i) => (
              <div
                key={c.symbol}
                data-hi={i}
                onMouseEnter={() => setHi(i)}
                onClick={() => pick(c)}
                style={{
                  display: "flex", alignItems: "baseline", gap: 10,
                  padding: "5px 8px",
                  borderRadius: 3,
                  background: i === hi ? "var(--bg-3)" : "transparent",
                  cursor: "pointer",
                }}
              >
                <span style={{ fontFamily: "var(--t-chord)", fontSize: 15, minWidth: 70, color: "var(--ink-0)" }}>{c.symbol}</span>
                <span className="tiny" style={{ color: "var(--ink-2)" }}>{c.quality.type}</span>
                <span className="tiny" style={{ color: "var(--ink-3)", marginLeft: "auto", fontFamily: "var(--t-mono)" }}>{c.quality.intervals}</span>
              </div>
            ))}
          </div>
          <div className="tiny" style={{ color: "var(--ink-3)", padding: "6px 8px 2px", borderTop: "1px solid var(--line)", marginTop: 4, fontFamily: "var(--t-mono)" }}>
            GET /api/v1/vocabulary/chord-symbols · {window.HL_DATA.CHORD_QUALITIES.length} qualities × {window.HL_DATA.ROOT_NOTES.length} roots
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   ChordEditPopover — opens beneath an edited chord
   --------------------------------------------------------------------- */
const COMMON_SYMBOLS = ["△7", "m7", "7", "7♭9", "7♯9", "ø7", "°7", "alt", "m7♭5", "sus4", "6", "9", "13", "♭13"];
const FUNCTIONS = ["tonic", "predominant", "dominant", "secondary dominant", "secondary ii", "tritone sub", "plagal", "chromatic", "pivot", "modulation"];

function ChordEditPopover({ chord, anchorRect, onCommit, onCancel }) {
  const [symbol, setSymbol] = useState(chord.symbol);
  const [roman, setRoman] = useState(chord.roman + (chord.superscript ? chord.superscript : ""));
  const [func, setFunc] = useState(chord.function);
  const [voicing, setVoicing] = useState(chord.voicing || "");
  const [comment, setComment] = useState(chord.comment || "");
  const [invalid, setInvalid] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, []);

  // simple "validity" check: must contain a root letter
  useEffect(() => {setInvalid(!/^[A-G]/.test(symbol.trim()));}, [symbol]);

  const onKey = (e) => {
    if (e.key === "Escape") {e.preventDefault();onCancel();}
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!invalid) onCommit({ symbol, roman, func, voicing, comment });
    }
  };

  return (
    <div className="popover" style={{ position: "absolute", top: anchorRect.top, left: anchorRect.left, width: 340 }} onKeyDown={onKey}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 16 }}>Edit chord · m.{chord.measureNumber}</div>
        <span className="tiny" style={{ color: "var(--ink-3)" }}>id {chord.id} · 0-idx {chord.chordIndex}</span>
      </div>

      <div className="row">
        <label>symbol</label>
        <ChordPicker
          value={symbol}
          onChange={setSymbol}
          onCommit={() => !invalid && onCommit({ symbol, roman, func, voicing, comment })}
          invalid={invalid}
        />
      </div>

      <div className="row" style={{ marginTop: 10 }}>
        <label>roman</label>
        <input className="input" value={roman} onChange={(e) => setRoman(e.target.value)} style={{ fontFamily: "var(--t-roman)", fontStyle: "italic" }} />
      </div>
      <div className="row">
        <label>function</label>
        <select className="input select" value={func} onChange={(e) => setFunc(e.target.value)}>
          {FUNCTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
          {!FUNCTIONS.includes(func) && <option value={func}>{func}</option>}
        </select>
      </div>
      <div className="row">
        <label>voicing {window.hlUseApi?.().mode === "live" && <span className="tiny" style={{ color: "var(--rose)", textTransform: "none", letterSpacing: 0, marginLeft: 4 }}>· mock</span>}</label>
        <input className="input" value={voicing} onChange={(e) => setVoicing(e.target.value)} placeholder="e.g. rootless A · drop-2" title="HM44 adds Chords.voicing_notation column" />
      </div>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <label style={{ paddingTop: 5 }}>comment</label>
        <textarea
          className="input"
          rows={2}
          style={{ height: "auto", padding: "6px 10px", resize: "vertical" }}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="free text…" />
        
      </div>

      <div className="actions">
        <span className="tiny" style={{ marginRight: "auto", color: "var(--ink-3)" }}>
          PUT /chords/{chord.id}
          <br />
          PUT /analysis/.../chord/{chord.chordIndex}
        </span>
        <button className="btn btn--ghost btn--sm" onClick={onCancel}>Cancel <span className="kbd">Esc</span></button>
        <button
          className="btn btn--primary btn--sm"
          disabled={invalid}
          style={invalid ? { opacity: 0.5, cursor: "not-allowed" } : {}}
          onClick={() => onCommit({ symbol, roman, func, voicing, comment })}>
          Save <span className="kbd">⏎</span></button>
      </div>
    </div>);

}

/* ---------------------------------------------------------------------
   KeyOverridePopover — circle of fifths
   --------------------------------------------------------------------- */
const CIRCLE_OF_FIFTHS = [
"C maj", "G maj", "D maj", "A maj", "E maj", "B maj",
"F# maj", "Db maj", "Ab maj", "Eb maj", "Bb maj", "F maj"];

const RELATIVE_MINORS = {
  "C maj": "A min", "G maj": "E min", "D maj": "B min", "A maj": "F# min", "E maj": "C# min", "B maj": "G# min",
  "F# maj": "D# min", "Db maj": "Bb min", "Ab maj": "F min", "Eb maj": "C min", "Bb maj": "G min", "F maj": "D min"
};

function KeyPopover({ detected, manual, onPick, onClear, onClose }) {
  return (
    <div className="popover" style={{ width: 380, top: "100%", marginTop: 12, left: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 16 }}>Set song key</div>
        <button className="btn btn--ghost btn--sm" onClick={onClose}>✕</button>
      </div>
      <div className="tiny" style={{ color: "var(--ink-3)", marginBottom: 8 }}>circle of fifths · major (row 1) → relative minor (row 2)</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 4 }}>
        {CIRCLE_OF_FIFTHS.map((k) =>
        <button
          key={k}
          className="btn"
          style={{
            height: 32, fontSize: 12, padding: 0,
            borderColor: manual === k ? "var(--amber)" : "var(--line)",
            background: manual === k ? "oklch(0.79 0.13 75 / .12)" : "var(--bg-2)",
            fontWeight: manual === k ? 600 : 400
          }}
          onClick={() => onPick(k)}>
          {k.replace(" maj", "")}</button>
        )}
        {CIRCLE_OF_FIFTHS.map((k) => {
          const rel = RELATIVE_MINORS[k];
          return (
            <button
              key={rel}
              className="btn"
              style={{
                height: 32, fontSize: 12, padding: 0,
                borderColor: manual === rel ? "var(--amber)" : "var(--line)",
                background: manual === rel ? "oklch(0.79 0.13 75 / .12)" : "var(--bg-1)",
                color: "var(--ink-1)",
                fontWeight: manual === rel ? 600 : 400
              }}
              onClick={() => onPick(rel)}>
              {rel.replace(" min", "m")}</button>);

        })}
      </div>
      <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="tiny" style={{ color: "var(--ink-3)" }}>
          detected · <strong style={{ color: "var(--ink-1)" }}>{detected}</strong>
          {manual && <> · current override · <strong style={{ color: "var(--amber)" }}>{manual}</strong></>}
        </span>
        <div className="actions" style={{ margin: 0 }}>
          {manual && <button className="btn btn--ghost btn--sm" onClick={onClear}>Use detected</button>}
        </div>
      </div>
      <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 8, fontFamily: "var(--t-mono)" }}>POST /analysis/songs/&#123;id&#125;/manual-key</div>
    </div>);

}

/* ---------------------------------------------------------------------
   Topbar
   --------------------------------------------------------------------- */
function Topbar({ route, onNavigate, songTitle }) {
  return (
    <div className="app-topbar">
      <div className="app-brand" style={{ cursor: "pointer" }} onClick={() => onNavigate({ name: "library" })}>HarmonyLab</div>
      <nav className="app-nav">
        <a className={route.name === "library" ? "is-active" : ""} onClick={() => onNavigate({ name: "library" })}>Library</a>
        {songTitle && <a className={route.name === "song" || route.name === "audit" ? "is-active" : ""} onClick={() => onNavigate({ name: "song", id: route.id || route.songId })}>{songTitle}</a>}
        <a className={route.name === "settings" ? "is-active" : ""} onClick={() => onNavigate({ name: "settings" })}>Settings</a>
        <a className={route.name === "lab" ? "is-active" : ""} onClick={() => onNavigate({ name: "lab" })}>Lab</a>
      </nav>
      <div className="app-spacer"></div>
      <div className="app-meta"><span className="dot"></span>db · 42 songs · canary <code>PINEAPPLE-HM41</code></div>
      <div className="user-chip"><span className="av"></span>pl</div>
    </div>);

}

/* ---------------------------------------------------------------------
   ConfirmModal — generic
   --------------------------------------------------------------------- */
function ConfirmModal({ title, body, confirmLabel, danger, onConfirm, onCancel }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "oklch(0.09 0.005 70 / .75)", zIndex: 800, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onCancel}>
      <div style={{ width: 440, background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: 8, padding: 20, boxShadow: "var(--sh-3)" }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: 0, fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20 }}>{title}</h3>
        <p style={{ margin: "10px 0 18px", color: "var(--ink-1)", fontSize: 13 }}>{body}</p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn btn--ghost" onClick={onCancel}>Cancel</button>
          <button className={"btn " + (danger ? "btn--danger" : "btn--primary")} onClick={onConfirm}>{confirmLabel || "Confirm"}</button>
        </div>
      </div>
    </div>);

}

/* ---------------------------------------------------------------------
   AI Key-center identification dialog
   - submit selected chords → Claude → suggested key + reasoning
   - accept inserts a KeyRegion + repaints affected chord cells
   --------------------------------------------------------------------- */

/* helpers — exported below */
function suggestKeyCenter(chords) {
  const syms = chords.map(c => c.symbol).join(" ");
  // pattern-match a handful of cadences for plausible AI responses
  if (/Gm7.+G♭7.+F7.+B♭/.test(syms)) {
    return {
      key: "Bb maj", confidence: 0.93,
      pattern: "ii – ♭V/ii – V – I (tritone-sub cadence in B♭)",
      reasoning: "These four bars form an extended cadence in B♭ major. Gm7 functions as ii, G♭7 is the tritone substitute of C7 (V/V), F7♭9 is V, and B♭△7 is the tonic. The chromatic bass G → G♭ → F → B♭ is the signature of the substitution.",
    };
  }
  // shorter version of the above — resolves to F (or F minor), not B♭ — DIFFERENT key from current
  if (/Gm7.+G♭7.+F7/.test(syms)) {
    return {
      key: "F maj", confidence: 0.71,
      pattern: "ii – ♭V/ii – V (cadence to F)",
      reasoning: "Without the resolving bar, this three-chord sub-phrase sets up F as the local tonic. Gm7 acts as ii of F; G♭7 is the tritone substitute of C7 (V/V of F); F7 is V. The full B♭ reading only emerges when the next measure is included.",
    };
  }
  if (/Am7.+D7.+G/.test(syms)) {
    return { key:"G maj", confidence:0.91, pattern:"ii – V – I in G", reasoning:"Standard ii–V–I cadence resolving on G major. Am7 is ii, D7 is V, G is the tonic." };
  }
  if (/Cm7.+F7.+B♭/.test(syms)) {
    return { key:"Bb maj", confidence:0.95, pattern:"ii – V – I in B♭", reasoning:"Classic ii–V–I in B♭ major. Cm7 (ii) → F7 (V) → B♭ (I)." };
  }
  if (/Am7♭5.+D7♭9?.+Gm/.test(syms)) {
    return { key:"G min", confidence:0.92, pattern:"iiø – V7♭9 – i in G minor", reasoning:"A half-diminished ii chord plus a flat-nine altered dominant is unambiguous evidence of a minor tonic. The line resolves to G minor." };
  }
  if (/Em7♭5.+A7/.test(syms)) {
    return { key:"D min", confidence:0.89, pattern:"iiø – V7 in D minor", reasoning:"Em7♭5 is iiø of D minor; A7♭9 is its altered V. The cadence implies D minor as the active key centre." };
  }
  if (/B△7.+D7.+G△7/.test(syms)) {
    return { key:"G maj", confidence:0.85, pattern:"Coltrane cycle pivot", reasoning:"The major-third descent B → G is a Coltrane-changes pivot. While both keys are present, G major is the resolving tonic of this sub-phrase." };
  }
  // fallback — best guess is the dominant existing key
  const firstKey = chords[0]?.keyCenter || "C maj";
  return {
    key: firstKey, confidence: 0.62,
    pattern: "no strong cadential pattern",
    reasoning: `The selection does not contain a clear functional cadence (ii–V–I or its substitutions). The chords are consistent with the prevailing ${firstKey} reading; consider extending the selection or treating these bars as transitional.`
  };
}

/* merge a new region [start..end] = key into existing region list, splitting
   any overlapping region and merging adjacent same-key regions. */
function mergeKeyRegion(regions, startMeasure, endMeasure, key) {
  const result = [];
  for (const r of regions) {
    if (r.endMeasure < startMeasure || r.startMeasure > endMeasure) {
      result.push({ ...r });
      continue;
    }
    if (r.startMeasure < startMeasure) {
      result.push({ ...r, endMeasure: startMeasure - 1, weight: startMeasure - r.startMeasure });
    }
    if (r.endMeasure > endMeasure) {
      result.push({ ...r, startMeasure: endMeasure + 1, weight: r.endMeasure - endMeasure });
    }
  }
  result.push({ startMeasure, endMeasure, key, weight: endMeasure - startMeasure + 1, isUserDefined: true });
  result.sort((a, b) => a.startMeasure - b.startMeasure);
  const merged = [];
  for (const r of result) {
    const last = merged[merged.length - 1];
    if (last && last.key === r.key && last.endMeasure + 1 === r.startMeasure) {
      last.endMeasure = r.endMeasure;
      last.weight = last.endMeasure - last.startMeasure + 1;
      last.isUserDefined = last.isUserDefined || r.isUserDefined;
    } else {
      merged.push({ ...r });
    }
  }
  return merged;
}

function AIKeyCenterDialog({ open, song, selectedChords, onAccept, onReject, onCancel }) {
  const [stage, setStage] = useState("thinking");   // thinking | response
  const [suggestion, setSuggestion] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [rejecting, setRejecting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setStage("thinking");
    setSuggestion(null);
    setRejecting(false);
    setRejectReason("");
    const t = setTimeout(() => {
      setSuggestion(suggestKeyCenter(selectedChords));
      setStage("response");
    }, 1400);
    return () => clearTimeout(t);
  }, [open, selectedChords]);

  if (!open) return null;

  const measRange = selectedChords.length
    ? `m.${Math.min(...selectedChords.map(c=>c.measureNumber))} – m.${Math.max(...selectedChords.map(c=>c.measureNumber))}`
    : "";
  const kvar = suggestion ? `var(--${hlKeyCss(suggestion.key) || "k-C"})` : "var(--ink-2)";
  const currentKey = selectedChords[0]?.keyCenter || song.detectedKey;
  const changing = suggestion && suggestion.key !== currentKey;

  return (
    <div style={{ position: "fixed", inset: 0, background: "oklch(0.09 0.005 70 / .78)", zIndex: 850, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }} onClick={onCancel}>
      <div style={{ width: "100%", maxWidth: 560, maxHeight: "90vh", overflow: "auto", background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: 8, boxShadow: "var(--sh-3)" }} onClick={e => e.stopPropagation()}>
        {/* head */}
        <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--line)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal)", flexShrink: 0 }}></span>
            <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20, lineHeight: 1.1 }}>Identify key center</div>
            <button className="btn btn--ghost btn--sm" style={{ marginLeft: "auto" }} onClick={onCancel}>✕</button>
          </div>
          <div className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)", marginTop: 4 }}>{measRange} · {selectedChords.length} chord{selectedChords.length>1?"s":""}</div>
        </div>

        {/* selection summary */}
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--line)", background: "var(--bg-0)" }}>
          <div className="tiny upper" style={{ color: "var(--ink-3)", marginBottom: 8 }}>Selection · sent as context</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {selectedChords.map(c => (
              <span key={c.id} className="pill" style={{ fontFamily: "var(--t-chord)", fontSize: 14, padding: "3px 10px" }}>
                <span className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)", marginRight: 4 }}>m.{c.measureNumber}</span>
                {c.symbol}
              </span>
            ))}
          </div>
          <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 8, fontFamily: "var(--t-mono)", wordBreak: "break-all" }}>
            POST /api/v1/analysis/songs/{song.id}/ai-analysis
            <br />selected_chords={selectedChords.map(c=>c.chordIndex).join(",")}
          </div>
        </div>

        {/* body */}
        <div style={{ padding: "20px 20px" }}>
          {stage === "thinking" && (
            <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "20px 0" }}>
              <div className="pulse-dot" style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--teal)", animation: "hl-pulse 1.2s ease-in-out infinite" }}></div>
              <div>
                <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 17, color: "var(--ink-1)" }}>Claude is reading the selection…</div>
                <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 4, fontFamily: "var(--t-mono)" }}>RAG · 12 theory docs · analysis_rules in system prompt</div>
              </div>
            </div>
          )}
          {stage === "response" && suggestion && (
            <>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
                <div className="tiny upper" style={{ color: "var(--teal)" }}>claude · suggestion</div>
                <span className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>confidence {suggestion.confidence}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", border: "1px solid var(--line-2)", borderRadius: 6, background: `color-mix(in oklch, ${kvar} 12%, var(--bg-0))` }}>
                <span style={{ width: 18, height: 18, borderRadius: "50%", background: kvar, boxShadow: `0 0 0 3px color-mix(in oklch, ${kvar} 30%, transparent)` }}></span>
                <div style={{ flex: 1 }}>
                  <div className="tiny upper" style={{ color: "var(--ink-3)" }}>suggested key centre for {measRange}</div>
                  <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 24, color: kvar, lineHeight: 1.1 }}>{suggestion.key}</div>
                </div>
                {!changing && (
                  <span className="pill" style={{ fontSize: 11, color: "var(--ink-3)" }}>matches current</span>
                )}
                {changing && (
                  <span className="pill" style={{ fontSize: 11, color: "var(--amber)", borderColor: "var(--amber)" }}>
                    from {currentKey}
                  </span>
                )}
              </div>

              {window.hlUseApi?.().mode === "live" && (
                <div style={{ marginTop: 12, padding: "8px 12px", border: "1px solid var(--rose)", borderRadius: 4, background: "oklch(.55 .15 25 / .12)", fontSize: 12, color: "var(--ink-1)", fontFamily: "var(--t-mono)", letterSpacing: ".04em" }}>
                  <strong style={{ color: "var(--rose)" }}>MOCK</strong> · HM44 adds <code>POST /analysis/&lcub;id&rcub;/key-regions</code>. Accept will toast only, no DB write.
                </div>
              )}

              <div className="tiny upper" style={{ color: "var(--ink-3)", marginTop: 16, marginBottom: 4 }}>pattern</div>
              <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 16, color: "var(--ink-0)" }}>{suggestion.pattern}</div>

              <div className="tiny upper" style={{ color: "var(--ink-3)", marginTop: 16, marginBottom: 4 }}>reasoning</div>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: "var(--ink-1)" }}>{suggestion.reasoning}</p>

              {changing && (
                <div style={{ marginTop: 16, padding: "10px 14px", border: "1px solid var(--line)", borderRadius: 6, background: "var(--bg-0)" }}>
                  <div className="tiny upper" style={{ color: "var(--ink-3)" }}>If accepted</div>
                  <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13, color: "var(--ink-1)", lineHeight: 1.7 }}>
                    <li>KeyRegions row added: <code>{measRange.replace("m.", "")} → {suggestion.key}</code></li>
                    <li>{selectedChords.length} chord cells re-tint to <span style={{ color: kvar }}>{suggestion.key}</span></li>
                    <li>Roman numerals recompute against the new tonic for the selection</li>
                    <li>Logged in HarmonicAnalysisExchanges with outcome=accepted</li>
                  </ul>
                </div>
              )}

              {rejecting && (
                <div style={{ marginTop: 16, padding: "10px 14px", border: "1px solid var(--rose)", borderRadius: 6, background: "oklch(.55 .10 25 / .08)" }}>
                  <div className="tiny upper" style={{ color: "var(--rose)" }}>Reject · optional note</div>
                  <input
                    className="input"
                    placeholder="Why reject? (logged to HarmonicAnalysisExchanges)"
                    value={rejectReason}
                    onChange={e => setRejectReason(e.target.value)}
                    style={{ width: "100%", marginTop: 6 }}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* footer */}
        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-0)" }}>
          <span className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>
            {stage === "thinking" ? "awaiting claude response…" : `POST /analysis/.../exchanges/{id}/outcome`}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn--ghost btn--sm" onClick={onCancel}>Cancel</button>
            {stage === "response" && !rejecting && (
              <>
                <button className="btn btn--sm" style={{ color: "var(--rose)", borderColor: "var(--rose)" }} onClick={() => setRejecting(true)}>✕ Reject</button>
                <button className="btn btn--primary btn--sm" onClick={() => onAccept(suggestion)}>✓ Accept · apply</button>
              </>
            )}
            {stage === "response" && rejecting && (
              <>
                <button className="btn btn--ghost btn--sm" onClick={() => setRejecting(false)}>Back</button>
                <button className="btn btn--sm" style={{ color: "var(--rose)", borderColor: "var(--rose)" }} onClick={() => onReject(suggestion, rejectReason)}>Confirm reject</button>
              </>
            )}
          </div>
        </div>
      </div>

      <style>{`@keyframes hl-pulse { 0%, 100% { opacity: 0.4; transform: scale(0.9); } 50% { opacity: 1; transform: scale(1.15); } }`}</style>
    </div>
  );
}

/* ---------------------------------------------------------------------
   export
   --------------------------------------------------------------------- */
Object.assign(window, {
  HLToast: Toast,
  hlUseToasts: useToasts,
  HLChordCell: ChordCell,
  HLChordEditPopover: ChordEditPopover,
  HLKeyPopover: KeyPopover,
  HLTopbar: Topbar,
  HLConfirmModal: ConfirmModal,
  HLAIKeyCenterDialog: AIKeyCenterDialog,
  hlSuggestKeyCenter: suggestKeyCenter,
  hlMergeKeyRegion: mergeKeyRegion,
});