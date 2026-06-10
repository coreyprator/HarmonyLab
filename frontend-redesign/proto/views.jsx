/* =====================================================================
   HarmonyLab interactive prototype — Library, Settings, Audit, Lab,
   Import modal
   ===================================================================== */

const { useState: useStateV, useEffect: useEffectV, useMemo: useMemoV, useRef: useRefV } = React;

/* ---------------------------------------------------------------------
   Column-header sort + multi-select filter primitives
   --------------------------------------------------------------------- */
function SortArrows({ dir, onToggle }) {
  // dir: "asc" | "desc" | null
  return (
    <button
      className="btn btn--ghost btn--sm"
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      title="Sort"
      style={{ height: 16, padding: "0 2px", display: "inline-flex", flexDirection: "column", gap: 0, alignItems: "center", lineHeight: 1 }}
    >
      <span style={{ fontSize: 8, color: dir === "asc" ? "var(--amber)" : "var(--ink-3)", lineHeight: .9 }}>▲</span>
      <span style={{ fontSize: 8, color: dir === "desc" ? "var(--amber)" : "var(--ink-3)", lineHeight: .9 }}>▼</span>
    </button>
  );
}

function ColumnFilter({ values, options, onChange, label }) {
  const [open, setOpen] = useStateV(false);
  const wrapRef = useRefV(null);
  useEffectV(() => {
    if (!open) return;
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const active = values && values.size > 0;
  const toggle = (v) => {
    const next = new Set(values || []);
    if (next.has(v)) next.delete(v); else next.add(v);
    onChange(next);
  };
  return (
    <span ref={wrapRef} style={{ position: "relative", display: "inline-block", marginLeft: 4 }}>
      <button
        className="btn btn--ghost btn--sm"
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o); }}
        title={"Filter " + label}
        style={{ height: 16, padding: "0 4px", fontSize: 10, color: active ? "var(--amber)" : "var(--ink-3)", borderColor: active ? "var(--amber)" : "transparent" }}
      >
        ▼{active ? ` ${values.size}` : ""}
      </button>
      {open && (
        <div
          style={{
            position: "absolute", top: "calc(100% + 4px)", left: 0,
            zIndex: 40, minWidth: 200, maxHeight: 320, overflow: "auto",
            background: "var(--bg-2)", border: "1px solid var(--line-2)",
            borderRadius: 4, boxShadow: "var(--sh-3)", padding: 6,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="tiny upper" style={{ color: "var(--ink-3)", padding: "4px 6px" }}>Filter · {label}</div>
          {active && (
            <div style={{ padding: "0 6px 6px", borderBottom: "1px solid var(--line)", marginBottom: 4 }}>
              <button className="btn btn--ghost btn--sm" style={{ width: "100%", fontSize: 10 }} onClick={() => onChange(new Set())}>Clear filter</button>
            </div>
          )}
          {options.map(opt => {
            const checked = values && values.has(opt.value);
            return (
              <label key={String(opt.value)} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 6px", fontSize: 12, cursor: "pointer", borderRadius: 3, color: checked ? "var(--ink-0)" : "var(--ink-1)" }}>
                <input type="checkbox" checked={!!checked} onChange={() => toggle(opt.value)} />
                <span style={{ flex: 1 }}>{opt.label}</span>
                <span className="tiny" style={{ color: "var(--ink-3)" }}>{opt.count}</span>
              </label>
            );
          })}
        </div>
      )}
    </span>
  );
}

function SortableHeader({ label, sortKey, sort, onSort, align, filterOptions, filterValues, onFilterChange }) {
  const dir = sort.key === sortKey ? sort.dir : null;
  const toggle = () => {
    if (sort.key !== sortKey) onSort({ key: sortKey, dir: "asc" });
    else if (sort.dir === "asc") onSort({ key: sortKey, dir: "desc" });
    else onSort({ key: null, dir: null });
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 2, justifyContent: align === "right" ? "flex-end" : "flex-start", width: "100%" }}>
      <span style={{ cursor: "pointer" }} onClick={toggle}>{label}</span>
      <SortArrows dir={dir} onToggle={toggle} />
      {filterOptions && <ColumnFilter values={filterValues} options={filterOptions} onChange={onFilterChange} label={label} />}
    </span>
  );
}

/* ---------------------------------------------------------------------
   LIBRARY
   --------------------------------------------------------------------- */
