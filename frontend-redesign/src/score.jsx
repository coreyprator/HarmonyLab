/* =====================================================================
   HarmonyLab interactive prototype — Score Workbench
   Replaces the previous tabbed Chords/Analysis/Notation/Notes view.

   Layout (per system):
     section banner (if first measure of section)
     key-center band (segmented per-measure)
     chord-symbol row    <-- primary edit surface, clickable + multi-select
     staff (treble; synthetic when raw_xml missing)
     roman-numeral row
     (lyrics row if present)
     (function-label strip, optional, on hover/toggle)

   Auto system-break by chord density:
     maxChordLen > 6  → 4 measures per system
     maxChordLen > 4  → 6 measures per system
     else             → 8 measures per system
   Section boundaries also force a system break.
   ===================================================================== */

import React from 'react';
import { hlFlattenChords, hlKeyCss } from './api.jsx';
import { ChordCell, AIKeyCenterDialog } from './components.jsx';

const { useState: useStateZ, useMemo: useMemoZ, useRef: useRefZ, useEffect: useEffectZ } = React;

/* ---------------------------------------------------------------------
   Layout helpers
   --------------------------------------------------------------------- */
export function maxChordLen(measures) {
  let max = 0;
  for (const m of measures) for (const c of m.chords) max = Math.max(max, (c.symbol || "").length);
  return max;
}
export function systemCapacity(measures) {
  const mx = maxChordLen(measures);
  if (mx > 6) return 4;
  if (mx > 4) return 6;
  return 8;
}
export function groupSystems(sections) {
  const systems = [];
  let cur = null;
  const flushCur = () => { if (cur && cur.measures.length) systems.push(cur); };
  for (const sec of sections) {
    flushCur();
    const sectionRange = `m.${sec.measures[0].number}–m.${sec.measures[sec.measures.length - 1].number}`;
    cur = { sectionName: sec.name, sectionSubtitle: sec.subtitle, sectionRange, sectionId: sec.id, measures: [] };
    for (const meas of sec.measures) {
      cur.measures.push({ ...meas, sectionId: sec.id });
      const cap = systemCapacity(cur.measures);
      if (cur.measures.length >= cap) {
        systems.push(cur);
        cur = { sectionName: null, sectionSubtitle: null, sectionRange: null, sectionId: sec.id, measures: [] };
      }
    }
  }
  flushCur();
  return systems;
}
/* tiny key-segment helper — given a system's measures, group consecutive same-key runs */
function keySegmentsForSystem(measures) {
  const segs = [];
  for (let i = 0; i < measures.length; i++) {
    const k = measures[i].chords[0]?.keyCenter || "—";
    const last = segs[segs.length - 1];
    if (last && last.key === k) last.count++;
    else segs.push({ key: k, count: 1, startIdx: i });
  }
  return segs;
}

/* ---------------------------------------------------------------------
   ChordSymbol — primary edit + selection surface
   --------------------------------------------------------------------- */
