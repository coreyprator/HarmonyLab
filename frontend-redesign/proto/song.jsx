/* =====================================================================
   HarmonyLab interactive prototype — Song detail view
   ===================================================================== */

const { useState: useStateS, useEffect: useEffectS, useRef: useRefS, useMemo: useMemoS, useCallback: useCallbackS } = React;

/* ---------------------------------------------------------------------
   Notation pane — stylised SVG render that knows about chord overrides
   --------------------------------------------------------------------- */
function NotationPane({ song, chords, focusChordId, onExpand }) {
  // Render up to first 8 measures worth — same look as the spec doc
  const visibleChords = chords.slice(0, 8);
  return (
    <div className="notation-pane">
      <div className="notation-head">
        <span>◎ Notation · OSMD</span>
        <span style={{ color: "var(--ink-3)" }}>·</span>
        <span>m.1 — 16 of {song.measureCount}</span>
        {!song.hasXml &&
        <span style={{ marginLeft: 10, color: "var(--rose)", fontFamily: "var(--t-mono)", fontSize: 11 }}>raw_xml missing</span>
        }
        <span className="right">
          <span className="tiny" style={{ color: "var(--ink-3)" }}>zoom</span>
          <button className="btn btn--sm">−</button>
          <button className="btn btn--sm">+</button>
          <button className="btn btn--sm">Fit</button>
          <button className="btn btn--sm" onClick={onExpand}>⤢ Expand</button>
        </span>
      </div>
      <div className="notation-body">
        {!song.hasXml ?
        <div style={{ padding: "32px 24px", textAlign: "center", color: "var(--ink-2)" }}>
            <div className="tiny upper" style={{ color: "var(--ink-3)" }}>Notation unavailable</div>
            <h3 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22, margin: "8px 0 12px", fontWeight: 500, color: "var(--ink-1)" }}>No MusicXML on file.</h3>
            <p style={{ fontSize: 13, margin: "0 auto 16px", maxWidth: 480 }}>This song was imported before the pipeline started storing raw_xml. Chord grid and analysis still work; re-import to enable notation.</p>
            <button className="btn btn--primary btn--sm">Re-import to enable</button>
          </div> :

        <svg viewBox="0 0 1200 240" xmlns="http://www.w3.org/2000/svg" style={{ fontFamily: "var(--t-chord)", width: "100%" }}>
            {/* chord symbols row */}
            <g fontFamily="Petaluma, serif" fontSize="22">
              {visibleChords.map((ch, i) => {
              const x = 80 + i * 120;
              const isHi = ch.id === focusChordId;
              return (
                <g key={ch.id}>
                    <text x={x} y={22}
                  fill={isHi ? "oklch(.79 .13 75)" : "oklch(.97 .005 80)"}
                  opacity={ch.isInferred ? 0.55 : 1}
                  fontStyle={ch.isInferred ? "italic" : "normal"}>
                      {ch.isInferred ? "· " : ""}{ch.symbol}
                    </text>
                    {ch.isInferred &&
                  <line x1={x} y1={28} x2={x + 76} y2={28} stroke="oklch(.42 .005 80)" strokeDasharray="1.5 3" strokeWidth="1" />
                  }
                  </g>);

            })}
            </g>
            {/* highlight rect for focus chord */}
            {focusChordId && (() => {
            const i = visibleChords.findIndex((c) => c.id === focusChordId);
            if (i < 0) return null;
            const x = 80 + i * 120 - 24;
            return <rect x={x} y={56} width={116} height={64} rx="3" fill="oklch(.79 .13 75 / .10)" stroke="oklch(.79 .13 75)" strokeWidth=".8" strokeDasharray="3 2" />;
          })()}

            {/* Treble staff */}
            <g stroke="oklch(.78 .005 80)" strokeWidth="1" fill="none">
              {[60, 74, 88, 102, 116].map((y) => <line key={y} x1={40} y1={y} x2={1170} y2={y} />)}
            </g>
            <text x="48" y="111" fontFamily="Petaluma, serif" fontSize="50" fill="oklch(.97 .005 80)">𝄞</text>
            <text x="100" y="91" fontFamily="Petaluma, serif" fontSize="26" fill="oklch(.78 .005 80)">♭♭</text>
            <text x="128" y="86" fontFamily="Petaluma, serif" fontSize="20" fill="oklch(.97 .005 80)">4</text>
            <text x="128" y="106" fontFamily="Petaluma, serif" fontSize="20" fill="oklch(.97 .005 80)">4</text>

            {/* bar lines + measure numbers */}
            <g stroke="oklch(.58 .005 80)" strokeWidth=".8">
              {[180, 300, 420, 540, 660, 780, 900, 1020].map((x) => <line key={x} x1={x} y1={60} x2={x} y2={116} />)}
              <line x1={1140} y1={60} x2={1140} y2={116} strokeWidth="1.5" />
            </g>
            <g fontFamily="JetBrains Mono, monospace" fontSize="9" fill="oklch(.42 .005 80)">
              {[148, 268, 388, 508, 628, 748, 868, 988].map((x, i) => <text key={x} x={x} y={52}>{i + 1}</text>)}
            </g>

            {/* faux melody — same as spec doc */}
            <g fill="oklch(.97 .005 80)">
              {[
            [92, 95, 98, 68], [128, 90, 134, 64], [158, 85, 164, 60],
            [212, 92, 218, 66], [248, 98, 254, 72], [278, 92, 284, 66],
            [332, 88, 338, 60], [368, 82, 374, 56], [398, 88, 404, 60],
            [452, 92, 458, 66], [488, 98, 494, 72], [518, 92, 524, 66],
            [572, 86, 578, 60], [608, 80, 614, 54],
            [692, 82, 698, 56], [728, 88, 734, 62],
            [812, 86, 818, 60], [848, 80, 854, 54],
            [932, 74, 938, 50], [968, 68, 974, 44],
            [1052, 74, 1058, 48], [1088, 80, 1094, 54]].
            map(([cx, cy, sx, sy], i) =>
            <g key={i}>
                  <ellipse cx={cx} cy={cy} rx={6} ry={4.5} />
                  <line x1={sx} y1={cy} x2={sx} y2={sy} stroke="oklch(.97 .005 80)" strokeWidth="1.2" />
                </g>
            )}
            </g>

            {/* Bass staff */}
            <g stroke="oklch(.78 .005 80)" strokeWidth="1" fill="none">
              {[160, 174, 188, 202, 216].map((y) => <line key={y} x1={40} y1={y} x2={1170} y2={y} />)}
            </g>
            <text x="48" y="193" fontFamily="Petaluma, serif" fontSize="38" fill="oklch(.97 .005 80)">𝄢</text>
            <text x="100" y="190" fontFamily="Petaluma, serif" fontSize="26" fill="oklch(.78 .005 80)">♭♭</text>
            <g stroke="oklch(.58 .005 80)" strokeWidth=".8">
              {[180, 300, 420, 540, 660, 780, 900, 1020].map((x) => <line key={x} x1={x} y1={160} x2={x} y2={216} />)}
              <line x1={1140} y1={160} x2={1140} y2={216} strokeWidth="1.5" />
            </g>
            <g fill="oklch(.97 .005 80)">
              {[138, 258, 370, 490, 610, 730, 850, 970, 1090].map((cx) => <ellipse key={cx} cx={cx} cy={195} rx={6.5} ry={4.5} />)}
            </g>
          </svg>
        }
      </div>
    </div>);

}