function Library({ route, onNavigate, prefs, toast, onOpenMode }) {
  const [q, setQ] = useStateV("");
  const [selected, setSelected] = useStateV(new Set());
  const [importOpen, setImportOpen] = useStateV(false);
  const [confirmDel, setConfirmDel] = useStateV(false);
  const [sort, setSort] = useStateV({ key: null, dir: null });
  const [filters, setFilters] = useStateV({});  // colKey -> Set of values

  // Live-mode data hook — mock mode returns ALL_LIBRARY_ROWS directly
  const api = hlUseApi();
  const { data: liveRows, loading, error } = hlUseLibraryRows();
  const all = liveRows || (api.mode === "mock" ? window.HL_DATA.ALL_LIBRARY_ROWS : []);

  // build per-column filter options (label + count over UNfiltered rows)
  const filterOptions = useMemoV(() => {
    const opt = (key, labelFn) => {
      const m = new Map();
      for (const r of all) {
        const v = key(r);
        m.set(v, (m.get(v) || 0) + 1);
      }
      return [...m.entries()]
        .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
        .map(([value, count]) => ({ value, label: labelFn ? labelFn(value) : String(value ?? "—"), count }));
    };
    return {
      title:    opt(r => r.title),
      composer: opt(r => r.composer),
      genre:    opt(r => r.genre || "—"),
      key:      opt(r => r.key),
      form:     opt(r => r.form),
      hasXml:   opt(r => r.hasXml ? "has XML" : "no XML"),
      hasLyrics: opt(r => r.hasLyrics ? "has lyrics" : "no lyrics"),
      hasOverrides: opt(r => r.overrideCount > 0 ? "has overrides" : "no overrides"),
    };
  }, [all]);

  const setColFilter = (col) => (vals) => {
    setFilters(f => {
      const next = { ...f };
      if (!vals || vals.size === 0) delete next[col];
      else next[col] = vals;
      return next;
    });
  };

  const rows = useMemoV(() => {
    const want = (col, v) => !filters[col] || filters[col].has(v);
    let xs = all.filter(r => {
      if (q && !(`${r.title} ${r.composer}`.toLowerCase().includes(q.toLowerCase()))) return false;
      if (!want("title", r.title)) return false;
      if (!want("composer", r.composer)) return false;
      if (!want("genre", r.genre || "—")) return false;
      if (!want("key", r.key)) return false;
      if (!want("form", r.form)) return false;
      if (filters.hasXml && !filters.hasXml.has(r.hasXml ? "has XML" : "no XML")) return false;
      if (filters.hasLyrics && !filters.hasLyrics.has(r.hasLyrics ? "has lyrics" : "no lyrics")) return false;
      if (filters.hasOverrides && !filters.hasOverrides.has(r.overrideCount > 0 ? "has overrides" : "no overrides")) return false;
      return true;
    });
    if (sort.key) {
      const getter = {
        title: r => r.title.toLowerCase(),
        composer: r => r.composer.toLowerCase(),
        genre: r => r.genre || "",
        key: r => r.key,
        form: r => r.form,
        measureCount: r => r.measureCount,
        chordCount: r => r.chordCount,
        importedAt: r => r.importedAt,
        fsModifiedAt: r => r.fsModifiedAt || "",
        dataScore: r => (r.hasXml?4:0) + (r.hasNotes?2:0) + (r.hasLyrics?1:0) + (r.overrideCount>0?0.5:0),
      }[sort.key] || (r => r[sort.key]);
      xs = [...xs].sort((a, b) => {
        const A = getter(a), B = getter(b);
        if (A < B) return sort.dir === "asc" ? -1 : 1;
        if (A > B) return sort.dir === "asc" ? 1 : -1;
        return 0;
      });
    }
    return xs;
  }, [q, filters, sort, all]);

  const stats = useMemoV(() => {
    return {
      total: all.length,
      withXml: all.filter(r => r.hasXml).length,
      withLyrics: all.filter(r => r.hasLyrics).length,
      withOverrides: all.filter(r => r.overrideCount > 0).length,
    };
  }, [all]);

  const toggle = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const allChecked = rows.length > 0 && rows.every(r => selected.has(r.id));
  const toggleAll = () => setSelected(allChecked ? new Set() : new Set(rows.map(r => r.id)));
  const activeFilterCount = Object.keys(filters).length;

  // Live-mode loading / error guards — placed AFTER all hooks to avoid Rules-of-Hooks violation
  if (api.mode === "live" && loading && !liveRows) {
    return <div className="app" style={{ minHeight: "100vh" }}><HLTopbar route={route} onNavigate={onNavigate} /><HLLoadingState what="library" /></div>;
  }
  if (api.mode === "live" && error && !liveRows) {
    return <div className="app" style={{ minHeight: "100vh" }}><HLTopbar route={route} onNavigate={onNavigate} /><HLErrorState error={error} onChangeMode={onOpenMode} /></div>;
  }

  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} />

      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", padding: "32px 32px 16px" }}>
        <div>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Library</div>
          <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 34, lineHeight: 1.1 }}>{stats.total} songs.</div>
          <div style={{ color: "var(--ink-2)", fontSize: 13, marginTop: 6 }}>
            {stats.withXml} have raw_xml · {stats.withLyrics} have lyrics · {stats.withOverrides} have chord overrides
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="input" placeholder="Filter title / composer…" style={{ width: 220 }} value={q} onChange={e => setQ(e.target.value)} />
          {activeFilterCount > 0 && (
            <button className="btn btn--ghost" onClick={() => setFilters({})}>Clear {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""}</button>
          )}
          {sort.key && (
            <button className="btn btn--ghost" onClick={() => setSort({ key: null, dir: null })}>Clear sort</button>
          )}
          {selected.size > 0 && <button className="btn btn--danger" onClick={() => setConfirmDel(true)}>Delete {selected.size}</button>}
          <button className="btn btn--primary" onClick={() => setImportOpen(true)}>+ Import</button>
        </div>
      </div>

      <table className="tbl" style={{ margin: "0 32px", width: "calc(100% - 64px)" }}>
        <thead>
          <tr>
            <th style={{ width: 24 }}><input type="checkbox" checked={allChecked} onChange={toggleAll} /></th>
            <th><SortableHeader label="Title" sortKey="title" sort={sort} onSort={setSort} filterOptions={filterOptions.title} filterValues={filters.title} onFilterChange={setColFilter("title")} /></th>
            <th><SortableHeader label="Composer" sortKey="composer" sort={sort} onSort={setSort} filterOptions={filterOptions.composer} filterValues={filters.composer} onFilterChange={setColFilter("composer")} /></th>
            <th><SortableHeader label="Genre" sortKey="genre" sort={sort} onSort={setSort} filterOptions={filterOptions.genre} filterValues={filters.genre} onFilterChange={setColFilter("genre")} /></th>
            <th><SortableHeader label="Key" sortKey="key" sort={sort} onSort={setSort} filterOptions={filterOptions.key} filterValues={filters.key} onFilterChange={setColFilter("key")} /></th>
            <th><SortableHeader label="Form" sortKey="form" sort={sort} onSort={setSort} filterOptions={filterOptions.form} filterValues={filters.form} onFilterChange={setColFilter("form")} /></th>
            <th style={{ textAlign: "right" }}><SortableHeader label="Measures" sortKey="measureCount" sort={sort} onSort={setSort} align="right" /></th>
            <th style={{ textAlign: "right" }}><SortableHeader label="Chords" sortKey="chordCount" sort={sort} onSort={setSort} align="right" /></th>
            <th><SortableHeader label="Imported" sortKey="importedAt" sort={sort} onSort={setSort} /></th>
            <th><SortableHeader label="Source · modified" sortKey="fsModifiedAt" sort={sort} onSort={setSort} /></th>
            <th style={{ textAlign: "right" }}>
              <SortableHeader
                label="Data"
                sortKey="dataScore"
                sort={sort}
                onSort={setSort}
                align="right"
                filterOptions={[...filterOptions.hasXml, ...filterOptions.hasLyrics, ...filterOptions.hasOverrides]}
                filterValues={new Set([...(filters.hasXml || []), ...(filters.hasLyrics || []), ...(filters.hasOverrides || [])])}
                onFilterChange={(vals) => {
                  setFilters(f => {
                    const next = { ...f };
                    const xml = new Set(), lyr = new Set(), ovr = new Set();
                    for (const v of vals) {
                      if (v === "has XML" || v === "no XML") xml.add(v);
                      else if (v === "has lyrics" || v === "no lyrics") lyr.add(v);
                      else if (v === "has overrides" || v === "no overrides") ovr.add(v);
                    }
                    if (xml.size) next.hasXml = xml; else delete next.hasXml;
                    if (lyr.size) next.hasLyrics = lyr; else delete next.hasLyrics;
                    if (ovr.size) next.hasOverrides = ovr; else delete next.hasOverrides;
                    return next;
                  });
                }}
              />
            </th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const kvar = `var(--${hlKeyCss(r.key) || "k-C"})`;
            const dataTags = [
              r.hasXml && "XML",
              r.hasNotes && "NOTES",
              r.hasLyrics && "LYRICS",
              r.overrideCount > 0 && `${r.overrideCount} override${r.overrideCount > 1 ? "s" : ""}`,
            ].filter(Boolean);
            return (
              <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onNavigate({ name: "song", id: r.id })}>
                <td onClick={e => e.stopPropagation()}><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} /></td>
                <td className="t-title">{r.title}</td>
                <td className="t-composer">{r.composer}</td>
                <td className="t-composer" style={{ color: "var(--ink-2)" }}>{r.genre || "—"}</td>
                <td>
                  <span className="pill pill--key" style={{ borderColor: kvar, color: kvar }}>
                    <span className="swatch" style={{ background: kvar }}></span>{r.key}
                  </span>
                </td>
                <td>{r.form}</td>
                <td className="t-mono" style={{ textAlign: "right" }}>{r.measureCount}</td>
                <td className="t-mono" style={{ textAlign: "right" }}>{r.chordCount}</td>
                <td className="t-mono">{r.importedAt}</td>
                <td className="t-mono">{r.fsModifiedAt || "—"}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <span className="tiny" style={{ color: r.hasXml ? (r.overrideCount > 0 ? "var(--amber)" : "var(--green)") : "var(--ink-3)" }}>{dataTags.join(" · ") || "NO XML"}</span>
                </td>
                <td onClick={e => e.stopPropagation()}>
                  {r.hasNotes && <a className="tiny" style={{ color: "var(--ink-blue)" }} onClick={() => onNavigate({ name: "audit", id: r.id })}>audit →</a>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div style={{ display: "flex", justifyContent: "space-between", padding: "16px 32px 28px", alignItems: "center" }}>
        <div className="tiny">
          {selected.size} selected · {rows.length} of {all.length} shown
          {sort.key && <> · sorted by <strong style={{ color: "var(--amber)" }}>{sort.key} {sort.dir === "asc" ? "↑" : "↓"}</strong></>}
          {activeFilterCount > 0 && <> · {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""} active</>}
        </div>
        <div className="tiny" style={{ color: "var(--ink-3)" }}>GET /api/v1/songs/?limit=100 · {rows.length} results · 31ms</div>
      </div>

      {importOpen && <ImportModal onClose={() => setImportOpen(false)} onImport={(name) => { setImportOpen(false); toast(`Imported "${name}" to library`, { meta:"POST /imports/omr/import · 200" }); }} />}
      {confirmDel && (
        <HLConfirmModal
          title={`Delete ${selected.size} song${selected.size > 1 ? "s" : ""}?`}
          body="This cascades through 14 child tables: chords, measures, sections, notes, lyrics, imports. Cannot be undone."
          confirmLabel="Delete"
          danger
          onConfirm={() => {
            const n = selected.size;
            setSelected(new Set());
            setConfirmDel(false);
            toast(`Deleted ${n} song${n > 1 ? "s" : ""}`, { meta:"DELETE /songs/bulk/delete · 200" });
          }}
          onCancel={() => setConfirmDel(false)}
        />
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   SETTINGS
   --------------------------------------------------------------------- */
function Settings({ route, onNavigate, prefs, setPrefs, toast }) {
  const [pendingPrefs, setPendingPrefs] = useStateV(prefs);
  const [dirty, setDirty] = useStateV(false);

  const setMode = (mode) => { setPendingPrefs(p => ({ ...p, chordMode: mode })); setDirty(true); };
  const setColor = (key, value) => { setPendingPrefs(p => ({ ...p, keyColors: { ...p.keyColors, [key]: value } })); setDirty(true); };
  const setDebug = (val) => { setPendingPrefs(p => ({ ...p, debugMode: val })); setDirty(true); };

  const save = () => {
    setPrefs(pendingPrefs);
    setDirty(false);
    toast("Preferences saved", { meta: "PUT /api/v1/preferences · 200" });
  };
  const reset = () => {
    setPendingPrefs({ chordMode: "jazz", keyColors: { ...window.HL_DATA.KEY_COLOR_DEFAULTS }, debugMode: false });
    setDirty(true);
  };

  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} />
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "calc(100vh - 50px)" }}>
        <aside style={{ borderRight: "1px solid var(--line)", padding: "24px 16px" }}>
          <div className="tiny upper" style={{ color: "var(--ink-3)", marginBottom: 12 }}>Sections</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2, fontSize: 13 }}>
            <a style={{ padding: "6px 10px", background: "var(--bg-2)", borderRadius: 4 }}>Display & colors</a>
            <a style={{ padding: "6px 10px", color: "var(--ink-2)" }}>Notation</a>
            <a style={{ padding: "6px 10px", color: "var(--ink-2)" }}>Voicing defaults <span className="badge b-new" style={{ marginLeft: 4 }}>new</span></a>
            <a style={{ padding: "6px 10px", color: "var(--ink-2)" }}>Debug</a>
            <a style={{ padding: "6px 10px", color: "var(--ink-2)" }}>Account</a>
          </div>
        </aside>
        <div style={{ padding: "32px 40px", maxWidth: 920 }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Display</div>
          <h3 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 32, margin: "6px 0 24px", fontWeight: 500 }}>How chords appear.</h3>

          <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 24, alignItems: "start", borderBottom: "1px solid var(--line)", paddingBottom: 24 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>Chord symbol style</div>
              <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 4 }}>Affects display + export. Internal symbols always canonical.</div>
            </div>
            <div>
              <div className="seg" style={{ marginBottom: 16 }}>
                <button className={pendingPrefs.chordMode === "jazz" ? "is-on" : ""} onClick={() => setMode("jazz")}>Jazz · Δ ø °</button>
                <button className={pendingPrefs.chordMode === "plain" ? "is-on" : ""} onClick={() => setMode("plain")}>Plain · maj7 m7♭5</button>
              </div>
              <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
                <div>
                  <div className="tiny upper" style={{ color: "var(--ink-3)" }}>preview</div>
                  <div style={{ fontFamily: "var(--t-chord)", fontSize: 32, marginTop: 4 }}>
                    {pendingPrefs.chordMode === "jazz"
                      ? "C△7 · F♯ø7 · B°7 · D−7"
                      : "Cmaj7 · F♯m7♭5 · Bdim7 · Dm7"
                    }
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 32 }}>
            <div className="tiny upper" style={{ color: "var(--amber)" }}>Key-center colors · your data</div>
            <h3 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 24, margin: "6px 0 16px", fontWeight: 500 }}>Pick a color for every key.</h3>
            <p style={{ fontSize: 13, color: "var(--ink-2)", margin: "0 0 16px", maxWidth: "60ch" }}>
              These persist to <code>UserPreferences.key_center_colors</code> and surface on every chord cell, key pill, and the analysis timeline. The brand will never override them.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              {Object.keys(window.HL_DATA.KEY_COLOR_DEFAULTS).filter(k => k.endsWith("maj")).map(k => (
                <div key={k} style={{ border: "1px solid var(--line)", borderRadius: 6, padding: 10, background: "var(--bg-1)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 14, height: 14, borderRadius: 3, background: pendingPrefs.keyColors[k] || window.HL_DATA.KEY_COLOR_DEFAULTS[k] }}></span>
                    <span style={{ fontSize: 13 }}>{k}</span>
                  </div>
                  <input
                    type="text"
                    className="input"
                    value={pendingPrefs.keyColors[k] || window.HL_DATA.KEY_COLOR_DEFAULTS[k]}
                    onChange={e => setColor(k, e.target.value)}
                    style={{ width: "100%", marginTop: 6, fontFamily: "var(--t-mono)", fontSize: 10, height: 24 }}
                  />
                </div>
              ))}
            </div>
            <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 10 }}>
              Minor keys inherit major-key hue at lower lightness · 24 entries total · only 12 majors editable in this preview.
            </div>
          </div>

          <div style={{ marginTop: 32, padding: "20px 0", borderTop: "1px solid var(--line)" }}>
            <div className="tiny upper" style={{ color: "var(--amber)", marginBottom: 12 }}>Debug</div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
              <input type="checkbox" checked={pendingPrefs.debugMode} onChange={e => setDebug(e.target.checked)} />
              Enable HLDebug overlay on song.html (logs to <code>window.HLDebug.log()</code>)
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 32 }}>
            <button className="btn btn--ghost" onClick={reset}>Reset to defaults</button>
            <button className="btn" onClick={() => { setPendingPrefs(prefs); setDirty(false); }}>Cancel</button>
            <button className="btn btn--primary" disabled={!dirty} style={!dirty ? { opacity: 0.5, cursor: "not-allowed" } : {}} onClick={save}>Save preferences</button>
          </div>
          <div className="tiny" style={{ textAlign: "right", marginTop: 8, color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>PUT /api/v1/preferences · Authorization: Bearer ...</div>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   AUDIT page
   --------------------------------------------------------------------- */
function Audit({ song, route, onNavigate, toast }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} songTitle={song.title} />
      <div className="meta-strip">
        <div className="item"><span className="lbl">song</span><span className="val" style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 18 }}>{song.title}</span></div>
        <div className="item"><span className="lbl">id</span><span className="val" style={{ fontFamily: "var(--t-mono)" }}>{song.id}</span></div>
        <div className="item"><span className="lbl">imports</span><span className="val">{song.importHistory.length}</span></div>
        <div className="item"><span className="lbl">measures</span><span className="val">{song.measureCount}</span></div>
        <div className="item"><span className="lbl">chords</span><span className="val">{song.chordCount}</span></div>
        <div className="item" style={{ marginLeft: "auto" }}>
          <button className="btn btn--sm" onClick={() => toast("Re-parsing notes from raw_xml…", { meta:"POST /imports/score/reparse-notes" })}>Reparse notes</button>
          <button className="btn btn--sm" style={{ marginLeft: 6 }} onClick={() => onNavigate({ name: "song", id: song.id })}>← back to song</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderTop: "1px solid var(--line)" }}>
        <div style={{ padding: 24, borderRight: "1px solid var(--line)" }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Import history</div>
          <table className="tbl" style={{ marginTop: 8 }}>
            <thead><tr><th>v</th><th>When</th><th>Source</th><th>Format</th><th style={{ textAlign: "right" }}>Chords</th><th style={{ textAlign: "right" }}>Notes</th><th>Status</th></tr></thead>
            <tbody>
              {song.importHistory.map(h => (
                <tr key={h.v}>
                  <td className="t-mono">{h.v}</td>
                  <td className="t-mono">{h.when}</td>
                  <td className="t-mono" style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={h.source}>{h.source}</td>
                  <td>{h.format}</td>
                  <td className="t-mono" style={{ textAlign: "right" }}>{h.chords}</td>
                  <td className="t-mono" style={{ textAlign: "right" }}>{h.notes}</td>
                  <td><span className="tiny" style={{ color: h.warningCount > 0 ? "var(--amber)" : "var(--green)" }}>{h.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <pre style={{ marginTop: 16, fontSize: 11, lineHeight: 1.6 }}>{`[${song.importHistory[0]?.when || "—"}] parser=score_v3.2 file=${song.sourceFileName}
  parsed ${song.measureCount} measures, ${song.chordCount} chords${song.hasNotes ? `, notes captured` : ""}
  warning m.7  → chord_symbol low-confidence 0.62, kept
  warning m.15 → key signature change detected, KeyRegions row pending
  warning m.23 → fill-forward applied to empty measure (BUG-007)
  raw_xml stored ${song.hasXml ? "✓" : "✗"}
  has_note_data=${song.hasNotes ? 1 : 0}  has_lyrics=${song.hasLyrics ? 1 : 0}`}</pre>
        </div>
        <div style={{ padding: 24 }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Decorations · per measure</div>
          <table className="tbl" style={{ marginTop: 8, fontSize: 12 }}>
            <thead><tr><th>m.</th><th>type</th><th>value</th><th>beat</th></tr></thead>
            <tbody>
              <tr><td className="t-mono">1</td><td>tempo</td><td>{song.tempo} "{song.genre}"</td><td className="t-mono">1.0</td></tr>
              <tr><td className="t-mono">1</td><td>key sig</td><td>{song.detectedKey}</td><td className="t-mono">1.0</td></tr>
              <tr><td className="t-mono">1</td><td>time sig</td><td>{song.timeSig}</td><td className="t-mono">1.0</td></tr>
              {song.keyRegions.slice(1).map((r, i) => (
                <tr key={i}><td className="t-mono">{r.startMeasure}</td><td>key sig</td><td>{r.key}</td><td className="t-mono">1.0</td></tr>
              ))}
            </tbody>
          </table>
          <div className="tiny upper" style={{ color: "var(--amber)", marginTop: 18 }}>Schema-only tables</div>
          <div style={{ padding: 10, background: "var(--bg-1)", border: "1px solid var(--line)", borderRadius: 4, marginTop: 6, color: "var(--ink-3)", fontFamily: "var(--t-mono)", fontSize: 11, lineHeight: 1.6 }}>
            song_dynamics · 0 rows<br />
            song_note_articulations · 0 rows
          </div>
        </div>
      </div>
      <div style={{ borderTop: "1px solid var(--line)", padding: "16px 24px", display: "flex", justifyContent: "space-between", fontFamily: "var(--t-mono)", fontSize: 11, color: "var(--ink-3)" }}>
        <span>GET /api/v1/songs/{song.id}/audit · 200 · 64ms</span>
        <span>GET /api/v1/songs/{song.id}/imports · 200 · 18ms</span>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   LAB — deemphasized stubs
   --------------------------------------------------------------------- */
function Lab({ route, onNavigate, toast }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} />
      <div style={{ padding: "32px 32px 16px" }}>
        <div className="tiny upper" style={{ color: "var(--amber)" }}>Lab</div>
        <h2 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 34, margin: "6px 0 6px", fontWeight: 500 }}>Experimental features.</h2>
        <p style={{ color: "var(--ink-2)", fontSize: 13, margin: "0 0 24px", maxWidth: 70 + "ch" }}>
          Stubbed code paths that have produced zero usage to date. Kept available behind one click while CAI decides whether to revive, redesign, or deprecate.
        </p>
      </div>
      <div style={{ padding: "0 32px 60px", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, maxWidth: 1100 }}>
        {[
          { title: "Riffs library", sub: "GET /riffs/ · 10 hardcoded patterns", verdict: "KEEP", color: "var(--green)", desc: "Browse and play curated jazz riffs (ii-V-I, bebop, tritone sub, Coltrane changes…)." },
          { title: "Quiz", sub: "QuizAttempts · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Chord-identification quiz scoped to a song. Move here from top-level until usage proves itself." },
          { title: "Progress tracking", sub: "UserSongProgress · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Per-song last-practiced + 5-point mastery rating. Reduce surface; surface only on song detail." },
          { title: "AI Improvisation", sub: "ImprovisationSessions · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "AI generates an improvised line over the chord changes. Low usage to date reflects insufficient context plumbing (the model didn't have enough to work with), not a wrong idea. Iterate on prompt + RAG context, then re-evaluate." },
          { title: "RLHF sessions", sub: "rlhf_sessions · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Apply approved overrides as a batch, revert as a batch. Per-chord edits + theory-chat outcomes cover the same surface today, but a structured RLHF cycle becomes useful once AI context improves and the user wants to compare a whole analysis pass against the prior one." },
          { title: "WebMIDI input", sub: "GET /midi/webmidi-check", verdict: "WIRE", color: "var(--ink-blue)", desc: "Web MIDI is plugged in but no UI calls it. Could power live chord identification at the piano." },
        ].map((it, i) => (
          <div key={i} style={{ border: "1px solid var(--line)", borderRadius: 6, padding: 18, background: "var(--bg-1)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ margin: 0, fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22, fontWeight: 500 }}>{it.title}</h3>
              <span className="badge" style={{ color: it.color, borderColor: it.color }}>{it.verdict}</span>
            </div>
            <div className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>{it.sub}</div>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-1)" }}>{it.desc}</p>
            <div style={{ marginTop: 6 }}>
              <button className="btn btn--sm" onClick={() => toast(`${it.title} · clicked`, { meta: "no-op in prototype" })}>Open →</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   IMPORT MODAL — score / OMR / batch
   --------------------------------------------------------------------- */
function ImportModal({ onClose, onImport }) {
  const [pipeline, setPipeline] = useStateV("omr");
  const [stage, setStage] = useStateV("drop");   // drop | uploading | parsing | preview
  const [fileName, setFileName] = useStateV("");
  const [songName, setSongName] = useStateV("");
  const [progress, setProgress] = useStateV(0);

  const startMockImport = (name) => {
    setFileName(name);
    setSongName(name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ").replace(/\bv\d+\b/i, "").trim());
    setStage("uploading");
    setProgress(0);
    let p = 0;
    const tick = setInterval(() => {
      p += 12;
      setProgress(Math.min(p, 100));
      if (p >= 100) {
        clearInterval(tick);
        setStage("parsing");
        setTimeout(() => setStage("preview"), 900);
      }
    }, 120);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "oklch(.09 .005 70 / .75)", zIndex: 700, display: "flex", justifyContent: "center", alignItems: "flex-start", paddingTop: 48 }} onClick={onClose}>
      <div style={{ width: 880, background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: 8, boxShadow: "var(--sh-3)", overflow: "hidden" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", padding: "14px 20px", borderBottom: "1px solid var(--line)" }}>
          <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20 }}>Import a lead sheet</div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <div className="seg">
              <button className={pipeline === "score" ? "is-on" : ""} onClick={() => { setPipeline("score"); setStage("drop"); }}>Score file</button>
              <button className={pipeline === "omr" ? "is-on" : ""} onClick={() => { setPipeline("omr"); setStage("drop"); }}>OMR · image / PDF</button>
              <button className={pipeline === "batch" ? "is-on" : ""} onClick={() => { setPipeline("batch"); setStage("drop"); }}>Batch ZIP</button>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={onClose}>✕</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 420 }}>
          {/* LEFT */}
          <div style={{ padding: 24, borderRight: "1px solid var(--line)" }}>
            <div className="tiny upper" style={{ color: "var(--ink-3)" }}>
              {pipeline === "score" && "Drop .mscz / .midi / .musicxml"}
              {pipeline === "omr" && "Drop a PDF or image"}
              {pipeline === "batch" && "Drop a ZIP of score files"}
            </div>

            {stage === "drop" ? (
              <div style={{ marginTop: 8, border: "1.5px dashed var(--line-2)", borderRadius: 6, padding: 24, textAlign: "center", background: "var(--bg-0)" }}>
                <div style={{ fontSize: 14, color: "var(--ink-1)" }}>Drag a file here, or:</div>
                <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
                  {pipeline === "omr" && [
                    "corcovado-fakebook.pdf",
                    "stella-fakebook-p1.jpg",
                  ].map(n => (
                    <button key={n} className="btn btn--sm" onClick={() => startMockImport(n)}>Use sample: {n}</button>
                  ))}
                  {pipeline === "score" && [
                    "blue-bossa.mscz",
                    "satin-doll.musicxml",
                  ].map(n => (
                    <button key={n} className="btn btn--sm" onClick={() => startMockImport(n)}>Use sample: {n}</button>
                  ))}
                  {pipeline === "batch" && (
                    <button className="btn btn--sm" onClick={() => startMockImport("jobim-bundle.zip")}>Use sample: jobim-bundle.zip</button>
                  )}
                </div>
                <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 14, fontFamily: "var(--t-mono)" }}>
                  max 25 MB · sha256 hashed for duplicate detection
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 8, border: "1px solid var(--line)", borderRadius: 6, padding: 20, background: "var(--bg-0)" }}>
                <div style={{ fontSize: 14, color: "var(--ink-1)" }}>{fileName}</div>
                <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 4, fontFamily: "var(--t-mono)" }}>1.4 MB · 2 pages · fs-modified 2024-11-04</div>
                <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 14, fontFamily: "var(--t-mono)", textTransform: "uppercase", letterSpacing: ".1em" }}>{pipeline === "omr" ? "Vision pipeline" : "Score pipeline"}</div>
                <ol style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13, color: "var(--ink-1)", lineHeight: 1.7 }}>
                  <li style={{ color: stage === "uploading" ? "var(--amber)" : "var(--green)" }}>{stage === "uploading" ? `▸ Upload (${progress}%)` : "✓ Upload"}</li>
                  <li style={{ color: stage === "parsing" ? "var(--amber)" : (stage === "preview" ? "var(--green)" : "var(--ink-3)") }}>
                    {stage === "parsing" ? "▸ " : (stage === "preview" ? "✓ " : "  ")}
                    {pipeline === "omr" ? "Page → image extraction" : "Parse score → measures + chords"}
                  </li>
                  <li style={{ color: stage === "preview" ? "var(--green)" : "var(--ink-3)" }}>
                    {stage === "preview" ? "✓ " : "  "}{pipeline === "omr" ? "Claude Vision · chord detection" : "Detect key + form"}
                  </li>
                  <li style={{ color: "var(--ink-3)" }}>  {pipeline === "omr" ? "Vision pass 2 · structure + key" : "Database commit"}</li>
                </ol>
              </div>
            )}
          </div>

          {/* RIGHT — preview */}
          <div style={{ padding: 24 }}>
            {stage !== "preview" ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-3)", textAlign: "center" }}>
                <div>
                  <div className="tiny upper">Preview appears here</div>
                  <p style={{ fontSize: 13, marginTop: 8 }}>Once parsing completes you can edit any low-confidence chord before committing.</p>
                </div>
              </div>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                  <div>
                    <div className="tiny upper" style={{ color: "var(--amber)" }}>Preview · before commit</div>
                    <h4 style={{ margin: "6px 0 0", fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22, fontWeight: 500 }}>
                      <input className="input" value={songName} onChange={e => setSongName(e.target.value)} style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22, fontWeight: 500, width: 220, padding: "0 6px" }} />
                      <span style={{ color: "var(--ink-2)", fontSize: 14, marginLeft: 8 }}>A. C. Jobim · B♭ maj · 32 bars · 64 chords</span>
                    </h4>
                  </div>
                  <span className="pill pill--confidence">parser · v3.2 · 88%</span>
                </div>
                <div className="chord-grid chord-grid--4" style={{ marginTop: 14 }}>
                  <div className="chord-cell k-Bb"><div className="key-strip"></div><div className="meas">m.3</div><div className="sym">Am7</div><div className="roman minor">vii<sup>7</sup>/iii</div></div>
                  <div className="chord-cell k-Bb"><div className="key-strip"></div><div className="meas">m.4</div><div className="sym">D7♭9</div><div className="roman major">V<sup>7♭9</sup>/iii</div></div>
                  <div className="chord-cell k-Bb"><div className="key-strip"></div><div className="meas">m.5</div><div className="sym">Gm7</div><div className="roman minor">vi<sup>7</sup></div></div>
                  <div className="chord-cell k-Bb"><div className="key-strip"></div><div className="meas">m.6</div><div className="sym">G♭7</div><div className="roman major">♭V<sup>7</sup></div></div>
                </div>
                <div style={{ marginTop: 14, padding: "10px 12px", border: "1px solid var(--amber)", borderRadius: 6, background: "oklch(.79 .13 75 / .08)", color: "var(--ink-1)", fontSize: 13 }}>
                  <strong style={{ color: "var(--amber)" }}>2 warnings</strong>
                  <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                    <li>m.7 — ambiguous symbol "F7♭9?" · accepted with conf 0.62</li>
                    <li>m.15 — possible modulation to E♭ not yet detected</li>
                  </ul>
                </div>
              </>
            )}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderTop: "1px solid var(--line)", background: "var(--bg-0)" }}>
          <div className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>
            POST /api/v1/imports/{pipeline}/preview · then /import on commit
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
            {stage === "preview" && <button className="btn" onClick={() => { setStage("uploading"); setProgress(0); setTimeout(() => setStage("preview"), 1200); }}>Re-run preview</button>}
            <button className="btn btn--primary" disabled={stage !== "preview"} style={stage !== "preview" ? { opacity: 0.4, cursor: "not-allowed" } : {}} onClick={() => onImport(songName)}>Import to library</button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { HLLibrary: Library, HLSettings: Settings, HLAudit: Audit, HLLab: Lab });
