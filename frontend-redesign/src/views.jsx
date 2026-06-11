/* =====================================================================
   HarmonyLab — Library, Settings, Audit, Lab, Import modal
   HM44.1: All writes wired. Mock mode removed.
   ===================================================================== */

const { useState: useStateV, useEffect: useEffectV, useMemo: useMemoV, useRef: useRefV } = React;

/* ---------------------------------------------------------------------
   Column-header sort + multi-select filter primitives
   --------------------------------------------------------------------- */
function SortArrows({ dir, onToggle }) {
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
        <div style={{ position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 40, minWidth: 200, maxHeight: 320, overflow: "auto", background: "var(--bg-2)", border: "1px solid var(--line-2)", borderRadius: 4, boxShadow: "var(--sh-3)", padding: 6 }} onClick={(e) => e.stopPropagation()}>
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
function Library({ route, onNavigate, prefs, toast }) {
  const [q, setQ] = useStateV("");
  const [selected, setSelected] = useStateV(new Set());
  const [importOpen, setImportOpen] = useStateV(false);
  const [confirmDel, setConfirmDel] = useStateV(false);
  const [sort, setSort] = useStateV({ key: null, dir: null });
  const [filters, setFilters] = useStateV({});
  const [libraryKey, setLibraryKey] = useStateV(0);  // bump to refresh

  const api = hlUseApi();
  const { data: liveRows, loading, error } = hlUseLibraryRows();
  const all = liveRows || [];

  const filterOptions = useMemoV(() => {
    const opt = (key) => {
      const m = new Map();
      for (const r of all) { const v = key(r); m.set(v, (m.get(v) || 0) + 1); }
      return [...m.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0]))).map(([value, count]) => ({ value, label: String(value ?? "—"), count }));
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
    setFilters(f => { const next = { ...f }; if (!vals || vals.size === 0) delete next[col]; else next[col] = vals; return next; });
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
        title: r => r.title.toLowerCase(), composer: r => r.composer.toLowerCase(), genre: r => r.genre || "",
        key: r => r.key, form: r => r.form, measureCount: r => r.measureCount, chordCount: r => r.chordCount,
        importedAt: r => r.importedAt, fsModifiedAt: r => r.fsModifiedAt || "",
        dataScore: r => (r.hasXml?4:0)+(r.hasNotes?2:0)+(r.hasLyrics?1:0)+(r.overrideCount>0?0.5:0),
      }[sort.key] || (r => r[sort.key]);
      xs = [...xs].sort((a, b) => { const A = getter(a), B = getter(b); if (A < B) return sort.dir === "asc" ? -1 : 1; if (A > B) return sort.dir === "asc" ? 1 : -1; return 0; });
    }
    return xs;
  }, [q, filters, sort, all]);

  const stats = useMemoV(() => ({
    total: all.length, withXml: all.filter(r => r.hasXml).length,
    withLyrics: all.filter(r => r.hasLyrics).length, withOverrides: all.filter(r => r.overrideCount > 0).length,
  }), [all]);

  const toggle = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const allChecked = rows.length > 0 && rows.every(r => selected.has(r.id));
  const toggleAll = () => setSelected(allChecked ? new Set() : new Set(rows.map(r => r.id)));
  const activeFilterCount = Object.keys(filters).length;

  const doBulkDelete = async () => {
    const ids = [...selected];
    const n = ids.length;
    setSelected(new Set());
    setConfirmDel(false);
    try {
      const qs = ids.map(id => `song_ids=${id}`).join("&");
      await api.fetcher(`/api/v1/songs/bulk/delete?${qs}`, { method: "DELETE" });
      toast(`Deleted ${n} song${n > 1 ? "s" : ""}`, { meta: `DELETE /songs/bulk/delete · 200` });
      setLibraryKey(k => k + 1);  // force re-fetch
      window.location.reload();
    } catch (e) {
      toast(`Delete failed: ${e.message}`, { level: "error" });
    }
  };

  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} />

      {loading && !all.length && <HLLoadingState what="library" />}
      {error && !all.length && <HLErrorState error={error} />}
      {(!loading || all.length > 0) && (
        <React.Fragment>
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
              {activeFilterCount > 0 && <button className="btn btn--ghost" onClick={() => setFilters({})}>Clear {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""}</button>}
              {sort.key && <button className="btn btn--ghost" onClick={() => setSort({ key: null, dir: null })}>Clear sort</button>}
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
                  <SortableHeader label="Data" sortKey="dataScore" sort={sort} onSort={setSort} align="right"
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
                const dataTags = [r.hasXml && "XML", r.hasNotes && "NOTES", r.hasLyrics && "LYRICS", r.overrideCount > 0 && `${r.overrideCount} override${r.overrideCount > 1 ? "s" : ""}`].filter(Boolean);
                return (
                  <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onNavigate({ name: "song", id: r.id })}>
                    <td onClick={e => e.stopPropagation()}><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} /></td>
                    <td className="t-title">{r.title}</td>
                    <td className="t-composer">{r.composer}</td>
                    <td className="t-composer" style={{ color: "var(--ink-2)" }}>{r.genre || "—"}</td>
                    <td><span className="pill pill--key" style={{ borderColor: kvar, color: kvar }}><span className="swatch" style={{ background: kvar }}></span>{r.key}</span></td>
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
            <div className="tiny">{selected.size} selected · {rows.length} of {all.length} shown{sort.key && <> · sorted by <strong style={{ color: "var(--amber)" }}>{sort.key} {sort.dir === "asc" ? "↑" : "↓"}</strong></>}{activeFilterCount > 0 && <> · {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""} active</>}</div>
            <div className="tiny" style={{ color: "var(--ink-3)" }}>GET /api/v1/songs/?limit=200 · {rows.length} results</div>
          </div>

          {importOpen && <ImportModal onClose={() => setImportOpen(false)} onImport={(name, songId) => { setImportOpen(false); toast(`Imported "${name}" · song #${songId}`, { meta: "POST /imports/…/import · 200" }); window.location.reload(); }} toast={toast} />}
          {confirmDel && (
            <HLConfirmModal
              title={`Delete ${selected.size} song${selected.size > 1 ? "s" : ""}?`}
              body="This cascades through 14 child tables: chords, measures, sections, notes, lyrics, imports. Cannot be undone."
              confirmLabel="Delete"
              danger
              onConfirm={doBulkDelete}
              onCancel={() => setConfirmDel(false)}
            />
          )}
        </React.Fragment>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   SETTINGS
   HM44.1: loads prefs from server, saves via PUT /api/v1/preferences
   --------------------------------------------------------------------- */
function Settings({ route, onNavigate, prefs, setPrefs, toast }) {
  const api = hlUseApi();
  const { data: serverPrefs } = hlUsePreferences();
  const [pendingPrefs, setPendingPrefs] = useStateV(prefs);
  const [dirty, setDirty] = useStateV(false);
  const [saving, setSaving] = useStateV(false);

  // Sync server prefs into local state on load
  useEffectV(() => {
    if (serverPrefs) {
      const merged = {
        chordMode: serverPrefs.chord_symbol_mode || "jazz",
        keyColors: serverPrefs.key_center_colors || { ...window.HL_DATA.KEY_COLOR_DEFAULTS },
        debugMode: !!serverPrefs.debug_mode,
        defaultVoicing: serverPrefs.default_voicing_notation || "",
      };
      setPendingPrefs(merged);
      setPrefs(merged);
    }
  }, [serverPrefs]);

  const setMode = (mode) => { setPendingPrefs(p => ({ ...p, chordMode: mode })); setDirty(true); };
  const setColor = (key, value) => { setPendingPrefs(p => ({ ...p, keyColors: { ...p.keyColors, [key]: value } })); setDirty(true); };
  const setDebug = (val) => { setPendingPrefs(p => ({ ...p, debugMode: val })); setDirty(true); };
  const setVoicing = (val) => { setPendingPrefs(p => ({ ...p, defaultVoicing: val })); setDirty(true); };

  const save = async () => {
    setSaving(true);
    try {
      await api.fetcher("/api/v1/preferences", {
        method: "PUT",
        body: JSON.stringify({
          chord_symbol_mode: pendingPrefs.chordMode,
          key_center_colors: pendingPrefs.keyColors,
          debug_mode: pendingPrefs.debugMode,
          default_voicing_notation: pendingPrefs.defaultVoicing || null,
        }),
      });
      setPrefs(pendingPrefs);
      setDirty(false);
      toast("Preferences saved", { meta: "PUT /api/v1/preferences · 200" });
    } catch (e) {
      toast(`Save failed: ${e.message}`, { level: "error" });
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    setPendingPrefs({ chordMode: "jazz", keyColors: { ...window.HL_DATA.KEY_COLOR_DEFAULTS }, debugMode: false, defaultVoicing: "" });
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
              <div>
                <div className="tiny upper" style={{ color: "var(--ink-3)" }}>preview</div>
                <div style={{ fontFamily: "var(--t-chord)", fontSize: 32, marginTop: 4 }}>
                  {pendingPrefs.chordMode === "jazz" ? "C△7 · F♯ø7 · B°7 · D−7" : "Cmaj7 · F♯m7♭5 · Bdim7 · Dm7"}
                </div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 32 }}>
            <div className="tiny upper" style={{ color: "var(--amber)" }}>Key-center colors · your data</div>
            <h3 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 24, margin: "6px 0 16px", fontWeight: 500 }}>Pick a color for every key.</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              {Object.keys(window.HL_DATA.KEY_COLOR_DEFAULTS).filter(k => k.endsWith("maj")).map(k => (
                <div key={k} style={{ border: "1px solid var(--line)", borderRadius: 6, padding: 10, background: "var(--bg-1)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 14, height: 14, borderRadius: 3, background: pendingPrefs.keyColors?.[k] || window.HL_DATA.KEY_COLOR_DEFAULTS[k] }}></span>
                    <span style={{ fontSize: 13 }}>{k}</span>
                  </div>
                  <input type="text" className="input" value={pendingPrefs.keyColors?.[k] || window.HL_DATA.KEY_COLOR_DEFAULTS[k]} onChange={e => setColor(k, e.target.value)} style={{ width: "100%", marginTop: 6, fontFamily: "var(--t-mono)", fontSize: 10, height: 24 }} />
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 32, padding: "20px 0", borderTop: "1px solid var(--line)" }}>
            <div className="tiny upper" style={{ color: "var(--amber)", marginBottom: 12 }}>Voicing default</div>
            <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 16, alignItems: "start" }}>
              <div style={{ fontSize: 13 }}>Default voicing label<div className="tiny" style={{ color: "var(--ink-3)" }}>e.g. "rootless A", "drop-2", "shell"</div></div>
              <input className="input" value={pendingPrefs.defaultVoicing || ""} onChange={e => setVoicing(e.target.value)} placeholder="leave blank for none" style={{ width: 240 }} />
            </div>
          </div>

          <div style={{ marginTop: 24, padding: "20px 0", borderTop: "1px solid var(--line)" }}>
            <div className="tiny upper" style={{ color: "var(--amber)", marginBottom: 12 }}>Debug</div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
              <input type="checkbox" checked={!!pendingPrefs.debugMode} onChange={e => setDebug(e.target.checked)} />
              Enable HLDebug overlay (logs to window.HLDebug)
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 32 }}>
            <button className="btn btn--ghost" onClick={reset}>Reset to defaults</button>
            <button className="btn" onClick={() => { setPendingPrefs(prefs); setDirty(false); }}>Cancel</button>
            <button className="btn btn--primary" disabled={!dirty || saving} style={(!dirty || saving) ? { opacity: 0.5, cursor: "not-allowed" } : {}} onClick={save}>{saving ? "Saving…" : "Save preferences"}</button>
          </div>
          <div className="tiny" style={{ textAlign: "right", marginTop: 8, color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>PUT /api/v1/preferences</div>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   AUDIT
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
          <button className="btn btn--sm" onClick={() => toast("Re-parsing notes from raw_xml…", { meta: "POST /imports/score/reparse-notes" })}>Reparse notes</button>
          <button className="btn btn--sm" style={{ marginLeft: 6 }} onClick={() => onNavigate({ name: "song", id: song.id })}>← back to song</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderTop: "1px solid var(--line)" }}>
        <div style={{ padding: 24, borderRight: "1px solid var(--line)" }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Import history</div>
          <table className="tbl" style={{ marginTop: 8 }}>
            <thead><tr><th>v</th><th>When</th><th>Source</th><th>Format</th><th style={{ textAlign: "right" }}>Chords</th><th style={{ textAlign: "right" }}>Notes</th><th>Status</th></tr></thead>
            <tbody>
              {(song.importHistory || []).map((h, i) => (
                <tr key={i}>
                  <td className="t-mono">{h.version_number || h.v || 1}</td>
                  <td className="t-mono">{(h.imported_at || h.when || "").slice(0, 16)}</td>
                  <td className="t-mono" style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={h.original_filename || h.source}>{h.original_filename || h.source}</td>
                  <td>{h.import_format || h.format}</td>
                  <td className="t-mono" style={{ textAlign: "right" }}>{h.chord_count_imported ?? h.chords ?? "—"}</td>
                  <td className="t-mono" style={{ textAlign: "right" }}>{h.note_count_imported ?? h.notes ?? "—"}</td>
                  <td><span className="tiny" style={{ color: h.import_status === "success" || h.status === "success" ? "var(--green)" : "var(--amber)" }}>{h.import_status || h.status || "?"}</span></td>
                </tr>
              ))}
              {(song.importHistory || []).length === 0 && (
                <tr><td colSpan={7} className="tiny" style={{ color: "var(--ink-3)", padding: "12px 0" }}>No import records found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: 24 }}>
          <div className="tiny upper" style={{ color: "var(--amber)" }}>Song metadata</div>
          <table className="tbl" style={{ marginTop: 8, fontSize: 12 }}>
            <thead><tr><th>field</th><th>value</th></tr></thead>
            <tbody>
              <tr><td>Detected key</td><td className="t-mono">{song.detectedKey}</td></tr>
              <tr><td>Time sig</td><td className="t-mono">{song.timeSig}</td></tr>
              <tr><td>Tempo</td><td className="t-mono">{song.tempo}</td></tr>
              <tr><td>Source file</td><td className="t-mono">{song.sourceFileName}</td></tr>
              <tr><td>Source type</td><td className="t-mono">{song.sourceFileType}</td></tr>
              <tr><td>has_raw_xml</td><td className="t-mono">{song.hasXml ? "✓" : "✗"}</td></tr>
              <tr><td>has_note_data</td><td className="t-mono">{song.hasNotes ? "✓" : "✗"}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div style={{ borderTop: "1px solid var(--line)", padding: "16px 24px", fontFamily: "var(--t-mono)", fontSize: 11, color: "var(--ink-3)" }}>
        GET /api/v1/songs/{song.id} + /audit
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   LAB
   --------------------------------------------------------------------- */
function Lab({ route, onNavigate, toast }) {
  return (
    <div className="app" style={{ minHeight: "100vh" }}>
      <HLTopbar route={route} onNavigate={onNavigate} />
      <div style={{ padding: "32px 32px 16px" }}>
        <div className="tiny upper" style={{ color: "var(--amber)" }}>Lab</div>
        <h2 style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 34, margin: "6px 0 6px", fontWeight: 500 }}>Experimental features.</h2>
        <p style={{ color: "var(--ink-2)", fontSize: 13, margin: "0 0 24px", maxWidth: "70ch" }}>
          Kept available behind one click. Revive candidates once context engineering matures.
        </p>
      </div>
      <div style={{ padding: "0 32px 60px", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, maxWidth: 1100 }}>
        {[
          { title: "Riffs library", sub: "GET /riffs/ · 10 hardcoded patterns", verdict: "KEEP", color: "var(--green)", desc: "Browse and play curated jazz riffs." },
          { title: "Quiz", sub: "QuizAttempts · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Chord-identification quiz scoped to a song." },
          { title: "Progress tracking", sub: "UserSongProgress · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Per-song last-practiced + 5-point mastery rating." },
          { title: "AI Improvisation", sub: "ImprovisationSessions · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "AI generates an improvised line over chord changes. Low usage reflects context plumbing limits, not wrong fit." },
          { title: "RLHF sessions", sub: "rlhf_sessions · 0 rows ever", verdict: "RETRY", color: "var(--amber)", desc: "Apply approved overrides as a batch. Useful once AI suggestion quality improves." },
          { title: "WebMIDI input", sub: "GET /midi/webmidi-check", verdict: "WIRE", color: "var(--ink-blue)", desc: "Web MIDI available but no UI calls it yet. Could power live chord ID at the piano." },
        ].map((it, i) => (
          <div key={i} style={{ border: "1px solid var(--line)", borderRadius: 6, padding: 18, background: "var(--bg-1)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ margin: 0, fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 22, fontWeight: 500 }}>{it.title}</h3>
              <span className="badge" style={{ color: it.color, borderColor: it.color }}>{it.verdict}</span>
            </div>
            <div className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>{it.sub}</div>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-1)" }}>{it.desc}</p>
            <button className="btn btn--sm" onClick={() => toast(`${it.title} · not yet wired`)}>Open →</button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =====================================================================
   IMPORT MODAL — real file upload wired to /api/v1/imports/*
   ===================================================================== */
function ImportModal({ onClose, onImport, toast }) {
  const api = hlUseApi();
  const [pipeline, setPipeline] = useStateV("omr");
  const [stage, setStage] = useStateV("drop");  // drop | uploading | parsing | preview | error
  const [file, setFile] = useStateV(null);
  const [fileName, setFileName] = useStateV("");
  const [songName, setSongName] = useStateV("");
  const [previewData, setPreviewData] = useStateV(null);
  const [progress, setProgress] = useStateV(0);
  const [errMsg, setErrMsg] = useStateV("");
  const [committing, setCommitting] = useStateV(false);
  const fileInputRef = useRefV(null);

  const ACCEPT = {
    score: ".mscz,.mscx,.musicxml,.xml,.mxl,.mid,.midi",
    omr: ".pdf,.jpg,.jpeg,.png,.svg",
    batch: ".zip",
  };

  const handleFile = async (f) => {
    if (!f) return;
    setFile(f);
    setFileName(f.name);
    setSongName(f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ").trim());
    setStage("uploading");
    setProgress(20);
    setErrMsg("");

    const fd = new FormData();
    fd.append("file", f);
    const endpoint = pipeline === "batch" ? "/api/v1/imports/batch" : `/api/v1/imports/${pipeline}/preview`;

    try {
      if (pipeline === "batch") {
        // batch has no preview step — go straight to commit
        setStage("parsing");
        setProgress(60);
        const result = await api.fetcher("/api/v1/imports/batch", { method: "POST", body: fd });
        setProgress(100);
        setStage("preview");
        setPreviewData({ batchResult: result });
      } else {
        setProgress(50);
        setStage("parsing");
        const preview = await api.fetcher(endpoint, { method: "POST", body: fd });
        setProgress(100);
        setPreviewData(preview.data ?? preview);
        const guessedTitle = (preview.data?.title ?? preview.title ?? f.name.replace(/\.[^.]+$/, "")).replace(/[-_]/g, " ").trim();
        if (guessedTitle) setSongName(guessedTitle);
        setStage("preview");
      }
    } catch (e) {
      setErrMsg(e.message || "Parse failed");
      setStage("error");
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onInputChange = (e) => {
    const f = e.target.files[0];
    if (f) handleFile(f);
  };

  const doCommit = async () => {
    if (!file) return;
    if (pipeline === "batch" && previewData?.batchResult) {
      // already committed during preview
      const r = previewData.batchResult;
      onImport(`${r.imported} songs from ZIP`, r.imported);
      return;
    }
    setCommitting(true);
    const fd = new FormData();
    fd.append("file", file);
    if (songName && pipeline !== "batch") {
      if (pipeline === "omr") fd.append("title_override", songName);
      else { fd.append("title", songName); }
    }
    try {
      const result = await api.fetcher(`/api/v1/imports/${pipeline}/import`, { method: "POST", body: fd });
      const id = result.song_id ?? result.id;
      const title = result.title || songName;
      onImport(title, id);
    } catch (e) {
      setErrMsg(e.message || "Import failed");
      setStage("error");
    } finally {
      setCommitting(false);
    }
  };

  const reset = () => { setStage("drop"); setFile(null); setFileName(""); setPreviewData(null); setErrMsg(""); setProgress(0); };

  const chordPreview = previewData?.chords_preview || previewData?.chords || [];
  const chordCount = previewData?.chord_count ?? chordPreview.length ?? 0;

  return (
    <div style={{ position: "fixed", inset: 0, background: "oklch(.09 .005 70 / .75)", zIndex: 700, display: "flex", justifyContent: "center", alignItems: "flex-start", paddingTop: 48 }} onClick={onClose}>
      <div style={{ width: 880, background: "var(--bg-1)", border: "1px solid var(--line-2)", borderRadius: 8, boxShadow: "var(--sh-3)", overflow: "hidden" }} onClick={e => e.stopPropagation()}>
        {/* header */}
        <div style={{ display: "flex", alignItems: "center", padding: "14px 20px", borderBottom: "1px solid var(--line)" }}>
          <div style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20 }}>Import a lead sheet</div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <div className="seg">
              <button className={pipeline === "score" ? "is-on" : ""} onClick={() => { setPipeline("score"); reset(); }}>Score file</button>
              <button className={pipeline === "omr" ? "is-on" : ""} onClick={() => { setPipeline("omr"); reset(); }}>OMR · image / PDF</button>
              <button className={pipeline === "batch" ? "is-on" : ""} onClick={() => { setPipeline("batch"); reset(); }}>Batch ZIP</button>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={onClose}>✕</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 420 }}>
          {/* LEFT */}
          <div style={{ padding: 24, borderRight: "1px solid var(--line)" }}>
            <div className="tiny upper" style={{ color: "var(--ink-3)" }}>
              {pipeline === "score" && "Drop .mscz / .mscx / .musicxml / .mid"}
              {pipeline === "omr" && "Drop a PDF or image"}
              {pipeline === "batch" && "Drop a ZIP of score files"}
            </div>

            {stage === "drop" ? (
              <div
                style={{ marginTop: 8, border: "1.5px dashed var(--line-2)", borderRadius: 6, padding: 24, textAlign: "center", background: "var(--bg-0)", cursor: "pointer" }}
                onDrop={onDrop} onDragOver={e => e.preventDefault()} onClick={() => fileInputRef.current?.click()}
              >
                <div style={{ fontSize: 14, color: "var(--ink-1)" }}>Drag a file here, or click to browse</div>
                <div className="tiny" style={{ color: "var(--ink-3)", marginTop: 14, fontFamily: "var(--t-mono)" }}>max 25 MB · sha256 hashed for duplicate detection</div>
                <input ref={fileInputRef} type="file" accept={ACCEPT[pipeline]} style={{ display: "none" }} onChange={onInputChange} />
              </div>
            ) : (
              <div style={{ marginTop: 8, border: "1px solid var(--line)", borderRadius: 6, padding: 20, background: "var(--bg-0)" }}>
                <div style={{ fontSize: 14, color: "var(--ink-1)" }}>{fileName}</div>
                <ol style={{ margin: "10px 0 0", paddingLeft: 18, fontSize: 13, color: "var(--ink-1)", lineHeight: 1.7 }}>
                  <li style={{ color: (stage === "uploading") ? "var(--amber)" : "var(--green)" }}>{stage === "uploading" ? `▸ Upload (${progress}%)` : "✓ Upload"}</li>
                  <li style={{ color: stage === "parsing" ? "var(--amber)" : (stage === "preview" ? "var(--green)" : "var(--ink-3)") }}>
                    {stage === "parsing" ? "▸ " : (stage === "preview" ? "✓ " : "  ")}
                    {pipeline === "omr" ? "Claude Vision · chord detection" : "Parse score → chords"}
                  </li>
                  <li style={{ color: stage === "preview" ? "var(--green)" : "var(--ink-3)" }}>{stage === "preview" ? "✓ " : "  "}Ready to commit</li>
                </ol>
                {stage === "error" && <div style={{ marginTop: 10, color: "var(--rose)", fontSize: 12 }}>{errMsg}</div>}
              </div>
            )}

            {stage !== "drop" && stage !== "error" && (
              <button className="btn btn--ghost btn--sm" style={{ marginTop: 12 }} onClick={reset}>← Try a different file</button>
            )}
          </div>

          {/* RIGHT */}
          <div style={{ padding: 24 }}>
            {stage !== "preview" ? (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-3)", textAlign: "center" }}>
                <div>
                  <div className="tiny upper">Preview appears here</div>
                  <p style={{ fontSize: 13, marginTop: 8 }}>Parsed chords and metadata will show here.</p>
                </div>
              </div>
            ) : previewData?.batchResult ? (
              <div>
                <div className="tiny upper" style={{ color: "var(--amber)" }}>Batch result</div>
                <div style={{ marginTop: 12, fontSize: 14 }}>
                  <div><strong style={{ color: "var(--green)" }}>{previewData.batchResult.imported}</strong> imported</div>
                  <div style={{ color: "var(--ink-3)" }}>{previewData.batchResult.skipped_duplicate || 0} skipped (duplicate)</div>
                  <div style={{ color: "var(--rose)" }}>{previewData.batchResult.failed || 0} failed</div>
                </div>
                {(previewData.batchResult.files || []).slice(0, 8).map((f, i) => (
                  <div key={i} className="tiny" style={{ marginTop: 6, color: f.status === "imported" ? "var(--green)" : f.status === "skipped" ? "var(--ink-3)" : "var(--rose)" }}>
                    {f.filename} · {f.status}
                  </div>
                ))}
              </div>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                  <div>
                    <div className="tiny upper" style={{ color: "var(--amber)" }}>Preview · before commit</div>
                    <h4 style={{ margin: "6px 0 0", fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20, fontWeight: 500 }}>
                      <input className="input" value={songName} onChange={e => setSongName(e.target.value)} style={{ fontFamily: "var(--t-display)", fontStyle: "italic", fontSize: 20, fontWeight: 500, width: 220, padding: "0 6px" }} />
                      <span style={{ color: "var(--ink-2)", fontSize: 13, marginLeft: 8 }}>
                        {[previewData?.key, previewData?.time_signature, `${chordCount} chords`].filter(Boolean).join(" · ")}
                      </span>
                    </h4>
                  </div>
                  {previewData?.format && <span className="pill pill--confidence">{previewData.format}</span>}
                </div>
                {chordPreview.length > 0 && (
                  <div className="chord-grid chord-grid--4" style={{ marginTop: 14 }}>
                    {chordPreview.slice(0, 12).map((c, i) => (
                      <div key={i} className="chord-cell">
                        <div className="meas" style={{ fontSize: 9, color: "var(--ink-3)" }}>m.{c.measure || c.measure_number || i + 1}</div>
                        <div className="sym">{c.symbol || c.chord_symbol || c}</div>
                      </div>
                    ))}
                  </div>
                )}
                {previewData?.warning && (
                  <div style={{ marginTop: 10, padding: "8px 12px", border: "1px solid var(--amber)", borderRadius: 6, color: "var(--amber)", fontSize: 12 }}>{previewData.warning}</div>
                )}
              </>
            )}
          </div>
        </div>

        {/* footer */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderTop: "1px solid var(--line)", background: "var(--bg-0)" }}>
          <div className="tiny" style={{ color: "var(--ink-3)", fontFamily: "var(--t-mono)" }}>
            POST /api/v1/imports/{pipeline}/{stage === "preview" ? "import" : "preview"}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
            {stage === "preview" && !previewData?.batchResult && (
              <button className="btn" onClick={() => { reset(); }}>Re-run preview</button>
            )}
            <button
              className="btn btn--primary"
              disabled={stage !== "preview" || committing}
              style={(stage !== "preview" || committing) ? { opacity: 0.4, cursor: "not-allowed" } : {}}
              onClick={doCommit}
            >
              {committing ? "Importing…" : (previewData?.batchResult ? "Done" : "Import to library")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