/* ---------------------------------------------------------------------
   KeyCenterTimeline
   --------------------------------------------------------------------- */
function KeyCenterTimeline({ song }) {
  const total = song.keyRegions.reduce((a, r) => a + r.weight, 0);
  return (
    <div style={{ marginTop: 24 }}>
      <div className="tiny upper" style={{ color: "var(--ink-3)", marginBottom: 6 }}>Key-center timeline · {song.measureCount} bars · {song.keyRegions.length - 1} modulation{song.keyRegions.length > 2 ? "s" : ""}</div>
      <div style={{ display: "flex", height: 34, border: "1px solid var(--line)", borderRadius: 4, overflow: "hidden", fontFamily: "var(--t-mono)", fontSize: 11 }}>
        {song.keyRegions.map((r, i) => {
          const kvar = "--k-" + (hlKeyCss(r.key).replace("k-", "") || "C");
          return (
            <div key={i} style={{ flex: r.weight, display: "flex", alignItems: "center", justifyContent: "center", background: `color-mix(in oklch, var(${kvar}) 22%, var(--bg-1))`, color: `var(${kvar})` }}>
              {r.key} · m.{r.startMeasure}–{r.endMeasure}
            </div>);

        })}
      </div>
    </div>);

}

/* ---------------------------------------------------------------------
   Export menu
   --------------------------------------------------------------------- */