export function ChordSymbol({ chord, isSelected, isEditing, onClick, onPromoteInferred }) {
  return (
    <div
      className={"hl-chordsym" + (isSelected ? " is-selected" : "") + (isEditing ? " is-editing" : "") + (chord.isInferred ? " is-inferred" : "") + (chord.isManualEdit ? " is-edited" : "")}
      onClick={(e) => onClick(chord, e)}
      role="button"
      title={chord.comment ? chord.comment : `m.${chord.measureNumber} · ${chord.function}`}
    >
      {chord.comment && <span className="hl-comment-dot" aria-hidden="true"></span>}
      <span className="hl-sym">{chord.isInferred ? "· " : ""}{chord.symbol}</span>
      {chord.voicing && <span className="hl-voicing">{chord.voicing}</span>}
      {chord.isInferred && onPromoteInferred && isSelected && (
        <button
          className="btn btn--sm"
          style={{ position: "absolute", top: -10, right: -8, height: 18, padding: "0 6px", fontSize: 9, color: "var(--ink-blue)", borderColor: "var(--ink-blue)", background: "var(--bg-1)" }}
          onClick={(e) => { e.stopPropagation(); onPromoteInferred(chord); }}
          title="Accept as composer-written"
        >accept ↩</button>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   ScoreSystem — one row of the score (notation + chords + RN)
   --------------------------------------------------------------------- */
export function ScoreSystem({ system, song, idx, hasXml, selectedChordIds, editingChordId, onChordClick, onPromoteInferred, showRoman, showFunc }) {
  const { measures } = system;
  const cols = measures.length;
  const segs = keySegmentsForSystem(measures);

  // build a grid template — equal columns
  const gridCols = `repeat(${cols}, minmax(0, 1fr))`;

  return (
    <div className="hl-system" style={{ marginBottom: 22 }}>
      {/* section banner */}
      {system.sectionName && (
        <div className="hl-section-banner">
          <span className="hl-section-label">{system.sectionName}</span>
          <span className="hl-section-subtitle">{system.sectionSubtitle}</span>
          <span className="hl-section-range">{system.sectionRange}</span>
        </div>
      )}

      {/* key-center band */}
      <div className="hl-keyband" style={{ display: "grid", gridTemplateColumns: gridCols }}>
        {(() => {
          // emit one element per key-segment spanning N columns
          const out = [];
          let col = 1;
          for (const s of segs) {
            const kc = hlKeyCss(s.key) || "k-C";
            out.push(
              <div key={s.startIdx + "-" + s.key} className={"hl-keyband-seg " + kc} style={{ gridColumn: `${col} / span ${s.count}` }}>
                <span className="hl-keyband-label">{s.key}</span>
              </div>
            );
            col += s.count;
          }
          return out;
        })()}
      </div>

      {/* chord-symbol row */}
      <div className="hl-chordrow" style={{ display: "grid", gridTemplateColumns: gridCols }}>
        {measures.map((meas) => (
          <div key={meas.number} className="hl-measure-chordcell">
            {meas.chords.map(ch => {
              // resolve chordIndex
              const enriched = { ...ch, measureNumber: meas.number };
              // chord index resolution (linear scan)
              let i = 0;
              for (const sec of song.sections) for (const m of sec.measures) for (const c of m.chords) {
                if (c.id === ch.id) enriched.chordIndex = i;
                i++;
              }
              return (
                <ChordSymbol
                  key={ch.id}
                  chord={enriched}
                  isSelected={selectedChordIds.has(ch.id)}
                  isEditing={editingChordId === ch.id}
                  onClick={onChordClick}
                  onPromoteInferred={onPromoteInferred}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* staff */}
      <div className="hl-staff-wrap">
        {hasXml ? <Staff system={system} idx={idx} /> : <SyntheticStaff measures={measures} />}
      </div>

      {/* roman numeral row */}
      {showRoman && (
        <div className="hl-romanrow" style={{ display: "grid", gridTemplateColumns: gridCols }}>
          {measures.map(meas => (
            <div key={meas.number} className="hl-measure-romancell">
              {meas.chords.map(ch => (
                <span key={ch.id} className={"hl-roman " + ch.romanCase + (ch.isInferred ? " is-inferred" : "")}>
                  {ch.roman}{ch.superscript && <sup>{ch.superscript}</sup>}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* function strip — small, secondary */}
      {showFunc && (
        <div className="hl-funcrow" style={{ display: "grid", gridTemplateColumns: gridCols }}>
          {measures.map(meas => (
            <div key={meas.number} className="hl-measure-funccell">
              {meas.chords.map(ch => (
                <span key={ch.id} className="hl-func">{ch.function}</span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   Staff — stylised treble staff render for one system
   --------------------------------------------------------------------- */
export function Staff({ system, idx }) {
  const cols = system.measures.length;
  const W = 1200, H = 96, leftPad = idx === 0 ? 60 : 24, rightPad = 14;
  const colW = (W - leftPad - rightPad) / cols;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: 84, display: "block" }}>
      {/* 5 staff lines */}
      <g stroke="oklch(.62 .005 80)" strokeWidth="1" fill="none">
        {[20, 32, 44, 56, 68].map(y => <line key={y} x1={4} y1={y} x2={W - 4} y2={y} />)}
      </g>
      {/* treble clef (only on first system per song) */}
      {idx === 0 && (
        <text x={10} y={62} fontFamily="Petaluma, serif" fontSize={42} fill="oklch(.97 .005 80)">𝄞</text>
      )}
      {/* bar lines */}
      <g stroke="oklch(.55 .005 80)" strokeWidth=".8">
        {Array.from({ length: cols + 1 }, (_, i) => {
          const x = leftPad + i * colW;
          const isFinal = i === cols;
          return <line key={i} x1={x} y1={20} x2={x} y2={68} strokeWidth={isFinal ? 1.6 : 0.8} />;
        })}
      </g>
      {/* measure numbers */}
      <g fontFamily="JetBrains Mono, monospace" fontSize={8.5} fill="oklch(.42 .005 80)">
        {system.measures.map((m, i) => (
          <text key={m.number} x={leftPad + i * colW + 4} y={14}>m.{m.number}</text>
        ))}
      </g>
      {/* stylised melody notes — three per measure deterministically */}
      <g fill="oklch(.97 .005 80)">
        {system.measures.flatMap((m, mi) => {
          // deterministic seed by measureNumber
          const seed = (m.number * 9301 + 49297) % 233280;
          const r = (k) => ((seed + k * 1373) % 233280) / 233280;
          return [0, 1, 2].map(k => {
            const cx = leftPad + mi * colW + colW * (0.25 + k * 0.25);
            const cy = 28 + r(k) * 30;
            const sy = cy - 22;
            return (
              <g key={m.number + "-" + k}>
                <ellipse cx={cx} cy={cy} rx={4.5} ry={3.5} />
                <line x1={cx + 4.5} y1={cy - 1} x2={cx + 4.5} y2={sy} stroke="oklch(.97 .005 80)" strokeWidth="1" />
              </g>
            );
          });
        })}
      </g>
    </svg>
  );
}

/* synthetic staff — used when raw_xml missing (32/42 songs) */
export function SyntheticStaff({ measures }) {
  const cols = measures.length;
  return (
    <div className="hl-synth-staff" style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }} title="No MusicXML on file · synthetic staff">
      {measures.map((m, i) => (
        <div key={m.number} className="hl-synth-measure">
          <div className="hl-synth-line"></div>
          <span className="hl-synth-num">m.{m.number}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------------
   RightRail — comments / AI exchanges / override history
   --------------------------------------------------------------------- */
export function RightRail({ open, song, flatChords, onClose, onJumpToChord, onOpenChat }) {
  const [tab, setTab] = useStateZ("comments");
  if (!open) return null;
  const commented = flatChords.filter(c => c.comment);
  const edited = flatChords.filter(c => c.isManualEdit);
  return (
    <aside className="hl-rail" data-open={open}>
      <div className="hl-rail-head">
        <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 17 }}>Study notes</div>
        <button className="btn btn--ghost btn--sm" style={{ marginLeft: "auto" }} onClick={onClose}>✕</button>
      </div>
      <div className="hl-rail-tabs">
        <button className={tab === "comments" ? "is-on" : ""} onClick={() => setTab("comments")}>Comments <span className="tiny">{commented.length}</span></button>
        <button className={tab === "exchanges" ? "is-on" : ""} onClick={() => setTab("exchanges")}>AI exchanges <span className="tiny">{(song.aiExchanges || []).length}</span></button>
        <button className={tab === "overrides" ? "is-on" : ""} onClick={() => setTab("overrides")}>Overrides <span className="tiny">{edited.length}</span></button>
      </div>
      <div className="hl-rail-body">
        {tab === "comments" && (commented.length === 0
          ? <div className="tiny" style={{ color: "var(--ink-3)", padding: 14 }}>No comments yet. Click any chord above the staff and add a comment in the popover.</div>
          : commented.map(c => (
              <div key={c.id} className="hl-rail-item" onClick={() => onJumpToChord(c)}>
                <div className="hl-rail-item-head">
                  <span className="tiny upper" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>m.{c.measureNumber}</span>
                  <span style={{ fontFamily: "var(--t-chord)", fontSize: 16 }}>{c.symbol}</span>
                  <span style={{ fontFamily: "var(--t-roman)", fontStyle: "italic", color: "var(--ink-2)" }}>{c.roman}{c.superscript && <sup>{c.superscript}</sup>}</span>
                </div>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-1)", fontFamily: "var(--t-display)", fontStyle: "italic" }}>"{c.comment}"</p>
              </div>
            ))
        )}
        {tab === "exchanges" && (
          <>
            {(song.aiExchanges || []).length === 0
              ? <div className="tiny" style={{ color: "var(--ink-3)", padding: 14 }}>No prior exchanges. <a style={{ color: "var(--ink-blue)", cursor: "pointer" }} onClick={onOpenChat}>Open Theory Chat →</a></div>
              : (song.aiExchanges || []).map((ex, i) => (
                  <div key={i} className="hl-rail-item">
                    <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                      <span className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>{ex.date}</span>
                      <span className="tiny" style={{ color: ex.outcome === "accepted" ? "var(--green)" : ex.outcome === "rejected" ? "var(--rose)" : "var(--ink-3)", marginLeft: "auto" }}>{ex.outcome}</span>
                    </div>
                    <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-1)", fontFamily: "var(--t-display)", fontStyle: "italic" }}>"{ex.question}"</p>
                    {ex.rejectionReason && <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--rose)" }}>↪ {ex.rejectionReason}</p>}
                  </div>
                ))
            }
            <div style={{ padding: 12, borderTop: "1px solid var(--line)" }}>
              <button className="btn btn--sm" onClick={onOpenChat}>+ New chat</button>
            </div>
          </>
        )}
        {tab === "overrides" && (
          edited.length === 0
            ? <div className="tiny" style={{ color: "var(--ink-3)", padding: 14 }}>No user overrides yet. Click any chord to edit the parser output.</div>
            : edited.map(c => (
                <div key={c.id} className="hl-rail-item" onClick={() => onJumpToChord(c)}>
                  <div className="hl-rail-item-head">
                    <span className="tiny upper" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>m.{c.measureNumber}</span>
                    <span style={{ fontFamily: "var(--t-chord)", fontSize: 16 }}>{c.symbol}</span>
                    <span className="badge b-edited" style={{ marginLeft: "auto" }}>edited</span>
                  </div>
                  {c.voicing && <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--ink-blue)", fontFamily: "var(--t-mono)" }}>voicing: {c.voicing}</p>}
                </div>
              ))
        )}
      </div>
    </aside>
  );
}

/* ---------------------------------------------------------------------
   BottomAnalysis — patterns + phrases + full key timeline
   --------------------------------------------------------------------- */
export function BottomAnalysis({ song }) {
  const total = song.keyRegions.reduce((a, r) => a + r.weight, 0);
  return (
    <section className="hl-bottom-analysis">
      <div className="hl-ba-card">
        <div className="tiny upper" style={{ color: "var(--amber)" }}>Key-center timeline</div>
        <div style={{ display: "flex", height: 26, border: "1px solid var(--line)", borderRadius: 4, overflow: "hidden", marginTop: 8 }}>
          {song.keyRegions.map((r, i) => {
            const kvar = "--k-" + (hlKeyCss(r.key).replace("k-","") || "C");
            return (
              <div key={i} style={{ flex: r.weight, display: "flex", alignItems: "center", justifyContent: "center", background: `color-mix(in oklch, var(${kvar}) 22%, var(--bg-1))`, color: `var(${kvar})`, fontFamily: "var(--t-mono)", fontSize: 10, padding: "0 6px", overflow: "hidden", whiteSpace: "nowrap" }}>{r.key}</div>
            );
          })}
        </div>
        <div className="tiny" style={{ marginTop: 6, color: "var(--ink-3)" }}>{song.keyRegions.length - 1} modulation{song.keyRegions.length > 2 ? "s" : ""} · {song.keyRegions.filter(r => r.isUserDefined).length} user-defined</div>
      </div>
      <div className="hl-ba-card">
        <div className="tiny upper" style={{ color: "var(--amber)" }}>Detected patterns · {song.patterns.length}</div>
        {song.patterns.length === 0 && <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 8 }}>None detected.</div>}
        <table style={{ width: "100%", marginTop: 6, fontSize: 12 }}><tbody>
          {song.patterns.slice(0, 4).map((p, i) => (
            <tr key={i}>
              <td style={{ padding: "4px 0", fontFamily: "var(--t-display)", fontStyle: "italic" }}>{p.name}</td>
              <td style={{ fontFamily: "var(--t-mono)", fontSize: 10, color: "var(--ink-2)", textAlign: "right" }}>{p.range}</td>
            </tr>
          ))}
        </tbody></table>
      </div>
      <div className="hl-ba-card">
        <div className="tiny upper" style={{ color: "var(--amber)" }}>Phrases · {song.phrases.length}</div>
        {song.phrases.length === 0 && <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 8 }}>None detected.</div>}
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6, fontSize: 12 }}>
          {song.phrases.slice(0, 4).map((p, i) => (
            <div key={i} style={{ color: "var(--ink-1)" }}><span style={{ fontFamily: "var(--t-mono)", fontSize: 10, color: "var(--ink-3)", marginRight: 6 }}>{p.range}</span><em style={{ fontFamily: "var(--t-display)" }}>{p.name}</em></div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------------
   ScoreWorkbench — the merged view
   --------------------------------------------------------------------- */
export function ScoreWorkbench({ song, selectedChordIds, selectedChords, editingChordId, onChordClick, onClearSelection, onOpenAIKeyDialog, onPromoteInferred, rightRailOpen, onCloseRail, onJumpToChord, onOpenChat }) {
  const [showRoman, setShowRoman] = useStateZ(true);
  const [showFunc, setShowFunc] = useStateZ(true);

  const systems = useMemoZ(() => groupSystems(song.sections), [song.sections]);
  const flatChords = useMemoZ(() => hlFlattenChords(song), [song]);

  // selection metrics
  const selectionStraddlesKey = useMemoZ(() => {
    if (selectedChords.length < 2) return false;
    const k = selectedChords[0].keyCenter;
    return selectedChords.some(c => c.keyCenter !== k);
  }, [selectedChords]);

  return (
    <>
      {/* score-mode toolbar */}
      <div className="hl-score-toolbar">
        <div className="seg">
          <button className={showRoman ? "is-on" : ""} onClick={() => setShowRoman(s => !s)}>Roman</button>
          <button className={showFunc ? "is-on" : ""} onClick={() => setShowFunc(s => !s)}>Function</button>
        </div>
        <span className="tiny" style={{ color: "var(--ink-3)", marginLeft: "auto" }}>
          {song.hasXml ? "OSMD render · raw_xml present" : "synthetic staff · re-import for full notation"}
          {" · "}
          ⌘-click to select, shift-click to range-select
        </span>
      </div>

      {/* selection toolbar */}
      {selectedChords.length > 0 && (
        <div className="hl-selection-bar">
          <span className="tiny upper" style={{ color: "var(--amber)" }}>Selection</span>
          <span style={{ fontFamily: "var(--t-mono)", fontSize: 12, color: "var(--ink-1)" }}>
            {selectedChords.length} chord{selectedChords.length>1?"s":""} · m.{selectedChords[0].measureNumber} – m.{selectedChords[selectedChords.length-1].measureNumber}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--ink-2)", fontFamily: "var(--t-chord)", fontSize: 14 }}>
            {selectedChords.slice(0, 6).map((c, i) => (
              <React.Fragment key={c.id}>{i > 0 && <span style={{ color: "var(--ink-3)" }}>·</span>}<span>{c.symbol}</span></React.Fragment>
            ))}
            {selectedChords.length > 6 && <span className="tiny" style={{ color: "var(--ink-3)", marginLeft: 4 }}>+ {selectedChords.length - 6} more</span>}
          </div>
          {selectionStraddlesKey && (
            <span className="pill" style={{ fontSize: 11, color: "var(--amber)", borderColor: "var(--amber)" }}>spans {[...new Set(selectedChords.map(c => c.keyCenter))].length} key centres</span>
          )}
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="btn btn--primary btn--sm" onClick={onOpenAIKeyDialog} disabled={selectedChords.length < 2} style={selectedChords.length < 2 ? { opacity: 0.5, cursor: "not-allowed", whiteSpace: "nowrap" } : { whiteSpace: "nowrap" }}>
              ✦ Identify key center
            </button>
            <button className="btn btn--ghost btn--sm" onClick={onClearSelection} title="Clear selection (Esc)">✕</button>
          </div>
        </div>
      )}

      {/* the score */}
      <div className={"hl-score" + (rightRailOpen ? " has-rail" : "")}>
        <div className="hl-score-body">
          {systems.map((sys, i) => (
            <ScoreSystem
              key={i}
              system={sys}
              song={song}
              idx={i}
              hasXml={song.hasXml}
              selectedChordIds={selectedChordIds}
              editingChordId={editingChordId}
              onChordClick={onChordClick}
              onPromoteInferred={onPromoteInferred}
              showRoman={showRoman}
              showFunc={showFunc}
            />
          ))}
          <BottomAnalysis song={song} />
        </div>
        {rightRailOpen && (
          <RightRail
            open={rightRailOpen}
            song={song}
            flatChords={flatChords}
            onClose={onCloseRail}
            onJumpToChord={onJumpToChord}
            onOpenChat={onOpenChat}
          />
        )}
      </div>
    </>
  );
}

Object.assign(window, { HLScoreWorkbench: ScoreWorkbench });
