"""
HM44.2: Convert frontend-redesign/src/ from global-scope Babel to ES modules.
Lesson 14 name-level audit: fix all HL* ghost refs.
Run from: g:\My Drive\Code\Python\harmonylab\
"""
import re, os, shutil

SRC = os.path.join(os.path.dirname(__file__), 'frontend-redesign', 'src')

def read(fn):
    with open(os.path.join(SRC, fn), encoding='utf-8') as f:
        return f.read()

def write(fn, content):
    path = os.path.join(SRC, fn)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f'  wrote {fn} ({len(content)} chars)')

# ─────────────────────────────────────────────────────────────────────────────
# data.jsx — add export keywords before each const
# ─────────────────────────────────────────────────────────────────────────────
def fix_data():
    src = read('data.jsx')
    src = re.sub(r'^const KEY_COLOR_DEFAULTS', 'export const KEY_COLOR_DEFAULTS', src, flags=re.MULTILINE)
    src = re.sub(r'^const CHORD_QUALITIES', 'export const CHORD_QUALITIES', src, flags=re.MULTILINE)
    src = re.sub(r'^const ROOT_NOTES', 'export const ROOT_NOTES', src, flags=re.MULTILINE)
    write('data.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# api.jsx — add React import, data import, exports; fix window.HL_DATA ref
# ─────────────────────────────────────────────────────────────────────────────
def fix_api():
    src = read('api.jsx')
    # Prepend imports after opening comment block
    imports = (
        "import React from 'react';\n"
        "import { CHORD_QUALITIES } from './data.jsx';\n"
        "\n"
    )
    # Insert after the opening /* ... */ comment
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Fix window.HL_DATA?.CHORD_QUALITIES fallback
    src = src.replace("window.HL_DATA?.CHORD_QUALITIES || []", "CHORD_QUALITIES")
    # Add export before top-level function/const declarations (that aren't already exported)
    to_export = [
        'ApiProvider', 'useApi', 'useApiQuery',
        'beSongToLibraryRow', 'splitRoman', 'normKeyCenter',
        'keyCenterForMeasure', 'transformChord', 'beAnalysisToSong',
        'useLibraryRows', 'useSong', 'usePreferences',
        'useChordVocabulary', 'useAuditData',
        'hlFlattenChords', 'hlMergeKeyRegion', 'hlKeyCss',
        'hlUseToasts', 'hlLoadState', 'hlSaveState',
        'parseHash', 'encodeRoute',
    ]
    for name in to_export:
        src = re.sub(
            r'^(function ' + re.escape(name) + r'[ (])',
            r'export \1',
            src, flags=re.MULTILINE
        )
        src = re.sub(
            r'^(const ' + re.escape(name) + r'\s*=)',
            r'export \1',
            src, flags=re.MULTILINE
        )
    write('api.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# components.jsx — add imports, fix window.HL_DATA refs, fix window.hlUseApi check,
#                  add exports
# ─────────────────────────────────────────────────────────────────────────────
def fix_components():
    src = read('components.jsx')
    imports = (
        "import React from 'react';\n"
        "import { CHORD_QUALITIES, ROOT_NOTES } from './data.jsx';\n"
        "import { useApi, hlKeyCss, hlMergeKeyRegion, hlUseToasts } from './api.jsx';\n"
        "\n"
    )
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Fix window.HL_DATA accesses
    src = src.replace('window.HL_DATA.CHORD_QUALITIES', 'CHORD_QUALITIES')
    src = src.replace('window.HL_DATA.ROOT_NOTES', 'ROOT_NOTES')
    # Mock mode checks — replace with false (mock mode removed in HM44.1)
    src = src.replace("window.hlUseApi?.().mode === \"live\"", "false")
    # Add exports
    to_export = [
        'Toast', 'useToasts', 'ChordCell', 'ChordPicker',
        'ChordEditPopover', 'KeyPopover', 'Topbar',
        'ConfirmModal', 'suggestKeyCenter', 'mergeKeyRegion',
        'AIKeyCenterDialog',
    ]
    for name in to_export:
        src = re.sub(
            r'^(function ' + re.escape(name) + r'[ (])',
            r'export \1',
            src, flags=re.MULTILINE
        )
        src = re.sub(
            r'^(const ' + re.escape(name) + r'\s*=)',
            r'export \1',
            src, flags=re.MULTILINE
        )
    write('components.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# score.jsx — add React import, imports from api, add exports
# ─────────────────────────────────────────────────────────────────────────────
def fix_score():
    src = read('score.jsx')
    imports = (
        "import React from 'react';\n"
        "import { hlFlattenChords, hlKeyCss } from './api.jsx';\n"
        "import { ChordCell, AIKeyCenterDialog } from './components.jsx';\n"
        "\n"
    )
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Add exports
    to_export = [
        'ScoreWorkbench', 'SyntheticStaff', 'ScoreSystem',
        'RightRail', 'BottomAnalysis', 'Staff', 'ChordSymbol',
        'maxChordLen', 'systemCapacity', 'groupSystems',
    ]
    for name in to_export:
        src = re.sub(
            r'^(function ' + re.escape(name) + r'[ (])',
            r'export \1',
            src, flags=re.MULTILINE
        )
        src = re.sub(
            r'^(const ' + re.escape(name) + r'\s*=)',
            r'export \1',
            src, flags=re.MULTILINE
        )
    write('score.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# views.jsx — add imports, fix all ghost HL* refs, add exports
# ─────────────────────────────────────────────────────────────────────────────
def fix_views():
    src = read('views.jsx')
    imports = (
        "import React from 'react';\n"
        "import { KEY_COLOR_DEFAULTS } from './data.jsx';\n"
        "import { useApi, useLibraryRows, usePreferences, hlKeyCss } from './api.jsx';\n"
        "import { Topbar, ConfirmModal, ImportModal } from './components.jsx';\n"
        "\n"
        "/* Inline utilities needed by views */\n"
        "function LoadingState({ what }) {\n"
        "  return <div style={{ color: 'var(--ink-2)', fontSize: 14, padding: '24px 0' }}>Loading {what}…</div>;\n"
        "}\n"
        "function ErrorState({ error }) {\n"
        "  return <div style={{ color: 'var(--rose)', fontSize: 14, padding: '24px 0' }}>Error: {error?.message || String(error)}</div>;\n"
        "}\n"
        "\n"
    )
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Fix ghost refs
    src = src.replace('window.HL_DATA.KEY_COLOR_DEFAULTS', 'KEY_COLOR_DEFAULTS')
    src = src.replace('hlUseApi()', 'useApi()')
    src = src.replace('hlUseLibraryRows()', 'useLibraryRows()')
    src = src.replace('hlUsePreferences()', 'usePreferences()')
    src = src.replace('<HLTopbar ', '<Topbar ')
    src = src.replace('<HLConfirmModal', '<ConfirmModal')
    src = src.replace('</HLConfirmModal>', '</ConfirmModal>')
    src = src.replace('<HLLoadingState ', '<LoadingState ')
    src = src.replace('<HLErrorState ', '<ErrorState ')
    # Note: ImportModal is already imported from components.jsx above,
    # views.jsx may define its own ImportModal - check and skip if so
    # Actually views.jsx defines ImportModal itself; don't import it from components
    # Re-do: only import what's needed without ImportModal
    src = src.replace(
        "import { Topbar, ConfirmModal, ImportModal } from './components.jsx';\n",
        "import { Topbar, ConfirmModal } from './components.jsx';\n"
    )
    # Add exports
    to_export = ['Library', 'Settings', 'Audit', 'Lab', 'ImportModal', 'SortArrows', 'ColumnFilter', 'SortableHeader']
    for name in to_export:
        src = re.sub(
            r'^(function ' + re.escape(name) + r'[ (])',
            r'export \1',
            src, flags=re.MULTILINE
        )
    write('views.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# song.jsx — add imports, fix ghost HL* refs, add exports
# ─────────────────────────────────────────────────────────────────────────────
def fix_song():
    src = read('song.jsx')
    imports = (
        "import React from 'react';\n"
        "import { useApi, hlFlattenChords, hlKeyCss, hlLoadState, hlMergeKeyRegion, hlSaveState } from './api.jsx';\n"
        "import { Topbar, ChordEditPopover, KeyPopover, ConfirmModal, AIKeyCenterDialog } from './components.jsx';\n"
        "import { ScoreWorkbench } from './score.jsx';\n"
        "\n"
    )
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Fix ghost refs
    src = src.replace('hlUseApi()', 'useApi()')
    src = src.replace('<HLTopbar ', '<Topbar ')
    src = src.replace('<HLScoreWorkbench', '<ScoreWorkbench')
    src = src.replace('</HLScoreWorkbench>', '</ScoreWorkbench>')
    src = src.replace('<HLChordEditPopover', '<ChordEditPopover')
    src = src.replace('</HLChordEditPopover>', '</ChordEditPopover>')
    src = src.replace('<HLKeyPopover ', '<KeyPopover ')
    src = src.replace('</HLKeyPopover>', '</KeyPopover>')
    src = src.replace('<HLConfirmModal', '<ConfirmModal')
    src = src.replace('</HLConfirmModal>', '</ConfirmModal>')
    src = src.replace('<HLAIKeyCenterDialog', '<AIKeyCenterDialog')
    src = src.replace('</HLAIKeyCenterDialog>', '</AIKeyCenterDialog>')
    # Add exports
    to_export = ['SongDetail', 'NotationPane', 'KeyCenterTimeline', 'ExportMenu', 'TheoryChat']
    for name in to_export:
        src = re.sub(
            r'^(function ' + re.escape(name) + r'[ (])',
            r'export \1',
            src, flags=re.MULTILINE
        )
    write('song.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# app.jsx — add imports, fix ALL ghost refs, create LoadingState/ErrorState,
#            remove ReactDOM.createRoot (moved to main.jsx)
# ─────────────────────────────────────────────────────────────────────────────
def fix_app():
    src = read('app.jsx')
    imports = (
        "import React from 'react';\n"
        "import { ApiProvider, parseHash, encodeRoute, useSong, hlUseToasts, hlLoadState, hlSaveState } from './api.jsx';\n"
        "import { KEY_COLOR_DEFAULTS } from './data.jsx';\n"
        "import { Toast, Topbar } from './components.jsx';\n"
        "import { Library, Settings, Lab, Audit } from './views.jsx';\n"
        "import { SongDetail } from './song.jsx';\n"
        "\n"
        "/* Inline loading/error states */\n"
        "function LoadingState({ what }) {\n"
        "  return <div style={{ color: 'var(--ink-2)', fontSize: 14, padding: '24px 0' }}>Loading {what}…</div>;\n"
        "}\n"
        "function ErrorState({ error }) {\n"
        "  return <div style={{ color: 'var(--rose)', fontSize: 14, padding: '24px 0' }}>Error: {error?.message || String(error)}</div>;\n"
        "}\n"
        "\n"
    )
    src = re.sub(r'(\/\*[\s\S]*?\*\/\s*\n)', r'\1' + imports, src, count=1)
    # Fix ghost component refs
    src = src.replace('<HLLibrary ', '<Library ')
    src = src.replace('<HLSettings ', '<Settings ')
    src = src.replace('<HLLab ', '<Lab ')
    src = src.replace('<HLAudit ', '<Audit ')
    src = src.replace('<HLSongDetail ', '<SongDetail ')
    src = src.replace('<HLToast ', '<Toast ')
    src = src.replace('<HLTopbar ', '<Topbar ')
    src = src.replace('<HLLoadingState ', '<LoadingState ')
    src = src.replace('<HLErrorState ', '<ErrorState ')
    # Fix ghost function refs
    src = src.replace('hlParseHash()', 'parseHash()')
    src = src.replace('hlEncodeRoute(', 'encodeRoute(')
    src = src.replace('hlUseSong(', 'useSong(')
    # Fix window.HL_DATA reference
    src = src.replace('window.HL_DATA.KEY_COLOR_DEFAULTS', 'KEY_COLOR_DEFAULTS')
    # Remove ReactDOM.createRoot call (moved to main.jsx)
    src = re.sub(r'\n\/\* Mount \*\/\n.*?_root\.render.*?;', '', src, flags=re.DOTALL)
    # Export AppShell
    src = re.sub(r'^(function AppShell\()', r'export \1', src, flags=re.MULTILINE)
    write('app.jsx', src)

# ─────────────────────────────────────────────────────────────────────────────
# main.jsx — NEW entry point for Vite
# ─────────────────────────────────────────────────────────────────────────────
def create_main():
    content = """\
import React from 'react';
import ReactDOM from 'react-dom/client';
import '../redesign.css';
import { ApiProvider } from './api.jsx';
import { AppShell } from './app.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <ApiProvider>
    <AppShell />
  </ApiProvider>
);
"""
    write('main.jsx', content)

if __name__ == '__main__':
    print('=== HM44.2 ES module conversion ===')
    fix_data()
    fix_api()
    fix_components()
    fix_score()
    fix_views()
    fix_song()
    fix_app()
    create_main()
    print('Done.')