function ExportMenu({ open, onClose, onExport }) {
  if (!open) return null;
  return (
    <>
      <div style={{ position: "fixed", inset: 0, zIndex: 50 }} onClick={onClose}></div>
      <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", width: 280, background: "var(--bg-2)", border: "1px solid var(--line-2)", borderRadius: 6, boxShadow: "var(--sh-3)", zIndex: 60, padding: 8 }}>
        <div className="tiny upper" style={{ color: "var(--ink-3)", padding: "6px 8px" }}>Export</div>
        <button className="btn btn--ghost" style={{ width: "100%", justifyContent: "space-between", height: 38 }} onClick={() => onExport("mscz")}>
          <span>MuseScore <span className="tiny" style={{ color: "var(--ink-3)" }}>.mscz</span></span>
          <span className="tiny" style={{ color: "var(--green)" }}>existing</span>
        </button>
        <button className="btn btn--ghost" style={{ width: "100%", justifyContent: "space-between", height: 38 }} onClick={() => onExport("musicxml")}>
          <span>MusicXML <span className="tiny" style={{ color: "var(--ink-3)" }}>.musicxml</span></span>
          <span className="tiny" style={{ color: "var(--amber)" }}>new-BE</span>
        </button>
        <button className="btn btn--ghost" style={{ width: "100%", justifyContent: "space-between", height: 38 }} onClick={() => onExport("pdf")}>
          <span>Print to PDF</span>
          <span className="tiny" style={{ color: "var(--ink-3)" }}>browser</span>
        </button>
      </div>
    </>);

}

/* ---------------------------------------------------------------------
   Theory chat drawer
   --------------------------------------------------------------------- */
function TheoryChat({ open, song, selectedChordIds, onClose, onLogOverride }) {
  const [messages, setMessages] = useStateS([
  { who: "you", text: "Why does Jobim use G♭7 here instead of a more conventional ii–V?", meta: `m.5–8 selected` },
  { who: "ai", text: "G♭7 in m.6 is the tritone substitute of C7, which would normally function as V/ii (resolving to Fm or F7). Jobim collapses the conventional Gm7 — C7 — F7 into Gm7 — G♭7 — F7♭9 so the bass walks chromatically down a half-step at every measure (G → G♭ → F).", pattern: "tritone-sub-of-V-of-V also seen in A Felicidade m.11–12", conf: 0.91 }]
  );
  const [draft, setDraft] = useStateS("");
  const [thinking, setThinking] = useStateS(false);

  const send = () => {
    if (!draft.trim()) return;
    setMessages((m) => [...m, { who: "you", text: draft, meta: selectedChordIds.length ? `${selectedChordIds.length} chord${selectedChordIds.length > 1 ? "s" : ""} selected` : null }]);
    setDraft("");
    setThinking(true);
    setTimeout(() => {
      setThinking(false);
      setMessages((m) => [...m, { who: "ai", text: "Yes — Bill Evans on the Riverside take uses an identical voicing in the right hand (F-A-D♭ on top) but anticipates the resolution by a half beat. Listen to take 2 around 1:12.", conf: 0.86 }]);
    }, 1400);
  };

  if (!open) return null;

  return (
    <aside style={{ position: "fixed", top: 0, right: 0, width: 420, height: "100vh", background: "var(--bg-1)", borderLeft: "1px solid var(--line)", zIndex: 90, display: "flex", flexDirection: "column", boxShadow: "var(--sh-3)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 16px", borderBottom: "1px solid var(--line)" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal)" }}></span>
        <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 17 }}>Theory chat</div>
        <span className="tiny" style={{ marginLeft: "auto", color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>claude · 12 docs in RAG</span>
        <button className="btn btn--ghost btn--sm" onClick={onClose}>✕</button>
      </div>
      <div style={{ flex: 1, padding: 16, overflow: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
        {messages.map((m, i) => m.who === "you" ?
        <div key={i}>
            <div className="tiny upper" style={{ color: "var(--ink-3)" }}>you{m.meta && ` · ${m.meta}`}</div>
            <div style={{ background: "var(--bg-2)", borderRadius: 6, padding: "10px 12px", marginTop: 4, fontSize: 13 }}>{m.text}</div>
          </div> :

        <div key={i}>
            <div className="tiny upper" style={{ color: "var(--teal)" }}>claude {m.conf && <span style={{ color: "var(--ink-3)", marginLeft: 8 }}>conf {m.conf}</span>}</div>
            <div style={{ border: "1px solid var(--line)", borderRadius: 6, padding: "10px 12px", marginTop: 4, fontSize: 13, lineHeight: 1.55, color: "var(--ink-1)" }}>
              {m.text}
              {m.pattern && <div className="tiny" style={{ marginTop: 8, color: "var(--ink-3)" }}>Pattern · {m.pattern}</div>}
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
              <button className="btn btn--sm" style={{ color: "var(--green)", borderColor: "var(--green)" }} onClick={() => onLogOverride(m)}>✓ Accept · log as override</button>
              <button className="btn btn--sm btn--ghost">✕ Reject</button>
              <button className="btn btn--sm btn--ghost">Why?</button>
            </div>
          </div>
        )}
        {thinking &&
        <div>
            <div className="tiny upper" style={{ color: "var(--teal)" }}>claude</div>
            <div style={{ border: "1px solid var(--line)", borderRadius: 6, padding: "10px 12px", marginTop: 4, fontSize: 13, color: "var(--ink-2)", fontStyle: "italic" }}>
              thinking…
            </div>
          </div>
        }
      </div>
      <div style={{ padding: "12px 14px", borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}>
        <input className="input" placeholder={selectedChordIds.length ? "Ask about the selection…" : "Ask about this song…"} style={{ flex: 1 }} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
        <button className="btn btn--primary btn--sm" onClick={send}>Ask ⏎</button>
      </div>
    </aside>);

}

/* ---------------------------------------------------------------------
   Song detail
   --------------------------------------------------------------------- */
function SongDetail({ song: initialSong, route, onNavigate, toast, prefs, onOpenMode }) {
  const api = hlUseApi();
  const isLive = api.mode === "live";
  // Local mutable copy of song (so edits are persistent during session)
  const [song, setSong] = useStateS(() => {
    const ls = hlLoadState();
    return ls.songs?.[initialSong.id] || initialSong;
  });
  // when the underlying song changes (e.g. live mode loads, or user navigates), refresh
  useEffectS(() => { setSong(initialSong); }, [initialSong.id, initialSong.title, isLive]);
  const [tab, setTab] = useStateS("chords");
  const [editingChordId, setEditingChordId] = useStateS(null);
  const [selectedChordIds, setSelectedChordIds] = useStateS(new Set());
  const [lastClickedChordId, setLastClickedChordId] = useStateS(null);
  const [keyOpen, setKeyOpen] = useStateS(false);
  const [exportOpen, setExportOpen] = useStateS(false);
  const [chatOpen, setChatOpen] = useStateS(false);
  const [reanalyzing, setReanalyzing] = useStateS(false);
  const [showColors, setShowColors] = useStateS(true);
  const [chordMode, setChordMode] = useStateS(prefs.chordMode || "jazz"); // jazz|plain
  const [grouping, setGrouping] = useStateS("8bar");
  const [confirmReanalyze, setConfirmReanalyze] = useStateS(false);
  const [aiKeyDialogOpen, setAiKeyDialogOpen] = useStateS(false);
  const [rightRailOpen, setRightRailOpen] = useStateS(false);

  // persist song edits
  useEffectS(() => {
    const ls = hlLoadState();
    hlSaveState({ songs: { ...(ls.songs || {}), [song.id]: song } });
  }, [song]);

  const flatChords = useMemoS(() => hlFlattenChords(song), [song]);
  const effectiveKey = song.manualKeyOverride || song.detectedKey;

  // ---- chord cell click — distinguishes plain click (edit) vs modifier (select)
  const onChordCellClick = (chord, event) => {
    const mod = event && (event.metaKey || event.ctrlKey);
    const shift = event && event.shiftKey;
    if (mod) {
      // toggle this chord in selection
      setSelectedChordIds((s) => {
        const n = new Set(s);
        if (n.has(chord.id)) n.delete(chord.id);else
        n.add(chord.id);
        return n;
      });
      setLastClickedChordId(chord.id);
      return;
    }
    if (shift && lastClickedChordId != null) {
      // range select from lastClicked to this chord (inclusive) using chordIndex
      const allChords = flatChords;
      const aIdx = allChords.findIndex((c) => c.id === lastClickedChordId);
      const bIdx = allChords.findIndex((c) => c.id === chord.id);
      if (aIdx >= 0 && bIdx >= 0) {
        const [lo, hi] = aIdx < bIdx ? [aIdx, bIdx] : [bIdx, aIdx];
        const range = allChords.slice(lo, hi + 1).map((c) => c.id);
        setSelectedChordIds((s) => new Set([...s, ...range]));
      }
      return;
    }
    // plain click — if selection is active, plain click clears it without opening edit;
    // if selection is empty, open edit popover
    if (selectedChordIds.size > 0) {
      setSelectedChordIds(new Set());
      setLastClickedChordId(null);
      return;
    }
    setEditingChordId(chord.id);
    setLastClickedChordId(chord.id);
  };

  const clearSelection = () => {setSelectedChordIds(new Set());setLastClickedChordId(null);};

  const selectedChords = useMemoS(() => {
    return flatChords.filter((c) => selectedChordIds.has(c.id)).
    sort((a, b) => a.measureNumber - b.measureNumber);
  }, [flatChords, selectedChordIds]);

  // ---- AI key-center dialog handlers
  const onAcceptAIKey = (suggestion) => {
    setAiKeyDialogOpen(false);
    if (!suggestion || selectedChords.length === 0) return;
    const startM = selectedChords[0].measureNumber;
    const endM = selectedChords[selectedChords.length - 1].measureNumber;

    setSong((s) => {
      const next = JSON.parse(JSON.stringify(s));
      // (1) merge new region into keyRegions
      next.keyRegions = hlMergeKeyRegion(next.keyRegions || [], startM, endM, suggestion.key);
      // (2) update each affected chord's keyCenter so cells repaint
      const selIds = new Set(selectedChords.map((c) => c.id));
      for (const sec of next.sections) for (const meas of sec.measures) for (const ch of meas.chords) {
        if (selIds.has(ch.id)) ch.keyCenter = suggestion.key;
      }
      // (3) log to AI exchanges
      next.aiExchanges = [
      { date: new Date().toISOString().slice(0, 10), question: `Identify key center · m.${startM}–${endM}`, outcome: "accepted" },
      ...(next.aiExchanges || [])];

      // (4) bump override count
      next.overrideCount = (next.overrideCount || 0) + 1;
      return next;
    });
    clearSelection();
    toast(`Key center · m.${startM}–${endM} → ${suggestion.key}`, { meta: `POST /analysis/.../exchanges/{id}/outcome=accept · KeyRegion +1` });
  };
  const onRejectAIKey = (suggestion, reason) => {
    setAiKeyDialogOpen(false);
    setSong((s) => ({
      ...s,
      aiExchanges: [
      { date: new Date().toISOString().slice(0, 10), question: `Identify key center · ${selectedChords[0]?.measureNumber}–${selectedChords[selectedChords.length - 1]?.measureNumber}`, outcome: "rejected", rejectionReason: reason || null },
      ...(s.aiExchanges || [])]

    }));
    toast("AI suggestion rejected", { meta: `POST /analysis/.../exchanges/{id}/outcome=reject` });
  };

  // commit chord edit
  const onCommitEdit = (chord, values) => {
    if (isLive && hlLiveToastFor(api, toast, `PUT /api/v1/chords/${chord.id}`)) {
      setEditingChordId(null);
      return;
    }
    setSong((s) => {
      const next = JSON.parse(JSON.stringify(s));
      for (const sec of next.sections) {
        for (const meas of sec.measures) {
          const idx = meas.chords.findIndex((c) => c.id === chord.id);
          if (idx >= 0) {
            const old = meas.chords[idx];
            // parse roman field: separate base from superscript chars
            const m = values.roman.match(/^([^0-9♭♯ø°Δ]+)(.*)$/);
            const baseRoman = m ? m[1] : values.roman;
            const sup = m ? m[2] : "";
            meas.chords[idx] = {
              ...old,
              symbol: values.symbol,
              roman: baseRoman,
              superscript: sup,
              function: values.func,
              voicing: values.voicing,
              comment: values.comment,
              isInferred: false, // edit removes inferred state
              isManualEdit: true,
              hasOverride: true
            };
          }
        }
      }
      // bump override count for header
      next.overrideCount = (next.overrideCount || 0) + (chord.hasOverride ? 0 : 1);
      return next;
    });
    setEditingChordId(null);
    toast(`Saved · m.${chord.measureNumber} → ${values.symbol}`, { meta: `PUT /chords/${chord.id} · 200 · 84ms` });
  };

  // promote inferred → composer
  const onPromoteInferred = (chord) => {
    if (isLive && hlLiveToastFor(api, toast, `PUT /api/v1/chords/${chord.id}`, { is_inferred: false })) return;
    setSong((s) => {
      const next = JSON.parse(JSON.stringify(s));
      for (const sec of next.sections) for (const meas of sec.measures) {
        const idx = meas.chords.findIndex((c) => c.id === chord.id);
        if (idx >= 0) {
          meas.chords[idx] = { ...meas.chords[idx], isInferred: false, isManualEdit: true };
        }
      }
      return next;
    });
    toast(`Accepted inferred chord at m.${chord.measureNumber} as composer-written`, { meta: `PUT /chords/${chord.id} · is_inferred=false` });
  };

  const onPickKey = (k) => {
    if (isLive && hlLiveToastFor(api, toast, `POST /api/v1/analysis/songs/${song.id}/manual-key`, { key: k })) {
      setKeyOpen(false);
      return;
    }
    setSong((s) => ({ ...s, manualKeyOverride: k }));
    setKeyOpen(false);
    toast(`Manual key set · ${k}`, { meta: `POST /analysis/songs/${song.id}/manual-key` });
    // auto re-analyze for realism
    setReanalyzing(true);
    setTimeout(() => {
      setReanalyzing(false);
      toast("Re-analyzed with new key", { meta: `POST /analysis/songs/${song.id} · 200 · 612ms` });
    }, 1200);
  };
  const onClearManualKey = () => {
    setSong((s) => ({ ...s, manualKeyOverride: null }));
    setKeyOpen(false);
    toast(`Manual key cleared · using detected ${song.detectedKey}`);
  };

  const reanalyze = () => {
    setConfirmReanalyze(false);
    if (isLive && hlLiveToastFor(api, toast, `POST /api/v1/analysis/songs/${song.id}`)) return;
    setReanalyzing(true);
    setTimeout(() => {
      setReanalyzing(false);
      toast("Re-analysis complete", { meta: `POST /analysis/songs/${song.id} · 200 · 612ms · 0 changes` });
    }, 1100);
  };

  const onExport = (kind) => {
    setExportOpen(false);
    if (kind === "mscz") toast("Downloading Corcovado.mscz…", { meta: `GET /exports/musescore/${song.id}` });
    if (kind === "musicxml") toast("Downloading Corcovado.musicxml…", { meta: `GET /exports/musicxml/${song.id} · NEW-BE` });
    if (kind === "pdf") toast("Print dialog → save as PDF");
  };

  const toggleSelect = (chord) => {
    setSelectedChordIds((s) => {
      const next = new Set(s);
      if (next.has(chord.id)) next.delete(chord.id);else
      next.add(chord.id);
      return next;
    });
  };

  /* render */
  const editingChord = flatChords.find((c) => c.id === editingChordId);

  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} songTitle={song.title} />

      {/* title strip */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", padding: "24px 32px 12px", gap: 32 }}>
        <div style={{ flex: 1 }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Song · #{song.id} · imported via {song.sourceFileType}</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginTop: 4 }}>
            <h1 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontWeight: 500, fontSize: 46, margin: 0, lineHeight: 1 }}>{song.title}</h1>
            <span style={{ color: "var(--ink-2)", fontSize: 15 }}>{song.composer} · {song.year} · {song.tempo} · {song.timeSig}</span>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center", flexWrap: "wrap", position: "relative" }}>
            <div style={{ position: "relative" }}>
              <span
                className="pill pill--key"
                style={{ borderColor: `var(--${hlKeyCss(effectiveKey) || "k-C"})`, color: `var(--${hlKeyCss(effectiveKey) || "k-C"})`, cursor: "pointer", whiteSpace: "nowrap" }}
                onClick={() => setKeyOpen((o) => !o)}>
                
                <span className="swatch" style={{ background: `var(--${hlKeyCss(effectiveKey) || "k-C"})` }}></span>
                {effectiveKey} {song.manualKeyOverride && <span style={{ marginLeft: 4, color: "var(--amber)" }}>· manual</span>}
              </span>
              {keyOpen && <HLKeyPopover detected={song.detectedKey} manual={song.manualKeyOverride} onPick={onPickKey} onClear={onClearManualKey} onClose={() => setKeyOpen(false)} />}
            </div>
            <span className="pill"><span style={{ color: "var(--ink-3)" }}>conf</span> {song.confidence}</span>
            <span className="pill">{song.form} · {song.measureCount} bars</span>
            {song.overrideCount > 0 && <span className="pill" style={{ borderColor: "var(--ink-blue)", color: "var(--ink-blue)" }}>{song.overrideCount} override{song.overrideCount > 1 ? "s" : ""}</span>}
            <button className="btn btn--ghost btn--sm" onClick={() => setKeyOpen((o) => !o)}>✎ key</button>
            <button className="btn btn--sm" onClick={() => setConfirmReanalyze(true)} disabled={reanalyzing}>{reanalyzing ? "Analyzing…" : "↻ Re-analyze"}</button>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", position: "relative" }}>
          <button
            className="btn btn--sm"
            style={Object.assign({ whiteSpace: "nowrap" }, rightRailOpen ? { borderColor: "var(--amber)", color: "var(--amber)" } : {})}
            onClick={() => setRightRailOpen(o => !o)}
            title="Study notes — comments, AI exchanges, override history"
          >☰ Notes</button>
          <button className={"btn btn--sm" + (chatOpen ? "" : "")} style={chatOpen ? { borderColor: "var(--teal)", color: "var(--teal)" } : {}} onClick={() => setChatOpen((o) => !o)}>Theory chat</button>
          <div style={{ position: "relative" }}>
            <button className="btn btn--sm" onClick={() => setExportOpen((o) => !o)}>⤓ Export ▾</button>
            <ExportMenu open={exportOpen} onClose={() => setExportOpen(false)} onExport={onExport} />
          </div>
        </div>
      </div>

      {/* score workbench — replaces the old tabs */}
      <HLScoreWorkbench
        song={song}
        selectedChordIds={selectedChordIds}
        selectedChords={selectedChords}
        editingChordId={editingChordId}
        onChordClick={onChordCellClick}
        onClearSelection={clearSelection}
        onOpenAIKeyDialog={() => setAiKeyDialogOpen(true)}
        onPromoteInferred={onPromoteInferred}
        rightRailOpen={rightRailOpen}
        onCloseRail={() => setRightRailOpen(false)}
        onJumpToChord={(c) => { setEditingChordId(c.id); }}
        onOpenChat={() => setChatOpen(true)}
      />

      {/* edit popover */}
      {editingChord &&
      <>
          <div style={{ position: "fixed", inset: 0, zIndex: 30 }} onClick={() => setEditingChordId(null)}></div>
          <div style={{ position: "fixed", zIndex: 40, top: "30vh", left: "50%", transform: "translateX(-50%)" }}>
            <HLChordEditPopover
            chord={editingChord}
            anchorRect={{ top: 0, left: 0 }}
            onCommit={(v) => onCommitEdit(editingChord, v)}
            onCancel={() => setEditingChordId(null)} />
          
          </div>
        </>
      }

      {/* confirm re-analyze */}
      {confirmReanalyze &&
      <HLConfirmModal
        title="Re-analyze this song?"
        body={`Recomputes Roman numerals, function labels and key regions against ${effectiveKey}. User overrides are preserved.`}
        confirmLabel="Re-analyze"
        onConfirm={reanalyze}
        onCancel={() => setConfirmReanalyze(false)} />

      }

      {/* theory chat drawer */}
      <TheoryChat
        open={chatOpen}
        song={song}
        selectedChordIds={[...selectedChordIds]}
        onClose={() => setChatOpen(false)}
        onLogOverride={(m) => toast("Logged AI suggestion as override", { meta: `POST /analysis/.../exchanges/.../outcome=accept` })} />
      

      {/* AI key-center identification dialog */}
      <HLAIKeyCenterDialog
        open={aiKeyDialogOpen}
        song={song}
        selectedChords={selectedChords}
        onAccept={onAcceptAIKey}
        onReject={onRejectAIKey}
        onCancel={() => setAiKeyDialogOpen(false)} />
      
    </div>);

}

Object.assign(window, { HLSongDetail: SongDetail });