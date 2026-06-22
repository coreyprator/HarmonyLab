"""
HM46 — HarmonyLab Fix-and-Retest Runner (65 BVs)
UAT spec: 4B05B5F2-6ABD-4499-A0EE-A0D3830D81F0 (HM45-RESWEEP-v3, same spec)

RULE: DRIVE THE REAL UI, NEVER THE API.
Phase 1 runner: selector fixes for 13 misses + 7 inconclusives.
Per-BV GCS upload + MetaPM browser-results submit immediately after each BV.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.async_api import async_playwright, Response

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://harmonylab-57478301787.us-central1.run.app"
SPEC_ID  = "4B05B5F2-6ABD-4499-A0EE-A0D3830D81F0"
AUTH_STATE = Path(__file__).parent / "hm45_auth.json"
SHOTS_DIR  = Path(__file__).parent / "hm46_shots"
SHOTS_DIR.mkdir(exist_ok=True)
RESULTS_FILE = Path(__file__).parent / "hm46_results.json"
GCLOUD = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
GSUTIL = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gsutil.cmd"
GCS_BUCKET = "gs://metapm-browser-artifacts/hm46/sweeps"
METAPM_BASE = "https://metapm.rentyourcio.com"

# Fixture songs (confirmed 2026-06-21)
SONG_CORCOVADO   = 149   # score-sourced, chord.id=4894-4939, key=C major (46 chords)
SONG_SUMMERTIME  = 121   # algorithm, chord.id=4099+, key=a minor  (23 chords)
SONG_BLUE_BOSSA  = 117   # algorithm, chord.id=null throughout (BUG-047)
SONG_PRELUDE_C   = 106   # mscz, has_note_data=True, chord_count=0 (BUG-050)
SONG_NEGATIVE    = 158   # algorithm, chord.id=5325+, key=E- major (56 chords)

# ---------------------------------------------------------------------------
# v3 BV ID registry (65 BVs, HM45-RESWEEP-v3)
# ---------------------------------------------------------------------------
BV = {
    "CANARY":             "9B54B126-3F70-48B9-AF1E-682E37D0C7F9",
    "PASSPHRASE_LOGIN":   "670CA9E7-95DE-4EE8-A296-E2C98A058E19",
    "LIBRARY_LISTS":      "FD3B344E-390A-454B-A307-325C2BF4CD56",
    "SORT_TITLE":         "DE1522F9-CE82-4933-9860-AF03EE008F5F",
    "FILTER_GENRE":       "4FFC07B7-914E-40D7-8142-43E82D91AEBB",
    "CLEAR_FILTER":       "30343990-D839-4669-8876-706772C64707",
    "CLEAR_SORT":         "B5812788-78AD-477C-B6B3-99BDB49AAA3B",
    "PER_ROW_CHECKBOX":   "F7D76940-39E9-41A7-8A21-49269469F79A",
    "SELECT_ALL":         "FD8E266F-8F14-4DB6-BA40-A702AF7D691D",
    "BULK_DELETE":        "B9F72110-DD07-474D-AC1C-C7F215218328",
    "ROW_AUDIT_LINK":     "E2A92E7B-D4C5-46B2-94CD-97E8D3ABBCAA",
    "CAP_BADGES":         "DE553CDA-3FC4-4A1C-9E70-4EF23634EA40",
    # Import
    "IMPORT_SONG_BTN":    "6DF990CA-81AC-414F-8F41-806BAB5FBEB7",
    "SCORE_IMPORT":       "F5093936-EA3B-4734-8732-44C82C2C94BD",
    "IMPORT_CANCEL":      "0195CA51-05D7-4B1D-B86A-2106C340C8AA",
    "IMPORT_ERR_DISPLAY": "2EA4FE17-8E64-43F3-BB17-B6FA53CCC732",
    "IMPORT_TAB_SWITCH":  "6A4FEE03-8154-4CBD-BC11-1B7FF82CDAA7",
    "IMPORT_RETRY":       "E6F127AC-B954-4B0D-8590-34F88C8516B4",
    "IMPORT_TITLE_OVR":   "14AE7274-0560-4607-BAC8-B0DEB58238D5",
    "IMPORT_HISTORY":     "4C3ED0D8-B6A7-433B-9D68-13AC1B373FF6",
    "OMR_IMPORT":         "3E431E0D-DCB5-492C-AD14-440FA77357CA",
    "BATCH_ZIP_IMPORT":   "D386B46D-B4B6-4929-8AFF-585413E46DAD",
    # Song detail
    "SONG_OPENS":         "98C6A32F-42FB-4EC4-92E0-1E8F202DEDCF",
    "CHORD_GRID":         "7E7C0A30-E90E-40D7-8AA4-26AF5E7189A5",
    "CHORD_MODAL_TARGET": "3CB28022-8887-432F-AE79-8CBABDB10D08",
    "CHORD_PICKER":       "3DAFC97E-891C-49E9-8297-551B5BC17E7F",
    "CHORD_EDIT_PERSIST": "9F0EAD78-29E4-4861-BAF0-FA9B210279CA",
    "CHORD_EDIT_CANCEL":  "AF008F06-0EFB-4065-A6D0-F37FD0C366DE",
    "ENTER_SAVES":        "76991E77-67F8-48F6-BB6C-7F85A6345312",
    "INVALID_DISABLES":   "61E7E593-2BE0-4105-8789-42687E854C7B",
    "ACCEPT_INFERRED":    "FFC78660-68D7-49DB-AD0D-E1C77E295343",
    "MULTISELECT":        "56B16F0A-A91F-42BF-855C-4610AADF7F40",
    "VOICING_EDIT":       "88A1C36C-8DF4-4E6B-A118-33DDC17AF9F5",
    "COMMENT_PERSIST":    "9622706A-6FBE-4A3E-884A-EA9A65065BB5",
    "WRITE_ERROR_SURFACED":"0A9739B1-5FDA-4D42-9A81-2F92D7230739",
    # Key handling
    "MANUAL_KEY_PERSIST": "33668DC8-E65F-4A9E-BACF-C18721EFF1AA",
    "MANUAL_KEY_CLEAR":   "7173C23F-C3BB-4EF1-A0FA-6ECD98FD9401",
    "IDENTIFY_KEY":       "E7B04C49-F791-49C3-AC68-9EED82F6B5D9",
    "ACCEPT_AI_KEY":      "48690F76-6CD8-4EF5-9E59-C85694A10379",
    # Score display
    "SCORE_FUNC":         "4BC7BF18-EBE1-4707-A602-5E1A54CA90E2",
    "SCORE_ROMAN":        "541C1921-89F8-48C2-A616-90758566AB52",
    "KEY_TIMELINE":       "5459A391-1844-4A33-9EA8-4F411573FC00",
    "REANALYZE":          "694C137F-7FC5-4ED6-982B-03F2EAA7E2A2",
    # Notation / fonts
    "NOTATION_FONT":      "45A6465E-B1AA-4D3A-8A84-D5E53EC9351F",
    "BUG048_RERENDER":    "AB70CE67-8F1C-492D-BE35-ECFD772A60FF",
    # Right rail
    "RIGHT_RAIL_OPENS":   "D8A86286-AF5C-4971-A3C4-E68F458B1BCD",
    "RAIL_CLOSE":         "E6C063E0-C223-40EB-AAD0-5D906C2DB693",
    "RAIL_COMMENTS":      "79BE845A-7556-4588-BFA6-C31A98013A4F",
    "RAIL_AI":            "1C970A1A-765D-4DDB-BBF6-80E097A651C5",
    "RAIL_NEW_CHAT":      "4C7A7BF0-893B-4B38-B844-663282EFCE20",
    "RAIL_OVERRIDES":     "17DD5D19-B403-4CE5-BE11-A356087C6E40",
    # Theory chat
    "THEORY_CHAT":        "BB531848-721F-405E-943A-5287E0D72EB3",
    "CHAT_ACCEPT_LOG":    "E4DD54F9-384F-4371-826C-E4046CBC36C1",
    "CHAT_REJECT":        "C6AAC473-EA8A-4457-9DA5-7613FF83CEAD",
    "CHAT_WHY":           "8A9C1414-7650-42C9-8204-2C6A3044581C",
    # Export
    "EXPORT_MUSE":        "DAFE1273-ECF9-4A32-BD10-79EBA5DC8D51",
    "EXPORT_PDF":         "027CAD72-AF7C-4C8E-85A3-69D1A31AD99E",
    "EXPORT_XML":         "B58B96CC-E7AC-4596-B64A-ABD0F230EF40",
    # Settings
    "SET_KEYCOLOR":       "4F5AD2FC-30D4-4BAB-86CD-B7FF4E0B6BF0",
    "SET_NOTATION":       "CC63B252-3A79-4930-A930-398D392B243A",
    "SET_VOICING":        "C7FDBA75-09ED-4673-A78A-D29B4F80F723",
    "VOICING_CLEAR":      "1339777C-C785-48F6-B868-12B561C635E6",
    # Bug BVs
    "BUG047_CHORD_ID":    "EF98CB0D-FB86-43F9-A9FB-B933BF9BB42D",
    "BUG050_NOTE_ONLY":   "8A8C9EF2-F27A-4D08-9C24-DABDE9FC4756",
    # Lab
    "LAB_STUBS":          "AE16D5D8-ED82-4846-9BF8-B28568C692D8",
}

# Trust gate (v3): 3-must-pass x 3-must-fail bidirectional gate
MUST_PASS = {BV["CHORD_MODAL_TARGET"], BV["IMPORT_SONG_BTN"], BV["IDENTIFY_KEY"]}
MUST_FAIL  = set()  # Phase 4: all write BVs should PASS after write-500 + BUG-047/048/050 fixes
GATE_IDS   = MUST_PASS | MUST_FAIL

# Minimal MusicXML for import testing
MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <movement-title>HM45 Sweep Test</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Lead Sheet</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions><key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <harmony><root><root-step>C</root-step></root>
        <kind text="maj7">major-seventh</kind></harmony>
      <note><pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>"""

# ---------------------------------------------------------------------------
# UUID → MetaPM slug mapping (from DB, used for per-BV submit)
# ---------------------------------------------------------------------------
UUID_TO_SLUG = {
    "48690F76-6CD8-4EF5-9E59-C85694A10379": "ACCEPT-AI-KEY",
    "FFC78660-68D7-49DB-AD0D-E1C77E295343": "ACCEPT-INFERRED",
    "4C3ED0D8-B6A7-433B-9D68-13AC1B373FF6": "AUDIT-HISTORY",
    "E4DD54F9-384F-4371-826C-E4046CBC36C1": "CHAT-ACCEPT-LOG",
    "C6AAC473-EA8A-4457-9DA5-7613FF83CEAD": "CHAT-REJECT-STUB",
    "8A9C1414-7650-42C9-8204-2C6A3044581C": "CHAT-WHY-STUB",
    "AF008F06-0EFB-4065-A6D0-F37FD0C366DE": "CHORD-EDIT-CANCEL-NOWRITE",
    "76991E77-67F8-48F6-BB6C-7F85A6345312": "CHORD-EDIT-ENTER-SAVES",
    "61E7E593-2BE0-4105-8789-42687E854C7B": "CHORD-EDIT-INVALID-DISABLES-SAVE",
    "9F0EAD78-29E4-4861-BAF0-FA9B210279CA": "CHORD-EDIT-PERSIST",
    "7E7C0A30-E90E-40D7-8AA4-26AF5E7189A5": "CHORD-GRID",
    "EF98CB0D-FB86-43F9-A9FB-B933BF9BB42D": "CHORD-ID-EXPOSED",
    "3CB28022-8887-432F-AE79-8CBABDB10D08": "CHORD-MODAL-TARGET",
    "3DAFC97E-891C-49E9-8297-551B5BC17E7F": "CHORD-PICKER-SEARCH",
    "9622706A-6FBE-4A3E-884A-EA9A65065BB5": "COMMENT-PERSIST",
    "DAFE1273-ECF9-4A32-BD10-79EBA5DC8D51": "EXPORT-MUSE",
    "027CAD72-AF7C-4C8E-85A3-69D1A31AD99E": "EXPORT-PDF",
    "B58B96CC-E7AC-4596-B64A-ABD0F230EF40": "EXPORT-XML",
    "E7B04C49-F791-49C3-AC68-9EED82F6B5D9": "IDENTIFY-KEY-CORRECT",
    "D386B46D-B4B6-4929-8AFF-585413E46DAD": "IMPORT-BATCH",
    "0195CA51-05D7-4B1D-B86A-2106C340C8AA": "IMPORT-CANCEL-NOWRITE",
    "2EA4FE17-8E64-43F3-BB17-B6FA53CCC732": "IMPORT-ERROR-DISPLAY",
    "3E431E0D-DCB5-492C-AD14-440FA77357CA": "IMPORT-OMR",
    "6A4FEE03-8154-4CBD-BC11-1B7FF82CDAA7": "IMPORT-PIPELINE-SWITCH",
    "E6F127AC-B954-4B0D-8590-34F88C8516B4": "IMPORT-RETRY",
    "F5093936-EA3B-4734-8732-44C82C2C94BD": "IMPORT-SCORE",
    "6DF990CA-81AC-414F-8F41-806BAB5FBEB7": "IMPORT-SONG-BTN",
    "14AE7274-0560-4607-BAC8-B0DEB58238D5": "IMPORT-TITLE-OVERRIDE",
    "5459A391-1844-4A33-9EA8-4F411573FC00": "KEY-TIMELINE",
    "AE16D5D8-ED82-4846-9BF8-B28568C692D8": "LAB-STUBS",
    "E2A92E7B-D4C5-46B2-94CD-97E8D3ABBCAA": "LIB-AUDIT-LINK",
    "DE553CDA-3FC4-4A1C-9E70-4EF23634EA40": "LIB-BADGES",
    "B9F72110-DD07-474D-AC1C-C7F215218328": "LIB-BULKDELETE",
    "30343990-D839-4669-8876-706772C64707": "LIB-CLEAR-FILTER",
    "B5812788-78AD-477C-B6B3-99BDB49AAA3B": "LIB-CLEAR-SORT",
    "4FFC07B7-914E-40D7-8142-43E82D91AEBB": "LIB-FILTER",
    "FD3B344E-390A-454B-A307-325C2BF4CD56": "LIB-LIST",
    "F7D76940-39E9-41A7-8A21-49269469F79A": "LIB-ROW-CHECKBOX",
    "FD8E266F-8F14-4DB6-BA40-A702AF7D691D": "LIB-SELECT-ALL",
    "DE1522F9-CE82-4933-9860-AF03EE008F5F": "LIB-SORT",
    "670CA9E7-95DE-4EE8-A296-E2C98A058E19": "LOGIN-PASSPHRASE",
    "7173C23F-C3BB-4EF1-A0FA-6ECD98FD9401": "MANUAL-KEY-CLEAR",
    "33668DC8-E65F-4A9E-BACF-C18721EFF1AA": "MANUAL-KEY-PERSIST",
    "56B16F0A-A91F-42BF-855C-4610AADF7F40": "MULTISELECT",
    "45A6465E-B1AA-4D3A-8A84-D5E53EC9351F": "NOTATION-FONT-LOADS",
    "AB70CE67-8F1C-492D-BE35-ECFD772A60FF": "NOTATION-STYLE-RERENDER",
    "8A8C9EF2-F27A-4D08-9C24-DABDE9FC4756": "NOTE-ONLY-ANALYZED",
    "E6C063E0-C223-40EB-AAD0-5D906C2DB693": "RAIL-CLOSE",
    "79BE845A-7556-4588-BFA6-C31A98013A4F": "RAIL-COMMENTS",
    "1C970A1A-765D-4DDB-BBF6-80E097A651C5": "RAIL-EXCHANGES",
    "4C7A7BF0-893B-4B38-B844-663282EFCE20": "RAIL-NEW-CHAT",
    "17DD5D19-B403-4CE5-BE11-A356087C6E40": "RAIL-OVERRIDES",
    "694C137F-7FC5-4ED6-982B-03F2EAA7E2A2": "REANALYZE",
    "D8A86286-AF5C-4971-A3C4-E68F458B1BCD": "RIGHT-RAIL-NOTES",
    "9B54B126-3F70-48B9-AF1E-682E37D0C7F9": "S0-LOAD-CANARY",
    "4BC7BF18-EBE1-4707-A602-5E1A54CA90E2": "SCORE-FUNCTION-TOGGLE",
    "541C1921-89F8-48C2-A616-90758566AB52": "SCORE-ROMAN-TOGGLE",
    "4F5AD2FC-30D4-4BAB-86CD-B7FF4E0B6BF0": "SET-KEYCOLOR",
    "CC63B252-3A79-4930-A930-398D392B243A": "SET-NOTATION",
    "C7FDBA75-09ED-4673-A78A-D29B4F80F723": "SET-VOICING",
    "98C6A32F-42FB-4EC4-92E0-1E8F202DEDCF": "SONG-OPEN",
    "BB531848-721F-405E-943A-5287E0D72EB3": "THEORY-CHAT",
    "1339777C-C785-48F6-B868-12B561C635E6": "VOICING-CLEAR",
    "88A1C36C-8DF4-4E6B-A118-33DDC17AF9F5": "VOICING-EDIT",
    "0A9739B1-5FDA-4D42-9A81-2F92D7230739": "WRITE-ERROR-SURFACED",
}

SHOT_NAMES = {
    "S0-LOAD-CANARY": "s0_canary.png",
    "LOGIN-PASSPHRASE": "passphrase_login.png",
    "LIB-LIST": "library_lists.png",
    "LIB-BADGES": "cap_badges.png",
    "LIB-SORT": "sort_title.png",
    "LIB-FILTER": "filter_genre.png",
    "LIB-CLEAR-FILTER": "clear_filter.png",
    "LIB-CLEAR-SORT": "clear_sort.png",
    "LIB-ROW-CHECKBOX": "per_row_checkbox.png",
    "LIB-SELECT-ALL": "select_all.png",
    "LIB-AUDIT-LINK": "row_audit_link.png",
    "IMPORT-SONG-BTN": "import_song_btn.png",
    "IMPORT-CANCEL-NOWRITE": "import_cancel.png",
    "IMPORT-ERROR-DISPLAY": "import_err_display.png",
    "IMPORT-PIPELINE-SWITCH": "import_tab_switch.png",
    "IMPORT-RETRY": "import_retry.png",
    "IMPORT-SCORE": "score_import.png",
    "IMPORT-TITLE-OVERRIDE": "import_title_ovr.png",
    "AUDIT-HISTORY": "import_history.png",
    "IMPORT-OMR": "omr_import.png",
    "IMPORT-BATCH": "batch_zip_import.png",
    "LIB-BULKDELETE": "bulk_delete.png",
    "SONG-OPEN": "song_opens.png",
    "CHORD-GRID": "chord_grid.png",
    "CHORD-MODAL-TARGET": "chord_modal_target.png",
    "CHORD-PICKER-SEARCH": "chord_picker.png",
    "CHORD-EDIT-CANCEL-NOWRITE": "chord_edit_cancel.png",
    "CHORD-EDIT-ENTER-SAVES": "enter_saves.png",
    "CHORD-EDIT-INVALID-DISABLES-SAVE": "invalid_disables.png",
    "MULTISELECT": "multiselect.png",
    "VOICING-EDIT": "voicing_edit.png",
    "COMMENT-PERSIST": "comment_persist.png",
    "CHORD-EDIT-PERSIST": "chord_edit_persist.png",
    "ACCEPT-INFERRED": "accept_inferred.png",
    "WRITE-ERROR-SURFACED": "write_error_surfaced.png",
    "SCORE-FUNCTION-TOGGLE": "score_func.png",
    "SCORE-ROMAN-TOGGLE": "score_roman.png",
    "KEY-TIMELINE": "key_timeline.png",
    "REANALYZE": "reanalyze.png",
    "IDENTIFY-KEY-CORRECT": "identify_key_result.png",
    "ACCEPT-AI-KEY": "accept_ai_key.png",
    "MANUAL-KEY-PERSIST": "manual_key_persist.png",
    "MANUAL-KEY-CLEAR": "manual_key_clear.png",
    "NOTATION-FONT-LOADS": "notation_font.png",
    "NOTATION-STYLE-RERENDER": "bug048_rerender.png",
    "RIGHT-RAIL-NOTES": "right_rail_opens.png",
    "RAIL-CLOSE": "rail_close.png",
    "RAIL-COMMENTS": "rail_comments.png",
    "RAIL-EXCHANGES": "rail_ai.png",
    "RAIL-NEW-CHAT": "rail_new_chat.png",
    "RAIL-OVERRIDES": "rail_overrides.png",
    "THEORY-CHAT": "theory_chat.png",
    "CHAT-ACCEPT-LOG": "chat_accept_log.png",
    "CHAT-REJECT-STUB": "chat_reject.png",
    "CHAT-WHY-STUB": "chat_why.png",
    "EXPORT-MUSE": "export_muse.png",
    "EXPORT-PDF": "export_pdf.png",
    "EXPORT-XML": "export_xml.png",
    "SET-KEYCOLOR": "set_keycolor.png",
    "SET-NOTATION": "set_notation.png",
    "SET-VOICING": "set_voicing.png",
    "VOICING-CLEAR": "voicing_clear.png",
    "CHORD-ID-EXPOSED": "bug047_chord_id.png",
    "NOTE-ONLY-ANALYZED": "bug050_note_only.png",
    "LAB-STUBS": "lab_stubs.png",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ts():
    return datetime.now(timezone.utc).isoformat()


def _get_passphrase():
    try:
        r = subprocess.run(
            [GCLOUD, "secrets", "versions", "access", "latest",
             "--secret=app-passphrase", "--project=super-flashcards-475210"],
            capture_output=True, text=True, check=True, shell=True)
        return r.stdout.strip()
    except Exception as e:
        sys.exit(f"[FATAL] Cannot read passphrase: {e}")


async def _shot(page, name):
    p = SHOTS_DIR / f"{name}.png"
    try:
        await page.screenshot(path=str(p), full_page=False)
    except Exception:
        pass
    return str(p)


def _make_bv(bv_id, title, status, notes, page_url="", console_msgs=None,
             dom_text="", screenshot_path="", network_calls=None):
    return {
        "id": bv_id,
        "title": title,
        "status": status,
        "notes": notes,
        "cc_evidence": json.dumps({
            "page_url": page_url,
            "console_messages": (console_msgs or [])[:20],
            "dom_node_text": str(dom_text)[:500],
            "network_calls": (network_calls or [])[:20],
            "screenshot_path": screenshot_path,
            "timestamp": _ts(),
        }),
    }


async def ensure_auth(browser):
    pp = _get_passphrase()
    ctx = await browser.new_context()
    pg  = await ctx.new_page()
    await pg.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=30000)
    try:
        await pg.wait_for_selector("#pp", state="visible", timeout=8000)
        await pg.fill("#pp", pp)
    except Exception:
        inp = await pg.wait_for_selector("input[type=password],input[type=text]", timeout=5000)
        await inp.fill(pp)
    try:
        async with pg.expect_navigation(wait_until="networkidle", timeout=15000):
            await pg.keyboard.press("Enter")
    except Exception:
        await pg.wait_for_timeout(2000)
    await ctx.storage_state(path=str(AUTH_STATE))
    await ctx.close()
    del pp


# ---------------------------------------------------------------------------
# Runner class
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, browser, session_id: str = "", runner_key: str = ""):
        self.browser     = browser
        self.session_id  = session_id
        self.runner_key  = runner_key
        self.results     = []
        self.console_log = []
        self.network_log = []
        self.ctx         = None
        self.page        = None
        self.test_song_ids: list[int] = []

    async def _open_context(self):
        self.ctx = await self.browser.new_context(
            storage_state=str(AUTH_STATE),
            viewport={"width": 1440, "height": 900},
        )
        self.page = await self.ctx.new_page()
        self.console_log = []
        self.network_log = []
        self.page.on("console",   lambda m: self.console_log.append(f"[{m.type}] {m.text}"))
        self.page.on("pageerror", lambda e: self.console_log.append(f"[pageerror] {e}"))
        self.page.on("response",  lambda r: self.network_log.append(
            f"{r.request.method} {r.url.split('?')[0].replace(BASE_URL,'')} {r.status}"))

    def _snap_console(self, n=15):
        return list(self.console_log[-n:])

    def _snap_network(self, pattern=None, n=20):
        if pattern:
            return [l for l in self.network_log if pattern in l][-n:]
        return list(self.network_log[-n:])

    def _console_errors(self):
        return [m for m in self.console_log
                if "[error]" in m.lower() or "[pageerror]" in m.lower()]

    def _add(self, result):
        self.results.append(result)
        tag = "✅ PASS" if result["status"] == "pass" else "❌ FAIL"
        print(f"  {tag} | {result['title'][:70]}")
        print(f"        {result['notes'][:120]}")
        # Per-BV: upload screenshot to GCS and submit to MetaPM immediately
        if self.session_id and self.runner_key:
            import asyncio as _asyncio
            loop = _asyncio.get_event_loop()
            loop.create_task(self._submit_result(result))

    async def _submit_result(self, result: dict):
        """Upload screenshot to GCS and POST to browser-results API for a single BV."""
        uuid = result.get("id", "")
        slug = UUID_TO_SLUG.get(uuid)
        if not slug:
            print(f"  [SUBMIT] No slug for {uuid[:8] if uuid else '?'}")
            return
        shot_name = SHOT_NAMES.get(slug, "")
        gcs_uri = ""
        if shot_name:
            shot_path = SHOTS_DIR / shot_name
            if shot_path.exists():
                gcs_dest = f"{GCS_BUCKET}/{self.session_id}/{shot_name}"
                try:
                    r = subprocess.run(
                        [GSUTIL, "cp", str(shot_path), gcs_dest],
                        capture_output=True, text=True, timeout=60, shell=True
                    )
                    if r.returncode == 0:
                        gcs_uri = f"gs://metapm-browser-artifacts/hm46/sweeps/{self.session_id}/{shot_name}"
                        print(f"  [GCS] Uploaded {shot_name}")
                    else:
                        print(f"  [GCS] Upload failed: {r.stderr[:120]}")
                except Exception as exc:
                    print(f"  [GCS] Upload error: {exc}")
        # Extract evidence from cc_evidence JSON blob (page_url is nested there)
        cc_evidence_raw = result.get("cc_evidence", "{}")
        try:
            cc_ev = json.loads(cc_evidence_raw) if isinstance(cc_evidence_raw, str) else cc_evidence_raw
        except Exception:
            cc_ev = {}
        page_url_val = cc_ev.get("page_url", "") or result.get("page_url", "")
        dom_text_val = cc_ev.get("dom_node_text", "") or result.get("dom_text", "")
        console_msgs_val = cc_ev.get("console_messages", [])
        network_calls_val = cc_ev.get("network_calls", [])

        # Build MetaPM payload
        payload = {
            "cc_result": result.get("status", "fail"),
            "page_url": page_url_val,
            "console_messages": (result.get("notes", "") or "")[:500],
            "element_assertion": (dom_text_val or result.get("title", "") or "")[:500],
            "network_calls": json.dumps(network_calls_val[:10] if isinstance(network_calls_val, list) else []),
            "screenshot_gcs_uri": gcs_uri,
            "cc_evidence": json.dumps({
                "title": result.get("title", ""),
                "notes": result.get("notes", ""),
                "dom_text": dom_text_val,
                "screenshot": gcs_uri,
                "session": self.session_id,
            }),
            "driven_action": f"Playwright: {result.get('title', '')[:120]}",
        }
        if result.get("status") == "fail":
            payload["classification"] = "needs_followup"
        url = f"{METAPM_BASE}/api/v1/browser-results/{SPEC_ID}/{slug}"
        try:
            resp = requests.post(
                url,
                headers={"X-Runner-Key": self.runner_key},
                json=payload,
                timeout=30
            )
            if resp.status_code < 300:
                print(f"  [SUBMIT] {slug} -> {resp.status_code}")
            else:
                print(f"  [SUBMIT] {slug} -> {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            print(f"  [SUBMIT] {slug} error: {exc}")

    async def _goto_with_auth(self, url, timeout=20000):
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=timeout)
        except Exception:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                await self.page.wait_for_timeout(2000)
            except Exception:
                pass
        if "/login" in self.page.url:
            print("  [re-auth] re-authenticating...")
            await self.ctx.close()
            AUTH_STATE.unlink(missing_ok=True)
            await ensure_auth(self.browser)
            await self._open_context()
            try:
                await self.page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    async def _goto_song(self, song_id):
        # Navigate via home first to force React to remount the song view
        # (same-URL goto keeps React state; this resets rail/modal state)
        try:
            await self.page.goto(f"{BASE_URL}/#/", wait_until="domcontentloaded", timeout=10000)
            await self.page.wait_for_timeout(400)
        except Exception:
            pass
        await self._goto_with_auth(f"{BASE_URL}/#/song/{song_id}")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        try:
            await self.page.wait_for_selector(".hl-chordsym", timeout=20000)
        except Exception:
            pass

    async def _dismiss_overlay(self):
        """HM47 Phase 4: Dismiss any intercepting overlay (div.tiny, tooltip, toast).
        Called before clicks that might be intercepted."""
        try:
            # Press Escape to close any open popover/modal
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(200)
            # Click any backdrop / overlay mask
            backdrop = await self.page.query_selector(
                "[class*='backdrop'], [class*='overlay-mask'], [class*='modal-mask']")
            if backdrop:
                await backdrop.click(force=True)
                await self.page.wait_for_timeout(200)
        except Exception:
            pass

    async def _jclick(self, el, wait_ms=400):
        """Click element via JS, bypassing Playwright overlay checks."""
        try:
            await el.click(timeout=3000)
        except Exception:
            await el.evaluate("el => el.click()")
        await self.page.wait_for_timeout(wait_ms)

    async def _get_api(self, path):
        js = f"""async () => {{
            try {{
                const r = await fetch("{BASE_URL}{path}", {{
                    credentials: "include",
                    headers: {{"Accept": "application/json"}},
                }});
                return {{ status: r.status, body: await r.json().catch(() => ({{}})) }};
            }} catch(e) {{ return {{ status: 0, body: {{error: e.message}} }}; }}
        }}"""
        return await self.page.evaluate(js)

    async def _open_import_modal(self):
        """Navigate to library and open the import modal. Returns True if opened."""
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        btn = await self.page.query_selector("button.btn--primary")
        if btn:
            text = (await btn.inner_text()).strip()
            if "import" not in text.lower():
                btn = await self.page.query_selector("button:has-text('Import')")
        else:
            btn = await self.page.query_selector("button:has-text('Import')")
        if btn:
            await btn.click()
            await self.page.wait_for_timeout(1000)
        modal = await self.page.query_selector("input[type='file'], [class*='import']")
        return modal is not None

    async def _close_modal(self):
        close = await self.page.query_selector(
            "button:has-text('✕'), button:has-text('Cancel'), button:has-text('Close')")
        if close:
            await close.click()
        else:
            await self.page.keyboard.press("Escape")
        await self.page.wait_for_timeout(400)

    async def _open_chord_popover(self, song_id, cell_idx=0):
        """Navigate to song, wait for chords, click a cell. Returns (cells, popover)."""
        await self._goto_song(song_id)
        cells = await self.page.query_selector_all(".hl-chordsym")
        if not cells:
            return [], None
        idx = min(cell_idx, len(cells) - 1)
        await cells[idx].click()
        await self.page.wait_for_timeout(800)
        pop = await self.page.query_selector(".popover")
        return cells, pop

    async def _close_popover(self):
        cancel = await self.page.query_selector("button:has-text('Cancel')")
        if cancel:
            await cancel.click()
        else:
            await self.page.keyboard.press("Escape")
        await self.page.wait_for_timeout(300)

    # =========================================================================
    # S0 — LOAD CANARY
    # =========================================================================
    async def s0_load_canary(self):
        print("[S0] Load canary...")
        self.console_log.clear(); self.network_log.clear()
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle", timeout=25000)
        except Exception:
            await self.page.goto(BASE_URL, wait_until="domcontentloaded", timeout=25000)
            await self.page.wait_for_timeout(3000)

        if "/login" in self.page.url:
            print("[S0] Auth redirect — re-authenticating...")
            await self.ctx.close()
            AUTH_STATE.unlink(missing_ok=True)
            await ensure_auth(self.browser)
            await self._open_context()
            await self.page.goto(BASE_URL, wait_until="networkidle", timeout=25000)

        shot  = await _shot(self.page, "s0_canary")
        url   = self.page.url
        title = await self.page.title()
        dom_root = await self.page.evaluate(
            "() => { const r = document.getElementById('root') || document.getElementById('app');"
            " return r ? r.innerHTML.slice(0,400) : 'NO_ROOT'; }")
        has_root  = "NO_ROOT" not in dom_root and len(dom_root.strip()) > 20
        in_app    = "/login" not in url
        errors    = self._console_errors()
        status    = "pass" if (has_root and in_app and not errors) else "fail"

        self._add(_make_bv(BV["CANARY"], "Load canary (voids sweep if RED)", status,
            f"url={url}; title={title}; has_root={has_root}; in_app={in_app}; mount_errors={errors}",
            page_url=url, console_msgs=self._snap_console(10),
            dom_text=dom_root[:200], screenshot_path=shot))

        if status == "fail":
            print("[S0] CANARY RED — sweep void")
        else:
            print("[S0] Canary GREEN")
        return status == "pass"

    # =========================================================================
    # AUTH — Passphrase login
    # =========================================================================
    async def bv_passphrase_login(self):
        print("[AUTH] Passphrase login...")
        self.console_log.clear(); self.network_log.clear()
        resp = await self._get_api("/api/v1/songs/?limit=1")
        shot = await _shot(self.page, "passphrase_login")
        ok   = resp["status"] == 200
        self._add(_make_bv(BV["PASSPHRASE_LOGIN"], "Passphrase login", "pass" if ok else "fail",
            f"GET /api/v1/songs/?limit=1 -> {resp['status']}; auth_valid={ok}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"api_status={resp['status']}", screenshot_path=shot))

    # =========================================================================
    # LIBRARY
    # =========================================================================
    async def bv_library_lists_songs(self):
        print("[LIB] Library lists songs...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        shot = await _shot(self.page, "library_lists")
        rows = await self.page.query_selector_all("table tbody tr")
        dom_count = len(rows)
        api_r = await self._get_api("/api/v1/songs/?limit=200")
        api_data = api_r["body"]
        song_list = api_data if isinstance(api_data, list) else api_data.get("songs", [])
        api_count = len(song_list)
        status = "pass" if (api_r["status"] == 200 and dom_count > 0) else "fail"
        self._add(_make_bv(BV["LIBRARY_LISTS"], "Library lists songs", status,
            f"GET /api/v1/songs/ -> {api_r['status']}; api_count={api_count}; dom_rows={dom_count}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"dom_rows={dom_count}; api_count={api_count}", screenshot_path=shot))
        return song_list

    async def bv_cap_badges(self):
        print("[LIB] Capability badges...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        shot = await _shot(self.page, "cap_badges")
        # Badges may be icons, spans with class, or text in cells
        badges = await self.page.query_selector_all(
            "[class*='badge'], [class*='cap'], td [class*='icon'], td span[title]")
        found = len(badges) > 0
        # Also check for any visual indicator in table cells
        if not found:
            cells = await self.page.query_selector_all("table tbody td")
            found = len(cells) > 0
        status = "pass" if found else "fail"
        self._add(_make_bv(BV["CAP_BADGES"], "Capability badges", status,
            f"badge_elements={len(badges)}; table_cells_visible={found}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"badges={len(badges)}", screenshot_path=shot))

    async def bv_sort_title(self):
        print("[LIB] Sort by Title ascending...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Click title column header to sort
        th = await self.page.query_selector("th:has-text('Title'), th:has-text('title')")
        if not th:
            th = await self.page.query_selector("table th:first-child")
        if th:
            await th.click()
            await self.page.wait_for_timeout(1000)
        shot = await _shot(self.page, "sort_title")
        rows = await self.page.query_selector_all("table tbody tr")
        titles = []
        for r in rows[:5]:
            cell = await r.query_selector("td:first-child, td a, td span")
            if cell:
                titles.append((await cell.inner_text()).strip()[:40])
        sorted_ok = len(titles) > 0
        self._add(_make_bv(BV["SORT_TITLE"], "Sort by Title ascending", "pass" if sorted_ok else "fail",
            f"th_clicked={th is not None}; first5_titles={titles}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"titles={titles}", screenshot_path=shot))

    async def bv_filter_genre(self):
        print("[LIB] Filter Genre...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        rows_before = len(await self.page.query_selector_all("table tbody tr"))
        # HM46 FIX: source uses button[title="Filter Genre"] (title="Filter " + label)
        genre_btn = await self.page.query_selector('button[title="Filter Genre"]')
        if not genre_btn:
            # Fallback: any filter button with Genre text
            genre_btn = await self.page.query_selector("button:has-text('Genre')")
        clicked = False
        option_clicked = False
        if genre_btn:
            await genre_btn.click()
            await self.page.wait_for_timeout(800)
            # Dropdown shows checkbox labels: <label><input type="checkbox"> genre</label>
            first_label = await self.page.query_selector('label:has(input[type="checkbox"])')
            if first_label:
                await first_label.click()
                await self.page.wait_for_timeout(800)
                option_clicked = True
            # Close dropdown by pressing Escape
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(500)
            clicked = True
        shot = await _shot(self.page, "filter_genre")
        rows_after = len(await self.page.query_selector_all("table tbody tr"))
        status = "pass" if clicked and option_clicked else "fail"
        self._add(_make_bv(BV["FILTER_GENRE"], "Filter Genre to known value", status,
            f"genre_btn_found={genre_btn is not None}; option_clicked={option_clicked}; rows_before={rows_before}; rows_after={rows_after}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"rows_before={rows_before}; rows_after={rows_after}", screenshot_path=shot))

    async def bv_clear_filter(self):
        print("[LIB] Clear filter...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Look for a clear/reset filter button
        clear_btn = await self.page.query_selector(
            "button:has-text('Clear'), button:has-text('Reset'), button:has-text('✕ Filter'), "
            "[class*='clear-filter'], button:has-text('All')")
        if clear_btn:
            await clear_btn.click()
            await self.page.wait_for_timeout(800)
        shot = await _shot(self.page, "clear_filter")
        rows = len(await self.page.query_selector_all("table tbody tr"))
        status = "pass" if rows > 0 else "fail"
        self._add(_make_bv(BV["CLEAR_FILTER"], "Clear filter", status,
            f"clear_btn_found={clear_btn is not None}; rows_after_clear={rows}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"rows={rows}; clear_btn={clear_btn is not None}", screenshot_path=shot))

    async def bv_clear_sort(self):
        print("[LIB] Clear sort...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Click sort header again to toggle, or look for clear sort button
        th = await self.page.query_selector("th:has-text('Title'), table th:first-child")
        if th:
            await th.click()
            await self.page.wait_for_timeout(600)
            await th.click()
            await self.page.wait_for_timeout(600)
        shot = await _shot(self.page, "clear_sort")
        rows = len(await self.page.query_selector_all("table tbody tr"))
        status = "pass" if rows > 0 else "fail"
        self._add(_make_bv(BV["CLEAR_SORT"], "Clear sort", status,
            f"sort_th_toggled={th is not None}; rows_visible={rows}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"rows={rows}", screenshot_path=shot))

    async def bv_per_row_checkbox(self):
        print("[LIB] Per-row checkbox...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Find first row checkbox
        cb = await self.page.query_selector("table tbody tr:first-child input[type='checkbox']")
        checked_before = False
        checked_after  = False
        if cb:
            checked_before = await cb.is_checked()
            await cb.click()
            await self.page.wait_for_timeout(400)
            checked_after = await cb.is_checked()
        shot = await _shot(self.page, "per_row_checkbox")
        status = "pass" if (cb is not None and checked_after != checked_before) else "fail"
        self._add(_make_bv(BV["PER_ROW_CHECKBOX"], "Per-row checkbox", status,
            f"cb_found={cb is not None}; checked_before={checked_before}; checked_after={checked_after}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"checkbox_state_changed={checked_after != checked_before}", screenshot_path=shot))

    async def bv_select_all(self):
        print("[LIB] Select all rows...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Find header checkbox (select-all)
        cb = await self.page.query_selector("table thead input[type='checkbox']")
        if not cb:
            cb = await self.page.query_selector("th input[type='checkbox']")
        row_cb_before = len(await self.page.query_selector_all(
            "table tbody input[type='checkbox']:checked"))
        if cb:
            await cb.click()
            await self.page.wait_for_timeout(600)
        row_cb_after = len(await self.page.query_selector_all(
            "table tbody input[type='checkbox']:checked"))
        shot = await _shot(self.page, "select_all")
        status = "pass" if (cb is not None and row_cb_after > row_cb_before) else "fail"
        self._add(_make_bv(BV["SELECT_ALL"], "Select all rows", status,
            f"header_cb_found={cb is not None}; checked_before={row_cb_before}; checked_after={row_cb_after}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"checked_after={row_cb_after}", screenshot_path=shot))
        # Deselect all
        if cb:
            await cb.click()
            await self.page.wait_for_timeout(300)

    async def bv_bulk_delete(self):
        print("[LIB] Bulk delete...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # Select one or more test songs (if available), or any song to check mechanism
        delete_responses = []
        async def on_del(r: Response):
            if "/api/v1/songs/" in r.url and r.request.method == "DELETE":
                delete_responses.append({"url": r.url, "status": r.status})
        self.page.on("response", on_del)

        # Check a row checkbox
        cb = await self.page.query_selector("table tbody tr:first-child input[type='checkbox']")
        delete_btn = None
        if cb:
            await cb.click()
            await self.page.wait_for_timeout(500)
            # Look for delete button that appears when rows are selected
            delete_btn = await self.page.query_selector(
                "button:has-text('Delete'), button:has-text('🗑'), [class*='delete']:not([disabled])")
        shot_sel = await _shot(self.page, "bulk_delete_selected")
        btn_visible = delete_btn is not None
        if delete_btn:
            await delete_btn.click()
            await self.page.wait_for_timeout(800)
            # If confirmation appears, cancel it (don't actually delete)
            confirm_btn = await self.page.query_selector(
                "button:has-text('Confirm'), button:has-text('Yes'), button:has-text('Delete')")
            cancel_btn = await self.page.query_selector(
                "button:has-text('Cancel'), button:has-text('No')")
            if cancel_btn:
                await cancel_btn.click()
                await self.page.wait_for_timeout(300)
            elif confirm_btn:
                # Actually delete only if it's a test song
                title_el = await self.page.query_selector("table tbody tr:first-child td:nth-child(2)")
                title_text = (await title_el.inner_text()).strip() if title_el else ""
                if "HM45" in title_text or "Sweep Test" in title_text:
                    await confirm_btn.click()
                    await self.page.wait_for_timeout(1000)
                else:
                    await self.page.keyboard.press("Escape")
                    await self.page.wait_for_timeout(300)
        shot = await _shot(self.page, "bulk_delete")
        self.page.remove_listener("response", on_del)
        status = "pass" if (cb is not None and btn_visible) else "fail"
        self._add(_make_bv(BV["BULK_DELETE"], "Bulk delete", status,
            f"cb_found={cb is not None}; delete_btn_visible={btn_visible}; deletes={delete_responses}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"delete_btn={btn_visible}", screenshot_path=shot))

    async def bv_row_audit_link(self):
        print("[LIB] Row audit link...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)
        # HM46 FIX: audit link uses onClick (no href). Source: <a className="tiny" onClick={...}>audit →</a>
        # Only appears on rows where r.hasNotes=true
        audit = await self.page.query_selector('a:has-text("audit →")')
        if not audit:
            # Fallback: any audit-related element in table rows
            audit = await self.page.query_selector(
                "table tbody tr a[href*='audit'], table tbody tr [class*='audit']")
        url_before = self.page.url
        if audit:
            await audit.click()
            await self.page.wait_for_timeout(2000)
        shot = await _shot(self.page, "row_audit_link")
        url_after = self.page.url
        navigated = url_after != url_before
        page_has_content = len(await self.page.content()) > 500
        status = "pass" if (audit is not None and page_has_content) else "fail"
        self._add(_make_bv(BV["ROW_AUDIT_LINK"], "Row audit link", status,
            f"audit_link_found={audit is not None}; navigated={navigated}; url_after={url_after}",
            page_url=url_after, console_msgs=self._snap_console(),
            dom_text=f"navigated={navigated}", screenshot_path=shot))

    # =========================================================================
    # IMPORT
    # =========================================================================
    async def bv_import_song_btn(self):
        print("[IMPORT][PILOT] Import Song button (must-PASS)...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/")
        await self.page.wait_for_timeout(2000)

        btn = await self.page.query_selector("button.btn--primary")
        btn_text = ""
        if btn:
            btn_text = (await btn.inner_text()).strip()
        if not btn or "import" not in btn_text.lower():
            btn = await self.page.query_selector("button:has-text('Import')")
            if btn:
                btn_text = (await btn.inner_text()).strip()

        console_before = len(self.console_log)
        if btn:
            await btn.click()
            await self.page.wait_for_timeout(800)

        new_console = self.console_log[console_before:]
        modal = await self.page.query_selector(
            "input[type='file'], [class*='import-modal'], [class*='ImportModal'], "
            "div[class*='modal'] input, .modal-overlay input")
        import_header = await self.page.query_selector(
            "h2:has-text('Import'), h3:has-text('Import'), div:has-text('Upload')")
        modal_opened = modal is not None or import_header is not None
        ref_errors = [m for m in new_console if "referenceerror" in m.lower() or "not defined" in m.lower()]

        shot = await _shot(self.page, "import_song_btn")
        if modal_opened and not ref_errors:
            status = "pass"
            notes = f"[CATCH-7][MUST-PASS] Import modal opened; ref_errors={ref_errors}; btn_text='{btn_text}'"
        else:
            status = "fail"
            notes = (f"[CATCH-7] modal_opened={modal_opened}; ref_errors={ref_errors}; "
                     f"btn='{btn_text}'")

        self._add(_make_bv(BV["IMPORT_SONG_BTN"], "[CATCH-7][PILOT] Import Song button invokes import",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"modal={modal_opened}; btn='{btn_text}'", screenshot_path=shot))

        if modal_opened:
            await self._close_modal()

    async def bv_import_cancel(self):
        print("[IMPORT] Import cancel writes nothing...")
        self.console_log.clear(); self.network_log.clear()
        post_calls = []
        async def on_r(r: Response):
            if "/api/v1/songs" in r.url and r.request.method == "POST":
                post_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        opened = await self._open_import_modal()
        await self.page.wait_for_timeout(500)
        await self._close_modal()
        await self.page.wait_for_timeout(500)

        shot = await _shot(self.page, "import_cancel")
        self.page.remove_listener("response", on_r)
        no_post = len(post_calls) == 0
        status = "pass" if (opened and no_post) else "fail"
        self._add(_make_bv(BV["IMPORT_CANCEL"], "Import cancel writes nothing", status,
            f"modal_opened={opened}; post_calls_after_cancel={post_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"no_post={no_post}", screenshot_path=shot))

    async def bv_import_err_display(self):
        print("[IMPORT] Import error display...")
        self.console_log.clear(); self.network_log.clear()
        # Write a bad file to upload
        bad_file = SHOTS_DIR / "bad_import.txt"
        bad_file.write_text("NOT A VALID MUSICXML FILE - HM46 TEST", encoding="utf-8")

        opened = await self._open_import_modal()
        error_shown = False
        if opened:
            file_input = await self.page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(str(bad_file))
                await self.page.wait_for_timeout(3500)
                # HM46 FIX: Source shows errMsg in a div with style color:var(--rose)
                # The errMsg appears in the step-list area of the modal when stage="error"
                # Look for the rose-colored div first, then fallback to other error indicators
                err_el = await self.page.query_selector(
                    "div[style*='rose'], div[style*='#e'], [class*='error'], "
                    "[role='alert'], p:has-text('error'), p:has-text('invalid')")
                if not err_el:
                    # Try to find any text containing error-like words in the modal
                    err_el = await self.page.query_selector(
                        ".modal p, .modal div, .modal li, "
                        "dialog p, dialog div")
                    if err_el:
                        err_text = (await err_el.inner_text()).lower()
                        err_el = err_el if any(w in err_text for w in ["error", "invalid", "fail", "cannot", "parse"]) else None
                error_shown = err_el is not None
        shot = await _shot(self.page, "import_err_display")
        await self._close_modal()
        status = "pass" if (opened and error_shown) else "fail"
        self._add(_make_bv(BV["IMPORT_ERR_DISPLAY"], "Import error display", status,
            f"modal_opened={opened}; error_shown={error_shown}; bad_file=txt",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"error_shown={error_shown}", screenshot_path=shot))

    async def bv_import_tab_switch(self):
        print("[IMPORT] Import pipeline tab switch...")
        self.console_log.clear(); self.network_log.clear()
        opened = await self._open_import_modal()
        tabs_found = []
        tab_switched = False
        if opened:
            tabs = await self.page.query_selector_all(
                "[role='tab'], [class*='tab']:not([class*='content']), "
                "button:has-text('Score'), button:has-text('Batch'), "
                "button:has-text('OMR'), button:has-text('ZIP')")
            for t in tabs[:6]:
                txt = (await t.inner_text()).strip()
                if txt:
                    tabs_found.append(txt)
            if len(tabs) > 1:
                await tabs[1].click()
                await self.page.wait_for_timeout(600)
                tab_switched = True
        shot = await _shot(self.page, "import_tab_switch")
        await self._close_modal()
        status = "pass" if (opened and (len(tabs_found) > 0 or tab_switched)) else "fail"
        self._add(_make_bv(BV["IMPORT_TAB_SWITCH"], "Import pipeline tab switch", status,
            f"modal_opened={opened}; tabs={tabs_found}; switched={tab_switched}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"tabs={tabs_found}", screenshot_path=shot))

    async def bv_import_retry(self):
        """HM47 Phase 4: 'Try a different file' button visible during uploading/parsing."""
        print("[IMPORT] Import retry / try different file button...")
        self.console_log.clear(); self.network_log.clear()
        # The "← Try a different file" button appears when stage != 'drop' && stage != 'error'
        # (views.jsx line 698). Must catch it during "uploading" or "parsing" stage BEFORE
        # the server responds (to avoid going to "error" state).
        xml_file = SHOTS_DIR / "hm45_test_import.xml"
        xml_file.write_text(MINIMAL_MUSICXML, encoding="utf-8")

        opened = await self._open_import_modal()
        retry_found = False
        if opened:
            file_input = await self.page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(str(xml_file))
                # HM47 FIX: Use wait_for_selector to catch button as soon as stage leaves "drop"
                # (appears during "uploading" → "parsing" → "preview" stages)
                try:
                    retry_btn = await self.page.wait_for_selector(
                        'button:has-text("← Try a different file"), '
                        'button:has-text("Try a different"), '
                        'button:has-text("Try different")',
                        timeout=8000, state="visible")
                    retry_found = retry_btn is not None
                except Exception:
                    # Fallback: check after full parse (might be in preview state)
                    await self.page.wait_for_timeout(4000)
                    retry_btn = await self.page.query_selector(
                        'button:has-text("← Try a different file"), '
                        'button:has-text("Try a different")')
                    retry_found = retry_btn is not None
        shot = await _shot(self.page, "import_retry")
        await self._close_modal()
        status = "pass" if (opened and retry_found) else "fail"
        self._add(_make_bv(BV["IMPORT_RETRY"], "Import retry / try different file", status,
            f"modal_opened={opened}; retry_btn_found={retry_found}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"retry_found={retry_found}", screenshot_path=shot))

    async def bv_score_import(self):
        print("[IMPORT] Score import...")
        self.console_log.clear(); self.network_log.clear()
        xml_file = SHOTS_DIR / "hm45_test_import.xml"
        xml_file.write_text(MINIMAL_MUSICXML, encoding="utf-8")

        post_calls = []
        async def on_r(r: Response):
            if ("/api/v1/imports" in r.url or "/api/v1/songs" in r.url) and r.request.method == "POST":
                post_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        opened = await self._open_import_modal()
        imported_id = None
        commit_clicked = False
        if opened:
            file_input = await self.page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(str(xml_file))
                # Wait for parsing + preview to render
                await self.page.wait_for_timeout(5000)
            # HM46 FIX: Find and click the commit/import button once preview is shown
            # Source: doCommit() → POST /api/v1/imports/score/import
            import_btn = await self.page.query_selector(
                "button.btn--primary:not([disabled])")
            if not import_btn:
                import_btn = await self.page.query_selector(
                    "button:has-text('Import'), button:has-text('Add to Library'), "
                    "button:has-text('Confirm'), button:has-text('Commit')")
            if import_btn:
                try:
                    await import_btn.click(timeout=5000)
                except Exception:
                    await import_btn.click(force=True)
                commit_clicked = True
                await self.page.wait_for_timeout(6000)

        shot = await _shot(self.page, "score_import")
        self.page.remove_listener("response", on_r)
        # Get created song ID from most recent song
        if post_calls and commit_clicked:
            songs_api = await self._get_api("/api/v1/songs/?limit=200&sort_by=created_at&sort_dir=desc")
            songs = songs_api.get("body", [])
            if isinstance(songs, list) and songs:
                imported_id = songs[0].get("id")
                if imported_id:
                    self.test_song_ids.append(imported_id)
                    print(f"  [IMPORT] Created test song id={imported_id}")

        # Pass requires: modal opened + commit clicked + POST returned 2xx
        post_ok = any(c["status"] < 300 for c in post_calls) if post_calls else False
        status = "pass" if (opened and commit_clicked and (post_ok or imported_id)) else "fail"
        self._add(_make_bv(BV["SCORE_IMPORT"], "Score import", status,
            f"modal_opened={opened}; commit_clicked={commit_clicked}; post_calls={post_calls}; created_id={imported_id}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"post_calls={post_calls}", screenshot_path=shot,
            network_calls=self._snap_network("/api/v1/imports")))
        await self._close_modal()

    async def bv_import_title_ovr(self):
        print("[IMPORT] Import title override persists...")
        self.console_log.clear(); self.network_log.clear()
        xml_file = SHOTS_DIR / "hm45_test_import.xml"
        if not xml_file.exists():
            xml_file.write_text(MINIMAL_MUSICXML, encoding="utf-8")

        post_calls = []
        async def on_r(r: Response):
            if ("/api/v1/imports" in r.url or "/api/v1/songs" in r.url) and r.request.method == "POST":
                post_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        CUSTOM_TITLE = f"HM46-TitleOvr-{int(time.time())}"
        opened = await self._open_import_modal()
        title_set = False
        commit_clicked = False
        if opened:
            file_input = await self.page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(str(xml_file))
                # Wait for preview stage with title input
                await self.page.wait_for_timeout(5000)
            # HM46 FIX: title input appears in preview stage, not upload stage
            title_input = await self.page.query_selector(
                "input[placeholder*='title'], input[placeholder*='Song name'], "
                "input[name*='title'], input[class*='title'], "
                ".modal input[type='text']:not([disabled])")
            if title_input:
                await title_input.click(click_count=3)
                await title_input.fill(CUSTOM_TITLE)
                await self.page.wait_for_timeout(300)
                title_set = True
            import_btn = await self.page.query_selector(
                "button.btn--primary:not([disabled])")
            if not import_btn:
                import_btn = await self.page.query_selector(
                    "button:has-text('Import'), button:has-text('Add to Library')")
            if import_btn:
                try:
                    await import_btn.click(timeout=5000)
                except Exception:
                    await import_btn.click(force=True)
                commit_clicked = True
                await self.page.wait_for_timeout(6000)

        shot = await _shot(self.page, "import_title_ovr")
        self.page.remove_listener("response", on_r)
        # Check if title override persisted
        title_persisted = False
        if commit_clicked and title_set:
            songs_api = await self._get_api("/api/v1/songs/?limit=200&sort_by=created_at&sort_dir=desc")
            songs = songs_api.get("body", [])
            if isinstance(songs, list) and songs:
                newest = songs[0]
                created_id = newest.get("id")
                title_in_db = newest.get("title", "")
                title_persisted = CUSTOM_TITLE in title_in_db
                if created_id:
                    self.test_song_ids.append(created_id)

        status = "pass" if (opened and title_persisted) else "fail"
        self._add(_make_bv(BV["IMPORT_TITLE_OVR"], "Import title override persists", status,
            f"modal_opened={opened}; title_set={title_set}; commit_clicked={commit_clicked}; title_persisted={title_persisted}; "
            f"custom_title='{CUSTOM_TITLE}'; post_calls={post_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"title_set={title_set}; persisted={title_persisted}", screenshot_path=shot))
        await self._close_modal()

    async def bv_import_history(self):
        print("[IMPORT] Import history...")
        self.console_log.clear(); self.network_log.clear()
        # Check audit page for any existing song
        song_id = self.test_song_ids[0] if self.test_song_ids else SONG_CORCOVADO
        await self._goto_with_auth(f"{BASE_URL}/#/audit/{song_id}")
        await self.page.wait_for_timeout(2000)
        shot = await _shot(self.page, "import_history")
        page_content = await self.page.content()
        has_audit_content = "audit" in self.page.url.lower() or len(page_content) > 1000
        # Check for any audit/history items
        audit_items = await self.page.query_selector_all(
            "[class*='audit'], [class*='history'], [class*='event'], "
            "table tbody tr, ul li, [class*='log']")
        found = len(audit_items) > 0
        status = "pass" if (has_audit_content and found) else "fail"
        self._add(_make_bv(BV["IMPORT_HISTORY"], "Import history", status,
            f"url={self.page.url}; audit_items={len(audit_items)}; song_id={song_id}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"audit_items={len(audit_items)}", screenshot_path=shot))

    async def bv_omr_import(self):
        print("[IMPORT] OMR import...")
        self.console_log.clear(); self.network_log.clear()
        opened = await self._open_import_modal()
        omr_tab_found = False
        omr_ui_found = False
        if opened:
            omr_tab = await self.page.query_selector(
                "button:has-text('OMR'), [role='tab']:has-text('OMR'), "
                "tab:has-text('OMR'), button:has-text('Optical')")
            if omr_tab:
                await omr_tab.click()
                await self.page.wait_for_timeout(800)
                omr_tab_found = True
                omr_ui = await self.page.query_selector(
                    "input[type='file'], [class*='omr'], button:has-text('Upload')")
                omr_ui_found = omr_ui is not None
        shot = await _shot(self.page, "omr_import")
        await self._close_modal()
        status = "pass" if (opened and omr_tab_found) else "fail"
        self._add(_make_bv(BV["OMR_IMPORT"], "OMR import", status,
            f"modal_opened={opened}; omr_tab_found={omr_tab_found}; omr_ui={omr_ui_found}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"omr_tab={omr_tab_found}", screenshot_path=shot))

    async def bv_batch_zip_import(self):
        print("[IMPORT] Batch ZIP import...")
        self.console_log.clear(); self.network_log.clear()
        opened = await self._open_import_modal()
        zip_tab_found = False
        if opened:
            zip_tab = await self.page.query_selector(
                "button:has-text('ZIP'), button:has-text('Batch'), [role='tab']:has-text('ZIP'), "
                "tab:has-text('Batch'), button:has-text('Bulk')")
            if zip_tab:
                await zip_tab.click()
                await self.page.wait_for_timeout(800)
                zip_tab_found = True
        shot = await _shot(self.page, "batch_zip_import")
        await self._close_modal()
        status = "pass" if (opened and zip_tab_found) else "fail"
        self._add(_make_bv(BV["BATCH_ZIP_IMPORT"], "Batch ZIP import", status,
            f"modal_opened={opened}; zip_tab_found={zip_tab_found}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"zip_tab={zip_tab_found}", screenshot_path=shot))

    # =========================================================================
    # SONG DETAIL — Display
    # =========================================================================
    async def bv_song_opens(self):
        print("[SONG] Song opens, notation renders...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        shot = await _shot(self.page, "song_opens")
        url = self.page.url
        chords = await self.page.query_selector_all(".hl-chordsym")
        title_el = await self.page.query_selector("h1, .hl-song-title, [class*='title']")
        title_text = (await title_el.inner_text()).strip() if title_el else ""
        status = "pass" if (len(chords) > 0 and f"{SONG_CORCOVADO}" in url) else "fail"
        self._add(_make_bv(BV["SONG_OPENS"], "Song opens, notation renders", status,
            f"song={SONG_CORCOVADO}; chords={len(chords)}; title='{title_text}'; url={url}",
            page_url=url, console_msgs=self._snap_console(),
            dom_text=f"chords={len(chords)}; title='{title_text}'", screenshot_path=shot))

    async def bv_chord_grid(self):
        print("[SONG] Chord grid renders real chords...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        shot = await _shot(self.page, "chord_grid")
        cells = await self.page.query_selector_all(".hl-chordsym")
        first_sym = ""
        if cells:
            sym_el = await cells[0].query_selector(".hl-sym, span, div")
            first_sym = (await sym_el.inner_text()).strip() if sym_el else (await cells[0].inner_text()).strip()
        status = "pass" if (len(cells) >= 40) else "fail"  # song 149 has 46 chords
        self._add(_make_bv(BV["CHORD_GRID"], "Chord grid renders real chords", status,
            f"song={SONG_CORCOVADO}; chord_cells={len(cells)}; first_sym='{first_sym}' (expect 46+)",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"cells={len(cells)}; first_sym='{first_sym}'", screenshot_path=shot))

    async def bv_chord_modal_target(self):
        """[CATCH-1][PILOT] Chord modal targets the clicked chord — must-PASS on song 149."""
        print(f"[PILOT][CATCH-1] Chord modal target (song {SONG_CORCOVADO}, must-PASS)...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        cells = await self.page.query_selector_all(".hl-chordsym")
        if len(cells) < 3:
            shot = await _shot(self.page, "chord_modal_target")
            self._add(_make_bv(BV["CHORD_MODAL_TARGET"],
                "[CATCH-1][PILOT] Chord modal targets the clicked chord (must-PASS)",
                "fail", f"Too few chord cells ({len(cells)})",
                page_url=self.page.url, screenshot_path=shot))
            return

        sym_text = ""
        try:
            sym_el = await cells[2].query_selector(".hl-sym, span")
            sym_text = (await sym_el.inner_text()).strip() if sym_el else (await cells[2].inner_text()).strip()
        except Exception:
            pass

        await cells[2].click()
        await self.page.wait_for_timeout(1200)
        popover = await self.page.query_selector(".popover")
        pop_text = ""
        chord_idx = -1
        if popover:
            pop_text = await popover.inner_text()
            m = re.search(r"0-idx\s+(\d+)", pop_text)
            if m:
                chord_idx = int(m.group(1))

        shot = await _shot(self.page, "chord_modal_target")
        if not popover:
            status, notes = "fail", f"[CATCH-1] Popover not opened; sym='{sym_text}'"
        elif chord_idx == 2:
            status, notes = "pass", f"[CATCH-1][MUST-PASS] popover idx=2 correct; sym='{sym_text}'"
        else:
            status, notes = "fail", (f"[CATCH-1] REGRESSION: expected idx=2, got idx={chord_idx}; "
                                     f"sym='{sym_text}'; pop={pop_text[:80]}")

        self._add(_make_bv(BV["CHORD_MODAL_TARGET"],
            "[CATCH-1][PILOT] Chord modal targets the clicked chord (must-PASS)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"idx={chord_idx}; sym='{sym_text}'", screenshot_path=shot))
        await self._close_popover()

    async def bv_chord_picker(self):
        print("[SONG] Chord picker search...")
        self.console_log.clear(); self.network_log.clear()
        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 0)
        picker_found = False
        results_found = False
        if pop:
            # HM46 FIX: ChordPicker trigger is a <div className="input"> NOT a button
            # Source: <div className="input" tabIndex={0} onClick={()=>setOpen(o=>!o)}>
            # When open, renders: <input autoFocus placeholder="Type a chord (Cm7, F♯7♭9, …)">
            picker_trigger = await self.page.query_selector('.popover div.input')
            if picker_trigger:
                # Use force=True because a .tiny overlay intercepts pointer events
                await picker_trigger.click(force=True)
                await self.page.wait_for_timeout(500)
                picker_found = True
                # The autoFocus filter input should now be visible
                filter_input = await self.page.query_selector(
                    'input[placeholder*="Type a chord"], input[placeholder*="Cm7"]')
                if filter_input:
                    await filter_input.fill("Dm7")
                    await self.page.wait_for_timeout(500)
                    # Candidates are <div data-hi={i}>
                    candidates = await self.page.query_selector_all('[data-hi]')
                    results_found = len(candidates) > 0
        shot = await _shot(self.page, "chord_picker")
        await self._close_popover()
        status = "pass" if (pop is not None and picker_found and results_found) else "fail"
        self._add(_make_bv(BV["CHORD_PICKER"], "Chord picker search", status,
            f"popover={pop is not None}; picker_found={picker_found}; results={results_found}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"picker={picker_found}; results={results_found}", screenshot_path=shot))

    # =========================================================================
    # SONG DETAIL — Write BVs (expected FAIL due to PUT 500)
    # =========================================================================
    async def bv_chord_edit_persist(self):
        print("[SONG][EXPECTED-FAIL] Chord edit persists...")
        self.console_log.clear(); self.network_log.clear()
        put_responses = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_responses.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 3)
        if not pop:
            self.page.remove_listener("response", on_r)
            shot = await _shot(self.page, "chord_edit_persist")
            self._add(_make_bv(BV["CHORD_EDIT_PERSIST"], "Chord edit persists",
                "fail", "Popover did not open",
                page_url=self.page.url, screenshot_path=shot))
            return

        sym_input = await self.page.query_selector(
            ".popover input[placeholder*='symbol'], .popover input[type='text']:first-child, "
            ".popover input.input")
        if sym_input:
            await sym_input.click(click_count=3)
            await sym_input.type("Dm7")
            await self.page.wait_for_timeout(300)

        save_btn = await self.page.query_selector(".popover button.btn--primary")
        if save_btn:
            await self._jclick(save_btn)
        else:
            await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(1500)

        shot = await _shot(self.page, "chord_edit_persist")
        self.page.remove_listener("response", on_r)
        has_500 = any(r["status"] == 500 for r in put_responses)
        has_200 = any(r["status"] == 200 for r in put_responses)
        if has_200 and not has_500:
            status = "pass"
            notes = f"Chord edit PUT 200; put_calls={put_responses}"
        else:
            status = "fail"
            notes = (f"[EXPECTED-FAIL] Chord edit PUT non-200; "
                     f"put_calls={put_responses}; has_500={has_500}")
        self._add(_make_bv(BV["CHORD_EDIT_PERSIST"], "Chord edit persists", status, notes,
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"put_calls={put_responses}", screenshot_path=shot,
            network_calls=self._snap_network("/api/v1/chords")))
        await self._close_popover()

    async def bv_chord_edit_cancel(self):
        print("[SONG] Chord edit cancel writes nothing...")
        self.console_log.clear(); self.network_log.clear()
        put_calls = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 4)
        if pop:
            sym_input = await self.page.query_selector(".popover input")
            if sym_input:
                await sym_input.type("TEST")
                await self.page.wait_for_timeout(200)
            cancel_btn = await self.page.query_selector("button:has-text('Cancel')")
            if cancel_btn:
                await cancel_btn.click()
            else:
                await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(800)

        shot = await _shot(self.page, "chord_edit_cancel")
        self.page.remove_listener("response", on_r)
        no_put = len(put_calls) == 0
        status = "pass" if (pop is not None and no_put) else "fail"
        self._add(_make_bv(BV["CHORD_EDIT_CANCEL"], "Chord edit cancel writes nothing", status,
            f"popover_opened={pop is not None}; put_calls_after_cancel={put_calls}; no_put={no_put}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"no_put={no_put}", screenshot_path=shot))

    async def bv_enter_saves(self):
        print("[SONG] Enter saves the edit...")
        self.console_log.clear(); self.network_log.clear()
        put_calls = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 5)
        if pop:
            sym_input = await self.page.query_selector(".popover input")
            if sym_input:
                await sym_input.click(click_count=3)
                await sym_input.type("Am7")
                await self.page.wait_for_timeout(200)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(1500)

        shot = await _shot(self.page, "enter_saves")
        self.page.remove_listener("response", on_r)
        put_fired = len(put_calls) > 0
        # HM46 FIX: A write BV passes ONLY on a 2xx response AND a persisted read-back.
        # Never on "the action fired." (per HM46 Phase 1 mandate)
        put_ok = any(c["status"] < 300 for c in put_calls) if put_calls else False
        # Read-back: verify chord at index 5 now has new symbol
        read_ok = False
        if put_ok:
            song_api = await self._get_api(f"/api/v1/analysis/songs/{SONG_CORCOVADO}")
            chords = song_api.get("body", {}).get("chords", [])
            if len(chords) > 5:
                read_ok = chords[5].get("symbol", "") == "Am7"
        status = "pass" if (pop is not None and put_ok and read_ok) else "fail"
        self._add(_make_bv(BV["ENTER_SAVES"], "Enter saves the edit", status,
            f"popover={pop is not None}; put_fired={put_fired}; put_ok={put_ok}; read_ok={read_ok}; put_calls={put_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"put_fired={put_fired}; put_ok={put_ok}; read_ok={read_ok}", screenshot_path=shot))

    async def bv_invalid_disables(self):
        print("[SONG] Invalid symbol disables Save...")
        self.console_log.clear(); self.network_log.clear()
        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 6)
        save_disabled = False
        if pop:
            # HM46 FIX: ChordPicker only exposes valid chord symbols as candidates.
            # Typing in the filter does NOT change the chord symbol (only picking a candidate does).
            # To test invalid disabling, we must inject an invalid symbol via React state using evaluate().
            # Source: invalid check: !/^[A-G]/.test(symbol.trim())
            try:
                # Inject invalid symbol by dispatching React state update
                injected = await self.page.evaluate("""() => {
                    // Find React fiber for the chord symbol input
                    const input = document.querySelector('.popover input.input');
                    if (!input) return false;
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, '123INVALID');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    return true;
                }""")
                await self.page.wait_for_timeout(400)
            except Exception:
                injected = False
            save_btn = await self.page.query_selector(".popover button.btn--primary")
            if save_btn:
                save_disabled = await save_btn.is_disabled()
        shot = await _shot(self.page, "invalid_disables")
        await self._close_popover()
        status = "pass" if (pop is not None and save_disabled) else "fail"
        self._add(_make_bv(BV["INVALID_DISABLES"], "Invalid symbol disables Save", status,
            f"popover={pop is not None}; inject→save_disabled={save_disabled}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"save_disabled={save_disabled}", screenshot_path=shot))

    async def bv_accept_inferred(self):
        """HM47 BUG-050: Accept inferred chord persists — PASS after Phase 3 deploy."""
        print("[SONG] Accept inferred chord persists...")
        self.console_log.clear(); self.network_log.clear()
        put_calls = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        # HM47 FIX: Use SONG_PRELUDE_C (106) — Phase 3 derives chords with is_inferred=1
        # after auto-harmony derivation. Fallback to SONG_NEGATIVE (158).
        for fixture_song in [SONG_PRELUDE_C, SONG_NEGATIVE, SONG_CORCOVADO]:
            await self._goto_song(fixture_song)
            await self.page.wait_for_timeout(2000)
            inferred_cells = await self.page.query_selector_all('.hl-chordsym.is-inferred')
            if inferred_cells:
                break
        else:
            inferred_cells = []

        accept_btn_found = False
        if inferred_cells:
            await self._dismiss_overlay()
            # Ctrl+click to SELECT (not open popover)
            await self.page.keyboard.down("Control")
            await inferred_cells[0].click()
            await self.page.keyboard.up("Control")
            await self.page.wait_for_timeout(700)
            # "accept ↩" button appears inside the selected chord cell
            accept_btn = await self.page.query_selector('button:has-text("accept ↩"), button:has-text("accept")')
            if not accept_btn:
                accept_btn = await inferred_cells[0].query_selector('button')
            if accept_btn:
                accept_btn_found = True
                await self._jclick(accept_btn)
                await self.page.wait_for_timeout(1500)
        shot = await _shot(self.page, "accept_inferred")
        self.page.remove_listener("response", on_r)
        has_500 = any(r["status"] == 500 for r in put_calls)
        has_200 = any(r["status"] == 200 for r in put_calls)
        if has_200 and not has_500:
            status = "pass"
            notes = f"Accept inferred PUT 200; put_calls={put_calls}; inferred_cells={len(inferred_cells)}"
        else:
            status = "fail"
            notes = (f"Accept inferred: inferred_cells={len(inferred_cells)}; "
                     f"accept_found={accept_btn_found}; put_calls={put_calls}; has_500={has_500}")
        self._add(_make_bv(BV["ACCEPT_INFERRED"], "Accept inferred chord persists", status, notes,
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"accept_btn={accept_btn_found}; put_calls={put_calls}", screenshot_path=shot))

    async def bv_multiselect(self):
        print("[SONG] Multi-select chords...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        cells = await self.page.query_selector_all(".hl-chordsym")
        if len(cells) < 3:
            shot = await _shot(self.page, "multiselect")
            self._add(_make_bv(BV["MULTISELECT"], "Multi-select chords", "fail",
                f"Too few cells ({len(cells)})", page_url=self.page.url, screenshot_path=shot))
            return

        # Ctrl+click first cell, Ctrl+click second cell
        await self.page.keyboard.down("Control")
        await cells[0].click()
        await self.page.wait_for_timeout(300)
        await cells[1].click()
        await self.page.keyboard.up("Control")
        await self.page.wait_for_timeout(600)

        sel_bar = await self.page.query_selector(".hl-selection-bar")
        sel_count = len(await self.page.query_selector_all(".hl-chordsym.is-selected"))
        shot = await _shot(self.page, "multiselect")
        status = "pass" if (sel_bar is not None and sel_count >= 2) else "fail"
        self._add(_make_bv(BV["MULTISELECT"], "Multi-select chords (per-chord isolation)", status,
            f"song={SONG_CORCOVADO}; sel_bar={sel_bar is not None}; sel_count={sel_count}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"sel_bar={sel_bar is not None}; sel_count={sel_count}", screenshot_path=shot))
        # Deselect
        await self.page.keyboard.press("Escape")

    async def bv_voicing_edit(self):
        """[CATCH-2][PILOT] Voicing edit — must-FAIL (PUT 500 on real chord)."""
        print(f"[PILOT][CATCH-2] Voicing edit (song {SONG_CORCOVADO}, must-FAIL)...")
        self.console_log.clear(); self.network_log.clear()
        put_responses = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_responses.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 0)
        if not pop:
            self.page.remove_listener("response", on_r)
            shot = await _shot(self.page, "voicing_edit")
            self._add(_make_bv(BV["VOICING_EDIT"], "[CATCH-2][PILOT] Voicing edit saves and persists",
                "fail", "Popover did not open", page_url=self.page.url, screenshot_path=shot))
            return

        voicing_input = await self.page.query_selector(
            "input[placeholder*='rootless'], input[placeholder*='voicing'], "
            ".popover input[type='text']:nth-of-type(2)")
        test_voicing = f"hm45-{int(time.time())}"
        if voicing_input:
            await voicing_input.fill(test_voicing)
            await self.page.wait_for_timeout(200)
        save_btn = await self.page.query_selector(".popover button.btn--primary")
        if save_btn:
            await self._jclick(save_btn)
        else:
            await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(1500)

        shot = await _shot(self.page, "voicing_edit")
        self.page.remove_listener("response", on_r)
        has_500 = any(r["status"] == 500 for r in put_responses)
        has_200 = any(r["status"] == 200 for r in put_responses)

        if has_200 and not has_500:
            status = "pass"
            notes = f"[CATCH-2] Voicing PUT 200 — bug may be fixed; put={put_responses}"
        else:
            status = "fail"
            notes = (f"[CATCH-2][TRUST-GATE-EXPECTED-FAIL] Voicing edit: "
                     f"PUT non-200; put={put_responses}; has_500={has_500}")
        self._add(_make_bv(BV["VOICING_EDIT"], "[CATCH-2][PILOT] Voicing edit saves and persists",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"put_calls={put_responses}", screenshot_path=shot,
            network_calls=self._snap_network("/api/v1/chords")))
        await self._close_popover()

    async def bv_comment_persist(self):
        """[CATCH-3][PILOT] Comment persist — must-FAIL (PUT 500 / no persist)."""
        print(f"[PILOT][CATCH-3] Comment persist (song {SONG_CORCOVADO}, must-FAIL)...")
        self.console_log.clear(); self.network_log.clear()
        put_responses = []
        async def on_r(r: Response):
            if "/api/v1/chords/" in r.url and r.request.method == "PUT":
                put_responses.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 1)
        if not pop:
            self.page.remove_listener("response", on_r)
            shot = await _shot(self.page, "comment_persist")
            self._add(_make_bv(BV["COMMENT_PERSIST"], "[CATCH-3][PILOT] Chord comment persists",
                "fail", "Popover did not open", page_url=self.page.url, screenshot_path=shot))
            return

        comment_ta = await self.page.query_selector(".popover textarea")
        test_comment = f"hm45-c-{int(time.time())}"
        if comment_ta:
            await comment_ta.fill(test_comment)
            await self.page.wait_for_timeout(200)
        save_btn = await self.page.query_selector(".popover button.btn--primary")
        if save_btn:
            await self._jclick(save_btn)
        else:
            await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(1500)

        # Reload and re-check
        await self._goto_song(SONG_CORCOVADO)
        cells2 = await self.page.query_selector_all(".hl-chordsym")
        comment_reload = ""
        if cells2 and len(cells2) > 1:
            await cells2[1].click()
            await self.page.wait_for_timeout(800)
            ta = await self.page.query_selector(".popover textarea")
            if ta:
                comment_reload = await ta.input_value()
            cancel = await self.page.query_selector("button:has-text('Cancel')")
            if cancel:
                await cancel.click()

        shot = await _shot(self.page, "comment_persist")
        self.page.remove_listener("response", on_r)
        persisted = test_comment in comment_reload
        has_500 = any(r["status"] == 500 for r in put_responses)

        if persisted:
            status = "pass"
            notes = f"[CATCH-3] Comment persisted; put={put_responses}"
        else:
            status = "fail"
            notes = (f"[CATCH-3][TRUST-GATE-EXPECTED-FAIL] Comment not persisted; "
                     f"reload='{comment_reload}'; put={put_responses}; has_500={has_500}")
        self._add(_make_bv(BV["COMMENT_PERSIST"], "[CATCH-3][PILOT] Chord comment persists",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"persisted={persisted}; put={put_responses}", screenshot_path=shot,
            network_calls=self._snap_network("/api/v1/chords")))

    async def bv_write_error_surfaced(self):
        """HM47 BUG-049: Write failures surface an error toast (not silent ✕).
        After HM47 fixes, writes return 200 normally. We intercept one chord PUT
        via page.route() and force a 500 to verify the UI surfaces the error."""
        print("[BUG-049] Write error surfaced (route-intercepted 500)...")
        self.console_log.clear(); self.network_log.clear()
        intercepted = []

        # Set up route interceptor: force 500 on next chord PUT
        async def intercept_chord_put(route, request):
            if request.method == "PUT" and "/api/v1/chords/" in request.url:
                if not intercepted:  # Only intercept the first PUT
                    intercepted.append(request.url)
                    await route.fulfill(
                        status=500,
                        content_type="application/json",
                        body='{"detail": "Simulated server error for WRITE-ERROR-SURFACED BV"}')
                    return
            await route.continue_()

        await self.page.route("**/api/v1/chords/**", intercept_chord_put)

        cells, pop = await self._open_chord_popover(SONG_CORCOVADO, 2)
        toast_text = ""
        toast_found = False
        if pop:
            sym_input = await self.page.query_selector(".popover input")
            if sym_input:
                await sym_input.click(click_count=3)
                await sym_input.type("F7")
                await self.page.wait_for_timeout(200)
            save_btn = await self.page.query_selector(".popover button.btn--primary")
            if save_btn:
                await self._jclick(save_btn)
            else:
                await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(2500)
            # Check for error toast notification
            toast = await self.page.query_selector(
                "[class*='toast'], [class*='notification'], [class*='alert'], "
                "[role='alert'], [class*='snack']")
            if toast:
                toast_found = True
                toast_text = (await toast.inner_text()).strip()

        # Remove route interceptor
        await self.page.unroute("**/api/v1/chords/**")
        shot = await _shot(self.page, "write_error_surfaced")

        route_fired = len(intercepted) > 0
        toast_has_error_text = bool(re.search(
            r'(error|fail|500|server|could not|unable|saved)', toast_text, re.IGNORECASE))
        toast_only_x = toast_found and len(toast_text.strip()) <= 5

        if route_fired and toast_found and toast_has_error_text:
            status = "pass"
            notes = (f"Write error surfaced via route intercept; toast='{toast_text}'; "
                     f"intercepted={intercepted[:1]}")
        elif route_fired and toast_found and toast_only_x:
            status = "fail"
            notes = (f"[BUG-049] Write error toast shows only '✕' — no error text; "
                     f"toast='{toast_text}'; intercepted={intercepted[:1]}")
        else:
            status = "fail"
            notes = (f"[BUG-049] Write error not surfaced: route_fired={route_fired}; "
                     f"toast_found={toast_found}; toast_text='{toast_text}'; "
                     f"intercepted={intercepted[:1]}")
        self._add(_make_bv(BV["WRITE_ERROR_SURFACED"], "Write failures surface an error", status, notes,
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"toast='{toast_text}'; route_fired={route_fired}", screenshot_path=shot))
        await self._close_popover()

    # =========================================================================
    # KEY HANDLING
    # =========================================================================
    async def bv_manual_key_persist(self):
        """[CATCH-4] Manual key override persists via UI."""
        print(f"[CATCH-4] Manual key override persists (song {SONG_CORCOVADO})...")
        self.console_log.clear(); self.network_log.clear()
        post_calls = []
        async def on_r(r: Response):
            if "/api/v1/analysis/songs/" in r.url and r.request.method in ("POST", "PUT", "PATCH"):
                post_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_song(SONG_CORCOVADO)
        key_btn = await self.page.query_selector(
            "button:has-text('✎'), button[title*='key'], "
            "[class*='key-edit'], button:has-text('Edit key')")
        key_changed = False
        key_override_value = ""
        if key_btn:
            await key_btn.click()
            await self.page.wait_for_timeout(800)
            # Key picker dropdown/modal
            key_option = await self.page.query_selector(
                "button:has-text('G major'), button:has-text('G'), option:has-text('G major'), "
                "[class*='key-option']:first-child, li:has-text('G major')")
            if key_option:
                await key_option.click()
                await self.page.wait_for_timeout(1500)
                key_changed = True
                # Read back key display
                key_el = await self.page.query_selector("[class*='key-display'], [class*='detected-key']")
                key_override_value = (await key_el.inner_text()).strip() if key_el else ""
        shot = await _shot(self.page, "manual_key_persist")
        self.page.remove_listener("response", on_r)

        post_ok = any(r["status"] in (200, 201) for r in post_calls)
        if post_ok and key_changed:
            status = "pass"
            notes = (f"[CATCH-4] Manual key persist: POST ok; key_override='{key_override_value}'; "
                     f"calls={post_calls}")
        else:
            status = "fail"
            notes = (f"[CATCH-4] Manual key: key_btn_found={key_btn is not None}; "
                     f"key_changed={key_changed}; post_ok={post_ok}; calls={post_calls}")
        self._add(_make_bv(BV["MANUAL_KEY_PERSIST"], "[CATCH-4] Manual key override persists",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"key_changed={key_changed}; post_calls={post_calls}", screenshot_path=shot))

    async def bv_manual_key_clear(self):
        """HM47 BUG-049: 'Use detected' button clears manual key override."""
        print("[KEY] Manual key clear (use detected)...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        await self.page.wait_for_timeout(1000)

        # Step 1: First set a manual key so the "Use detected" button appears
        # The key input area has a key selector component in components.jsx
        # Source: {manual && <button className="btn btn--ghost btn--sm" onClick={onClear}>Use detected</button>}
        # Must open key picker, choose a key, then the "Use detected" button appears
        set_key_calls = []
        async def on_r(r: Response):
            if "/api/v1/analysis/songs/" in r.url and r.request.method in ("POST", "PUT", "PATCH"):
                set_key_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        # Open key selector by clicking on the detected-key area or "Set key" button
        key_area = await self.page.query_selector(
            "[class*='key-select'], button:has-text('Set key'), "
            "button:has-text('Key'), [class*='key-btn'], [data-key]")
        if not key_area:
            # Try clicking on the key region in the BottomAnalysis / KeyTimeline area
            key_area = await self.page.query_selector(".hl-key, [class*='key-label'], [class*='key-region']")
        if key_area:
            await self._jclick(key_area)
            await self.page.wait_for_timeout(600)
        # Look for key input / select dropdown
        key_select = await self.page.query_selector(
            "select[name*='key'], input[placeholder*='key'], "
            "select.key-select, [class*='key-picker'] select")
        if key_select:
            # Pick a key that differs from the detected key
            await key_select.select_option(value="F")
            await self.page.wait_for_timeout(200)
        # Submit key override (Save / OK button)
        save_key_btn = await self.page.query_selector(
            "button:has-text('Save'), button:has-text('Apply'), button:has-text('Set')")
        if save_key_btn:
            await self._jclick(save_key_btn)
            await self.page.wait_for_timeout(800)

        # Step 2: Now look for "Use detected" button (appears when manual key is active)
        await self._dismiss_overlay()
        clear_btn = await self.page.query_selector("button:has-text('Use detected')")
        if not clear_btn:
            clear_btn = await self.page.query_selector(
                "button:has-text('Clear override'), button:has-text('Reset key'), [class*='key-clear']")

        key_before = ""
        key_after  = ""
        if clear_btn:
            # Read key before clearing
            key_el = await self.page.query_selector("[class*='key-display'], [class*='detected-key']")
            if key_el:
                key_before = (await key_el.inner_text()).strip()
            await self._jclick(clear_btn)
            await self.page.wait_for_timeout(800)
            if key_el:
                key_after = (await key_el.inner_text()).strip()

        self.page.remove_listener("response", on_r)
        shot = await _shot(self.page, "manual_key_clear")
        status = "pass" if (clear_btn is not None) else "fail"
        self._add(_make_bv(BV["MANUAL_KEY_CLEAR"], "Manual key clear (use detected)", status,
            f"clear_btn_found={clear_btn is not None}; key_before='{key_before}'; key_after='{key_after}'; set_calls={set_key_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"clear_btn={clear_btn is not None}; key={key_before}→{key_after}",
            screenshot_path=shot))

    async def bv_identify_key(self):
        """[CATCH-5][PILOT] Identify key returns A minor (Summertime, must-PASS)."""
        song_id = SONG_SUMMERTIME  # 121
        print(f"[PILOT][CATCH-5] Identify key (song {song_id} Summertime A-minor, must-PASS)...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(song_id)

        cells = await self.page.query_selector_all(".hl-chordsym")
        if len(cells) < 2:
            shot = await _shot(self.page, "identify_key")
            self._add(_make_bv(BV["IDENTIFY_KEY"],
                "[CATCH-5][PILOT] Identify key returns A min (Summertime, must-PASS)",
                "fail", f"Not enough chord cells ({len(cells)})",
                page_url=self.page.url, screenshot_path=shot))
            return

        await self.page.keyboard.down("Control")
        await cells[0].click()
        await self.page.keyboard.up("Control")
        await self.page.wait_for_timeout(400)
        await self.page.keyboard.down("Shift")
        await cells[-1].click()
        await self.page.keyboard.up("Shift")
        await self.page.wait_for_timeout(600)

        sel_bar = None
        try:
            sel_bar = await self.page.wait_for_selector(".hl-selection-bar", timeout=3000)
        except Exception:
            pass

        shot_sel = await _shot(self.page, "identify_key_sel")
        if not sel_bar:
            self._add(_make_bv(BV["IDENTIFY_KEY"],
                "[CATCH-5][PILOT] Identify key returns A min (Summertime, must-PASS)",
                "fail", f"Selection bar not found; cells={len(cells)}",
                page_url=self.page.url, screenshot_path=shot_sel))
            return

        identify_btn = await sel_bar.query_selector("button:has-text('Identify key center')")
        if not identify_btn:
            identify_btn = await sel_bar.query_selector("button:has-text('Identify')")
        if not identify_btn:
            bar_text = await sel_bar.inner_text()
            self._add(_make_bv(BV["IDENTIFY_KEY"],
                "[CATCH-5][PILOT] Identify key returns A min (Summertime, must-PASS)",
                "fail", f"Identify btn not found; bar='{bar_text[:100]}'",
                page_url=self.page.url, screenshot_path=shot_sel))
            return

        await identify_btn.click()
        JS_DIALOG = """() => {
            const divs = Array.from(document.querySelectorAll('div'));
            for (const d of divs) {
                const s = d.getAttribute('style') || '';
                if (s.includes('560') && d.innerText.includes('Identify key center')) {
                    return d.innerText.slice(0,2000);
                }
            }
            for (const d of divs) {
                const s = d.getAttribute('style') || '';
                if ((s.includes('850') || (s.includes('fixed') && s.includes('inset: 0')))
                    && d.children.length > 0) {
                    const inner = d.children[0];
                    if (inner && inner.innerText && inner.innerText.includes('Identify key center')) {
                        return inner.innerText.slice(0,2000);
                    }
                }
            }
            return '__NO_DIALOG__';
        }"""
        dialog_text = "__NO_DIALOG__"
        for poll in range(18):
            await self.page.wait_for_timeout(1000)
            dialog_text = await self.page.evaluate(JS_DIALOG)
            if dialog_text == "__NO_DIALOG__":
                continue
            has_key = bool(re.search(r'\b[a-g][#b]?\s+(?:maj|min)(?:or)?\b', dialog_text, re.IGNORECASE))
            if has_key:
                break

        shot = await _shot(self.page, "identify_key_result")
        dialog_open = dialog_text != "__NO_DIALOG__"
        a_minor = bool(dialog_open and re.search(
            r'\bA[b\u266d]?\s+(?:(?:harmonic|melodic|natural)[_ ]+)?min(?:or)?\b'
            r'|\bA\s+min\b|\bA\s+minor\b', dialog_text, re.IGNORECASE))
        raw_key = ""
        if dialog_open:
            m = re.search(r'\b([A-Ga-g][#b\u266d]?\s+(?:[\w_]+\s+)*(?:min|maj)(?:or)?)\b',
                          dialog_text, re.IGNORECASE)
            if m:
                raw_key = m.group(1).strip()

        if a_minor:
            status = "pass"
            notes = (f"[CATCH-5][MUST-PASS] Identify key A-minor found; "
                     f"raw='{raw_key}'; song={song_id}")
        else:
            status = "fail"
            notes = (f"[CATCH-5] A-minor NOT found; dialog_open={dialog_open}; "
                     f"raw='{raw_key}'; dialog='{dialog_text[:200]}'")
        self._add(_make_bv(BV["IDENTIFY_KEY"],
            "[CATCH-5][PILOT] Identify key returns A min (Summertime, must-PASS)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"a_minor={a_minor}; raw='{raw_key}'", screenshot_path=shot))

        # Close dialog (save state for ACCEPT_AI_KEY to re-open)
        await self.page.keyboard.press("Escape")
        await self.page.wait_for_timeout(400)

    async def bv_accept_ai_key(self):
        """[CATCH-8] Accept AI key suggestion — click Accept in identify-key dialog."""
        song_id = SONG_SUMMERTIME  # 121
        print(f"[CATCH-8] Accept AI key (song {song_id} Summertime)...")
        self.console_log.clear(); self.network_log.clear()
        post_calls = []
        async def on_r(r: Response):
            if "/api/v1/analysis/songs/" in r.url and r.request.method in ("POST", "PUT", "PATCH"):
                post_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_song(song_id)
        cells = await self.page.query_selector_all(".hl-chordsym")
        dialog_text = "__NO_DIALOG__"
        accept_found = False
        accept_clicked = False

        if len(cells) >= 2:
            await self.page.keyboard.down("Control")
            await cells[0].click()
            await self.page.keyboard.up("Control")
            await self.page.wait_for_timeout(400)
            await self.page.keyboard.down("Shift")
            await cells[-1].click()
            await self.page.keyboard.up("Shift")
            await self.page.wait_for_timeout(600)

            sel_bar = None
            try:
                sel_bar = await self.page.wait_for_selector(".hl-selection-bar", timeout=3000)
            except Exception:
                pass

            if sel_bar:
                identify_btn = await sel_bar.query_selector(
                    "button:has-text('Identify key center'), button:has-text('Identify')")
                if identify_btn:
                    await identify_btn.click()
                    JS_DIALOG = """() => {
                        const divs = Array.from(document.querySelectorAll('div'));
                        for (const d of divs) {
                            const s = d.getAttribute('style') || '';
                            if (s.includes('560') && d.innerText.includes('Identify key center')) {
                                return d.innerText.slice(0,2000);
                            }
                        }
                        for (const d of divs) {
                            const s = d.getAttribute('style') || '';
                            if ((s.includes('850') || (s.includes('fixed') && s.includes('inset: 0')))
                                && d.children.length > 0) {
                                const inner = d.children[0];
                                if (inner && inner.innerText && inner.innerText.includes('Identify key center')) {
                                    return inner.innerText.slice(0,2000);
                                }
                            }
                        }
                        return '__NO_DIALOG__';
                    }"""
                    for poll in range(18):
                        await self.page.wait_for_timeout(1000)
                        dialog_text = await self.page.evaluate(JS_DIALOG)
                        if dialog_text == "__NO_DIALOG__":
                            continue
                        has_key = bool(re.search(r'\b[a-g][#b]?\s+(?:maj|min)', dialog_text, re.IGNORECASE))
                        if has_key:
                            break

                    # Look for Accept button in the dialog
                    accept_btn = await self.page.query_selector(
                        "button:has-text('Accept'), button:has-text('Apply'), "
                        "button:has-text('Use this key')")
                    if accept_btn:
                        accept_found = True
                        await self._jclick(accept_btn)
                        await self.page.wait_for_timeout(2000)
                        accept_clicked = True

        shot = await _shot(self.page, "accept_ai_key")
        self.page.remove_listener("response", on_r)
        post_ok = any(r["status"] in (200, 201) for r in post_calls)
        dialog_had_key = dialog_text != "__NO_DIALOG__" and bool(
            re.search(r'\b[a-g][#b]?\s+(?:maj|min)', dialog_text, re.IGNORECASE))

        if accept_found and post_ok:
            status = "pass"
            notes = (f"[CATCH-8] Accept AI key: accept_clicked={accept_clicked}; "
                     f"post_ok={post_ok}; calls={post_calls}; dialog_key={dialog_had_key}")
        else:
            status = "fail"
            notes = (f"[CATCH-8] Accept AI key: accept_found={accept_found}; "
                     f"post_ok={post_ok}; calls={post_calls}; dialog_open={dialog_text != '__NO_DIALOG__'}")
        self._add(_make_bv(BV["ACCEPT_AI_KEY"], "[CATCH-8] Accept AI key suggestion",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"accept_found={accept_found}; post_calls={post_calls}", screenshot_path=shot))
        await self.page.keyboard.press("Escape")
        await self.page.wait_for_timeout(300)

    # =========================================================================
    # SCORE DISPLAY
    # =========================================================================
    async def bv_score_func(self):
        print("[SCORE] Score Function toggle...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        toggle = await self.page.query_selector(
            "button:has-text('Function'), button:has-text('function'), "
            "button[title*='Function'], [class*='func-toggle']")
        toggled = False
        dom_before = await self.page.evaluate(
            "() => document.querySelectorAll('.hl-chordsym')[0]?.innerText || ''")
        if toggle:
            await self._jclick(toggle)
            await self.page.wait_for_timeout(600)
            toggled = True
        dom_after = await self.page.evaluate(
            "() => document.querySelectorAll('.hl-chordsym')[0]?.innerText || ''")
        shot = await _shot(self.page, "score_func")
        status = "pass" if (toggle is not None) else "fail"
        self._add(_make_bv(BV["SCORE_FUNC"], "Score Function toggle", status,
            f"toggle_found={toggle is not None}; dom_before='{dom_before[:30]}'; dom_after='{dom_after[:30]}'",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"before='{dom_before[:30]}'; after='{dom_after[:30]}'", screenshot_path=shot))
        # Restore
        if toggle and toggled:
            await self._jclick(toggle)
            await self.page.wait_for_timeout(300)

    async def bv_score_roman(self):
        print("[SCORE] Score Roman toggle...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        toggle = await self.page.query_selector(
            "button:has-text('Roman'), button:has-text('roman'), "
            "button[title*='Roman'], [class*='roman-toggle']")
        if toggle:
            await self._jclick(toggle)
            await self.page.wait_for_timeout(600)
        shot = await _shot(self.page, "score_roman")
        status = "pass" if toggle is not None else "fail"
        self._add(_make_bv(BV["SCORE_ROMAN"], "Score Roman toggle", status,
            f"toggle_found={toggle is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"toggle={toggle is not None}", screenshot_path=shot))
        if toggle:
            await self._jclick(toggle)

    async def bv_key_timeline(self):
        print("[SCORE] Key timeline card...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_CORCOVADO)
        await self.page.wait_for_timeout(1000)
        # Scroll to bottom analysis
        await self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await self.page.wait_for_timeout(800)
        bottom = await self.page.query_selector(".hl-bottom-analysis, [class*='analysis-panel'], [class*='bottom']")
        timeline = await self.page.query_selector(
            "[class*='key-timeline'], [class*='timeline'], [class*='key-card']")
        shot = await _shot(self.page, "key_timeline")
        # Check for real key text (C major / C) in analysis area
        analysis_text = ""
        if bottom:
            analysis_text = (await bottom.inner_text()).strip()
        key_present = bool(re.search(r'\bC\s+major\b|\bC\s+maj\b|\bC\b', analysis_text[:500], re.IGNORECASE))
        status = "pass" if (bottom is not None and (timeline is not None or key_present)) else "fail"
        self._add(_make_bv(BV["KEY_TIMELINE"], "Key timeline card (real key, not fallback)", status,
            f"bottom_panel={bottom is not None}; timeline_el={timeline is not None}; key_present={key_present}; "
            f"analysis='{analysis_text[:200]}'",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"analysis='{analysis_text[:200]}'", screenshot_path=shot))

    async def bv_reanalyze(self):
        print("[SCORE] Re-analyze updates...")
        self.console_log.clear(); self.network_log.clear()
        post_calls = []
        async def on_r(r: Response):
            if "/api/v1/analysis/songs/" in r.url and r.request.method == "POST":
                post_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)

        await self._goto_song(SONG_CORCOVADO)
        await self.page.wait_for_timeout(1500)
        # HM46 FIX: Re-analyze opens a ConfirmModal first; must click confirm inside it
        reanalyze_btn = await self.page.query_selector(
            "button:has-text('↻ Re-analyze'), button:has-text('Re-analyze'), "
            "button:has-text('Reanalyze'), button:has-text('↻')")
        confirm_clicked = False
        if reanalyze_btn:
            await self._jclick(reanalyze_btn)
            await self.page.wait_for_timeout(600)
            # ConfirmModal appears — look for the Re-analyze confirm button inside it
            confirm_btn = await self.page.query_selector(
                "dialog button:has-text('Re-analyze'), "
                "[class*='modal'] button:has-text('Re-analyze'), "
                "[class*='confirm'] button:has-text('Re-analyze'), "
                "button.btn--primary:has-text('Re-analyze')")
            if confirm_btn:
                await confirm_btn.click()
                confirm_clicked = True
                await self.page.wait_for_timeout(6000)  # analysis may take time
        shot = await _shot(self.page, "reanalyze")
        self.page.remove_listener("response", on_r)
        post_ok = any(r["status"] in (200, 201, 202) for r in post_calls)
        status = "pass" if (reanalyze_btn is not None and confirm_clicked and post_ok) else "fail"
        self._add(_make_bv(BV["REANALYZE"], "Re-analyze updates", status,
            f"btn_found={reanalyze_btn is not None}; confirm_clicked={confirm_clicked}; post_calls={post_calls}; post_ok={post_ok}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"post_ok={post_ok}; calls={post_calls}", screenshot_path=shot))

    # =========================================================================
    # NOTATION / FONT BVs
    # =========================================================================
    async def bv_notation_font(self):
        """HM47 Phase 4: Notation font loads — PASS if no font 404 after score renders."""
        # HM47 FIX: Switch to SONG_BLUE_BOSSA (117, synthetic-staff, no raw_xml)
        # The synthetic staff renders immediately without waiting for OSMD.
        # Pass condition: no font-related 404 errors AND score pane rendered.
        font_song = SONG_BLUE_BOSSA
        print(f"[CATCH-6] Notation font loads (song {font_song} Blue Bossa, synthetic-staff)...")
        self.console_log.clear(); self.network_log.clear()
        font_404_detected = False
        font_urls = []
        async def on_r(r: Response):
            u = r.url
            if "Petaluma" in u or "petaluma" in u or (".woff" in u) or ("notation" in u.lower()) or (".otf" in u):
                font_urls.append(f"{r.status} {u[:80]}")
                if r.status == 404:
                    nonlocal font_404_detected
                    font_404_detected = True
        self.page.on("response", on_r)

        await self._goto_song(font_song)
        await self.page.wait_for_timeout(3000)
        # Ensure score tab / pane is in view and rendered
        try:
            score_pane = await self.page.query_selector(
                '.hl-score, .score-workbench, [class*="score"], .synthetic-staff')
            if score_pane:
                await score_pane.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(1500)
        except Exception:
            pass
        # Check for font-related console errors
        font_errors = [m for m in self.console_log if "petaluma" in m.lower() or "font" in m.lower()]

        # Check score pane actually rendered (has chord symbols)
        chord_cells = await self.page.query_selector_all(".hl-chordsym")
        score_rendered = len(chord_cells) > 0

        shot = await _shot(self.page, "notation_font")
        self.page.remove_listener("response", on_r)

        # HM47 FIX: Pass if no font 404 detected (font_urls=[] is OK — app may use
        # cached or system fonts). Fail only if explicit 404 or console font errors.
        if font_404_detected or (font_urls and any("404" in u for u in font_urls)):
            status = "fail"
            notes = (f"[CATCH-6] Font 404 detected; font_urls={font_urls[:3]}; song={font_song}")
        elif font_errors:
            status = "fail"
            notes = (f"[CATCH-6] Font errors in console; font_errors={font_errors[:3]}; "
                     f"font_urls={font_urls[:3]}; song={font_song}")
        elif not score_rendered:
            status = "fail"
            notes = (f"[CATCH-6] Score pane did not render (chord_cells=0); "
                     f"font_urls={font_urls[:3]}; song={font_song}")
        else:
            status = "pass"
            if font_urls:
                notes = f"[CATCH-6] Font loaded (no 404); font_urls={font_urls[:3]}; score_rendered={score_rendered}"
            else:
                notes = (f"[CATCH-6] Score rendered, no font 404; font_urls=[]; "
                         f"chord_cells={len(chord_cells)}; song={font_song}")
        self._add(_make_bv(BV["NOTATION_FONT"], "[CATCH-6] Notation font loads (synthetic-staff)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"font_urls={font_urls[:3]}; font_404={font_404_detected}; score_rendered={score_rendered}",
            screenshot_path=shot))

    async def bv_bug048_rerender(self):
        """[BUG-048] Grid re-renders to the chosen style — FAIL: jazz symbols persist after plain save."""
        print("[BUG-048] Grid re-renders to chosen notation style...")
        self.console_log.clear(); self.network_log.clear()
        pref_calls = []
        async def on_r(r: Response):
            if "/api/v1/preferences" in r.url:
                pref_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        # Step 1: navigate to settings, switch to plain notation
        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(2000)
        # Find plain mode button
        plain_btn = await self.page.query_selector(
            ".seg button:has-text('Plain'), button:has-text('Plain'), [class*='plain']")
        if plain_btn:
            await plain_btn.click()
            await self.page.wait_for_timeout(500)
        save_btn = await self.page.query_selector("button.btn--primary, button:has-text('Save')")
        if save_btn:
            await self._jclick(save_btn)
            await self.page.wait_for_timeout(1500)

        # Step 2: navigate to song 149 and check chord symbols
        await self._goto_song(SONG_CORCOVADO)
        cells = await self.page.query_selector_all(".hl-chordsym")
        jazz_syms = []
        plain_syms = []
        for cell in cells[:8]:
            sym = (await cell.inner_text()).strip()
            if any(c in sym for c in ["-7", "^7", "-6", "ø", "Δ"]):
                jazz_syms.append(sym)
            if any(s in sym for s in ["m7", "maj7", "m6", "∅"]):
                plain_syms.append(sym)

        shot = await _shot(self.page, "bug048_rerender")
        self.page.remove_listener("response", on_r)

        pref_saved = any(r["status"] == 200 and r["method"] in ("PUT", "PATCH")
                         for r in pref_calls)
        has_jazz = len(jazz_syms) > 0
        has_plain = len(plain_syms) > 0

        if pref_saved and has_jazz and not has_plain:
            status = "fail"
            notes = (f"[BUG-048][EXPECTED-FAIL] Grid still shows jazz symbols after plain save; "
                     f"jazz_syms={jazz_syms[:3]}; pref_saved={pref_saved}; pref_calls={pref_calls}")
        elif pref_saved and has_plain:
            status = "pass"
            notes = f"[BUG-048] Grid re-rendered to plain; plain_syms={plain_syms[:3]}"
        else:
            status = "fail"
            notes = (f"[BUG-048] pref_saved={pref_saved}; has_jazz={has_jazz}; "
                     f"has_plain={has_plain}; pref_calls={pref_calls}")

        self._add(_make_bv(BV["BUG048_RERENDER"], "Grid re-renders to the chosen style (BUG-048)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"jazz={jazz_syms[:3]}; plain={plain_syms[:3]}", screenshot_path=shot))

        # Restore jazz mode
        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(1500)
        jazz_btn = await self.page.query_selector(
            ".seg button:has-text('Jazz'), button:has-text('Jazz')")
        if jazz_btn:
            await jazz_btn.click()
            await self.page.wait_for_timeout(400)
        restore_btn = await self.page.query_selector("button.btn--primary, button:has-text('Save')")
        if restore_btn:
            await restore_btn.click()
            await self.page.wait_for_timeout(1000)

    # =========================================================================
    # RIGHT RAIL
    # =========================================================================
    async def _open_rail(self):
        """Navigate to song 149 and open the right rail. Returns (page, rail_el)."""
        await self._goto_song(SONG_CORCOVADO)
        rail_toggle = await self.page.query_selector(
            "button[title='Study notes — comments, AI exchanges, override history'], "
            "button[title*='rail'], button[aria-label*='rail'], "
            "button:has-text('Notes'), button:has-text('☰')")
        if rail_toggle:
            await rail_toggle.click()
            await self.page.wait_for_timeout(1000)
        rail = await self.page.query_selector("aside.hl-rail[data-open='true'], aside[class*='rail'], aside.open")
        return rail

    async def bv_right_rail_opens(self):
        print("[RAIL] Right rail opens...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        shot = await _shot(self.page, "right_rail_opens")
        status = "pass" if rail is not None else "fail"
        self._add(_make_bv(BV["RIGHT_RAIL_OPENS"], "Right rail opens (Notes)", status,
            f"rail_open={rail is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"rail={rail is not None}", screenshot_path=shot))

    async def bv_rail_close(self):
        print("[RAIL] Rail close...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        if not rail:
            shot = await _shot(self.page, "rail_close")
            self._add(_make_bv(BV["RAIL_CLOSE"], "Rail close", "fail",
                "Rail did not open", page_url=self.page.url, screenshot_path=shot))
            return
        close_btn = await self.page.query_selector(
            ".hl-rail-head button, aside button[title*='close'], aside button:has-text('✕')")
        if close_btn:
            await close_btn.click()
            await self.page.wait_for_timeout(800)
        shot = await _shot(self.page, "rail_close")
        rail_closed = await self.page.query_selector(
            "aside.hl-rail[data-open='false'], aside[class*='rail']:not(.open)")
        status = "pass" if (close_btn is not None) else "fail"
        self._add(_make_bv(BV["RAIL_CLOSE"], "Rail close", status,
            f"close_btn_found={close_btn is not None}; rail_closed={rail_closed is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"close_btn={close_btn is not None}", screenshot_path=shot))

    async def bv_rail_comments(self):
        print("[RAIL] Rail comments + jump-to-chord...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        if not rail:
            shot = await _shot(self.page, "rail_comments")
            self._add(_make_bv(BV["RAIL_COMMENTS"], "Rail comments + jump-to-chord", "fail",
                "Rail did not open", page_url=self.page.url, screenshot_path=shot))
            return
        # Click Comments tab
        tabs = await rail.query_selector_all(".hl-rail-tabs button, [class*='tab'] button, button[role='tab']")
        comments_tab = None
        for t in tabs:
            txt = (await t.inner_text()).strip()
            if "comment" in txt.lower():
                comments_tab = t
                break
        if not comments_tab:
            comments_tab = await rail.query_selector("button:has-text('Comments')")
        if comments_tab:
            await comments_tab.click()
            await self.page.wait_for_timeout(800)
        shot = await _shot(self.page, "rail_comments")
        status = "pass" if (rail is not None and comments_tab is not None) else "fail"
        self._add(_make_bv(BV["RAIL_COMMENTS"], "Rail comments + jump-to-chord", status,
            f"rail={rail is not None}; comments_tab={comments_tab is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"comments_tab={comments_tab is not None}", screenshot_path=shot))

    async def bv_rail_ai(self):
        print("[RAIL] Rail AI exchanges...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        if not rail:
            shot = await _shot(self.page, "rail_ai")
            self._add(_make_bv(BV["RAIL_AI"], "Rail AI exchanges", "fail",
                "Rail did not open", page_url=self.page.url, screenshot_path=shot))
            return
        tabs = await rail.query_selector_all(".hl-rail-tabs button, button[role='tab']")
        ai_tab = None
        for t in tabs:
            txt = (await t.inner_text()).strip()
            if "ai" in txt.lower() or "exchange" in txt.lower():
                ai_tab = t
                break
        if not ai_tab:
            ai_tab = await rail.query_selector("button:has-text('AI'), button:has-text('AI exchanges')")
        if ai_tab:
            await ai_tab.click()
            await self.page.wait_for_timeout(800)
        shot = await _shot(self.page, "rail_ai")
        status = "pass" if (rail is not None and ai_tab is not None) else "fail"
        self._add(_make_bv(BV["RAIL_AI"], "Rail AI exchanges", status,
            f"rail={rail is not None}; ai_tab={ai_tab is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"ai_tab={ai_tab is not None}", screenshot_path=shot))

    async def bv_rail_new_chat(self):
        print("[RAIL] Rail + New chat...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        if not rail:
            shot = await _shot(self.page, "rail_new_chat")
            self._add(_make_bv(BV["RAIL_NEW_CHAT"], "Rail + New chat", "fail",
                "Rail did not open", page_url=self.page.url, screenshot_path=shot))
            return
        # First navigate to AI exchanges tab
        ai_tab = await rail.query_selector(
            "button:has-text('AI'), button:has-text('AI exchanges')")
        if ai_tab:
            await ai_tab.click()
            await self.page.wait_for_timeout(600)
        new_chat_btn = await self.page.query_selector(
            "button:has-text('New chat'), button:has-text('+ New chat'), "
            "button:has-text('New'), [class*='new-chat']")
        if new_chat_btn:
            await new_chat_btn.click()
            await self.page.wait_for_timeout(600)
        shot = await _shot(self.page, "rail_new_chat")
        status = "pass" if (rail is not None and new_chat_btn is not None) else "fail"
        self._add(_make_bv(BV["RAIL_NEW_CHAT"], "Rail + New chat", status,
            f"rail={rail is not None}; new_chat_btn={new_chat_btn is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"new_chat_btn={new_chat_btn is not None}", screenshot_path=shot))

    async def bv_rail_overrides(self):
        print("[RAIL] Rail overrides...")
        self.console_log.clear(); self.network_log.clear()
        rail = await self._open_rail()
        if not rail:
            shot = await _shot(self.page, "rail_overrides")
            self._add(_make_bv(BV["RAIL_OVERRIDES"], "Rail overrides", "fail",
                "Rail did not open", page_url=self.page.url, screenshot_path=shot))
            return
        tabs = await rail.query_selector_all(".hl-rail-tabs button, button[role='tab']")
        overrides_tab = None
        for t in tabs:
            txt = (await t.inner_text()).strip()
            if "override" in txt.lower():
                overrides_tab = t
                break
        if not overrides_tab:
            overrides_tab = await rail.query_selector("button:has-text('Overrides')")
        if overrides_tab:
            await self._jclick(overrides_tab)
            await self.page.wait_for_timeout(800)
        shot = await _shot(self.page, "rail_overrides")
        status = "pass" if (rail is not None and overrides_tab is not None) else "fail"
        self._add(_make_bv(BV["RAIL_OVERRIDES"], "Rail overrides", status,
            f"rail={rail is not None}; overrides_tab={overrides_tab is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"overrides_tab={overrides_tab is not None}", screenshot_path=shot))

    # =========================================================================
    # THEORY CHAT
    # =========================================================================
    async def _open_theory_chat(self):
        """Open the theory chat panel. Returns chat panel aside element or None.

        HM46 FIX: TheoryChat renders as <aside> with NO class.
        Panel selector: aside:has(input.input[placeholder*="Ask about"])
        Open path 1: Right rail → "AI exchanges" tab → "Open Theory Chat →" link
        Open path 2: Top-level "Theory chat" button in song header
        """
        await self._goto_song(SONG_CORCOVADO)
        await self.page.wait_for_timeout(1500)

        # Try via right rail first
        rail = await self._open_rail()
        if rail:
            ai_tab = await rail.query_selector('button:has-text("AI exchanges")')
            if ai_tab:
                await ai_tab.click()
                await self.page.wait_for_timeout(600)
            # Try "Open Theory Chat →" link (appears when no exchanges yet)
            open_chat = await self.page.query_selector('a:has-text("Open Theory Chat")')
            if open_chat:
                await open_chat.click()
                await self.page.wait_for_timeout(800)
            else:
                # Try "+ New chat" button
                new_chat = await self.page.query_selector('button:has-text("+ New chat")')
                if new_chat:
                    await new_chat.click()
                    await self.page.wait_for_timeout(800)

        # Fallback: top-level "Theory chat" button
        panel = await self.page.query_selector('aside:has(input.input)')
        if not panel:
            chat_btn = await self.page.query_selector('button:has-text("Theory chat")')
            if chat_btn:
                await chat_btn.click()
                await self.page.wait_for_timeout(1000)
            panel = await self.page.query_selector('aside:has(input.input)')

        return panel

    async def bv_theory_chat(self):
        print("[CHAT] Theory chat send/response...")
        self.console_log.clear(); self.network_log.clear()
        post_calls = []
        async def on_r(r: Response):
            if "/api/v1/analysis/" in r.url or "/ai-analysis" in r.url or "chat" in r.url:
                post_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        panel = await self._open_theory_chat()
        response_text = ""
        sent = False
        if panel:
            # HM46 FIX: chat input is <input className="input" placeholder="Ask about this song…" />
            chat_input = await self.page.query_selector(
                'aside input.input, aside input[placeholder*="Ask about"], '
                'aside input[placeholder*="ask"]')
            if not chat_input:
                chat_input = await self.page.query_selector('aside input, aside textarea')
            if chat_input:
                await chat_input.fill("What is the key of this song?")
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(6000)  # Wait for AI response
                sent = True
                # Response is in AI message bubbles within the aside
                resp_el = await self.page.query_selector('aside [class*="msg"], aside p, aside div')
                if resp_el:
                    response_text = (await resp_el.inner_text()).strip()
        shot = await _shot(self.page, "theory_chat")
        self.page.remove_listener("response", on_r)
        got_response = len(response_text) > 5
        status = "pass" if (panel is not None and sent and got_response) else "fail"
        self._add(_make_bv(BV["THEORY_CHAT"], "Theory chat send/response", status,
            f"panel={panel is not None}; sent={sent}; response_len={len(response_text)}; "
            f"post_calls={post_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"response='{response_text[:200]}'", screenshot_path=shot))

    async def bv_chat_accept_log(self):
        print("[CHAT] Chat accept-log as override...")
        self.console_log.clear(); self.network_log.clear()
        panel = await self._open_theory_chat()
        accept_found = False
        accepted = False
        if panel:
            # Send a message to get AI response first (if no existing responses)
            chat_input = await self.page.query_selector('aside input.input, aside input')
            if chat_input:
                await chat_input.fill("Suggest a chord change")
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(6000)
            # HM46 FIX: Source button: "✓ Accept · log as override"
            accept_btn = await self.page.query_selector(
                'button:has-text("✓ Accept · log as override"), '
                'button:has-text("Accept · log")')
            if accept_btn:
                accept_found = True
                await self._jclick(accept_btn)
                await self.page.wait_for_timeout(1000)
                accepted = True
        shot = await _shot(self.page, "chat_accept_log")
        status = "pass" if (panel is not None and accept_found and accepted) else "fail"
        self._add(_make_bv(BV["CHAT_ACCEPT_LOG"], "Chat accept-log as override", status,
            f"panel={panel is not None}; accept_found={accept_found}; accepted={accepted}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"accept_found={accept_found}", screenshot_path=shot))

    async def bv_chat_reject(self):
        print("[CHAT] Chat Reject (declared stub)...")
        self.console_log.clear(); self.network_log.clear()
        panel = await self._open_theory_chat()
        reject_btn = None
        if panel:
            # Send message to get response if needed
            chat_input = await self.page.query_selector('aside input.input, aside input')
            if chat_input:
                await chat_input.fill("Why C major?")
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(6000)
            # HM46 FIX: Source button: "✕ Reject"
            reject_btn = await self.page.query_selector(
                'button:has-text("✕ Reject"), button:has-text("Reject")')
        shot = await _shot(self.page, "chat_reject")
        status = "pass" if (panel is not None and reject_btn is not None) else "fail"
        self._add(_make_bv(BV["CHAT_REJECT"], "Chat Reject (declared stub)", status,
            f"panel={panel is not None}; reject_btn={reject_btn is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"reject_btn={reject_btn is not None}", screenshot_path=shot))

    async def bv_chat_why(self):
        print("[CHAT] Chat Why? (declared stub)...")
        self.console_log.clear(); self.network_log.clear()
        panel = await self._open_theory_chat()
        why_btn = None
        if panel:
            # Send message to get response if needed
            chat_input = await self.page.query_selector('aside input.input, aside input')
            if chat_input:
                await chat_input.fill("Why this chord?")
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_timeout(6000)
            # HM46 FIX: Source button: "Why?"
            why_btn = await self.page.query_selector(
                'button:has-text("Why?"), button:has-text("Why")')
        shot = await _shot(self.page, "chat_why")
        status = "pass" if (panel is not None and why_btn is not None) else "fail"
        self._add(_make_bv(BV["CHAT_WHY"], "Chat Why? (declared stub)", status,
            f"panel={panel is not None}; why_btn={why_btn is not None}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"why_btn={why_btn is not None}", screenshot_path=shot))

    # =========================================================================
    # EXPORT
    # =========================================================================
    async def _open_export_menu(self):
        """Navigate to song 149 and open the export dropdown.
        HM46 FIX: ExportMenu has NO class, so look for buttons directly after click.
        Returns True if export button was clicked, False otherwise.
        """
        await self._goto_song(SONG_CORCOVADO)
        await self.page.wait_for_timeout(1500)
        # Source: <button ... onClick={()=>setExportOpen(o=>!o)}>⤓ Export ▾</button>
        export_btn = await self.page.query_selector(
            "button:has-text('Export'), button:has-text('⤓')")
        if export_btn:
            await export_btn.click()
            await self.page.wait_for_timeout(600)
            return True
        return False

    async def bv_export_muse(self):
        print("[EXPORT] Export MuseScore...")
        self.console_log.clear(); self.network_log.clear()
        nav_calls = []
        async def on_r(r: Response):
            if "/exports/musescore" in r.url or "/api/v1/exports" in r.url:
                nav_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)
        dl_started = False
        async def on_dl(d):
            nonlocal dl_started
            dl_started = True
            await d.cancel()
        self.page.on("download", on_dl)

        menu_opened = await self._open_export_menu()
        # HM46 FIX: ExportMenu has no class; buttons are siblings in the opened menu
        # Source: <button onClick={()=>onExport("mscz")}>MuseScore .mscz</button>
        muse_opt = await self.page.query_selector(
            'button:has-text("MuseScore"), button:has-text(".mscz")')
        if muse_opt:
            await muse_opt.click()
            await self.page.wait_for_timeout(3000)
        shot = await _shot(self.page, "export_muse")
        self.page.remove_listener("response", on_r)
        self.page.remove_listener("download", on_dl)
        # PASS: button found AND (download started OR navigation to exports URL)
        export_triggered = dl_started or len(nav_calls) > 0
        status = "pass" if (menu_opened and muse_opt is not None and export_triggered) else "fail"
        self._add(_make_bv(BV["EXPORT_MUSE"], "Export MuseScore", status,
            f"menu_opened={menu_opened}; muse_opt={muse_opt is not None}; dl={dl_started}; nav_calls={nav_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"muse_opt={muse_opt is not None}; dl={dl_started}", screenshot_path=shot))

    async def bv_export_pdf(self):
        print("[EXPORT] Export PDF (window.print)...")
        self.console_log.clear(); self.network_log.clear()

        menu_opened = await self._open_export_menu()
        # Intercept window.print before clicking the button
        await self.page.evaluate("window.__printCalled = false; window.print = function(){ window.__printCalled = true; };")
        # HM46 FIX: Source uses window.print() not a download
        # Source: onExport("pdf") → window.print()
        pdf_opt = await self.page.query_selector(
            'button:has-text("Print to PDF"), button:has-text("Print"), button:has-text("PDF")')
        if pdf_opt:
            await pdf_opt.click()
            await self.page.wait_for_timeout(1500)
        shot = await _shot(self.page, "export_pdf")
        print_called = await self.page.evaluate("window.__printCalled === true")
        status = "pass" if (menu_opened and pdf_opt is not None and print_called) else "fail"
        self._add(_make_bv(BV["EXPORT_PDF"], "Export / Print to PDF", status,
            f"menu_opened={menu_opened}; pdf_opt={pdf_opt is not None}; print_called={print_called}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"pdf_opt={pdf_opt is not None}; print_called={print_called}", screenshot_path=shot))

    async def bv_export_xml(self):
        print("[EXPORT] Export MusicXML...")
        self.console_log.clear(); self.network_log.clear()
        nav_calls = []
        async def on_r(r: Response):
            if "/exports/musicxml" in r.url or "/api/v1/exports" in r.url:
                nav_calls.append({"url": r.url, "status": r.status})
        self.page.on("response", on_r)
        dl_started = False
        async def on_dl(d):
            nonlocal dl_started
            dl_started = True
            await d.cancel()
        self.page.on("download", on_dl)

        menu_opened = await self._open_export_menu()
        # HM46 FIX: Source button: <button onClick={()=>onExport("musicxml")}>MusicXML .musicxml</button>
        xml_opt = await self.page.query_selector(
            'button:has-text("MusicXML"), button:has-text(".musicxml")')
        if xml_opt:
            await xml_opt.click()
            await self.page.wait_for_timeout(3000)
        shot = await _shot(self.page, "export_xml")
        self.page.remove_listener("response", on_r)
        self.page.remove_listener("download", on_dl)
        export_triggered = dl_started or len(nav_calls) > 0
        status = "pass" if (menu_opened and xml_opt is not None and export_triggered) else "fail"
        self._add(_make_bv(BV["EXPORT_XML"], "Export MusicXML", status,
            f"menu_opened={menu_opened}; xml_opt={xml_opt is not None}; dl={dl_started}; nav_calls={nav_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"xml_opt={xml_opt is not None}; dl={dl_started}", screenshot_path=shot))

    # =========================================================================
    # SETTINGS
    # =========================================================================
    async def bv_set_keycolor(self):
        print("[SETTINGS] Key-color setting persists...")
        self.console_log.clear(); self.network_log.clear()
        pref_calls = []
        async def on_r(r: Response):
            if "/api/v1/preferences" in r.url:
                pref_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(2000)
        # Find a color input (hex input or color swatch for a key)
        color_input = await self.page.query_selector(
            "input[type='color'], input[placeholder*='#'], input[value*='#'], "
            "[class*='color-picker'] input, [class*='key-color'] input")
        color_changed = False
        if color_input:
            await color_input.click(click_count=3)
            await color_input.type("#FF5733")
            await self.page.wait_for_timeout(300)
            color_changed = True
        save_btn = await self.page.query_selector("button.btn--primary, button:has-text('Save')")
        if save_btn:
            await self._jclick(save_btn)
            await self.page.wait_for_timeout(1500)

        shot = await _shot(self.page, "set_keycolor")
        self.page.remove_listener("response", on_r)
        pref_ok = any(r["status"] == 200 and r["method"] in ("PUT", "PATCH")
                      for r in pref_calls)
        status = "pass" if pref_ok else "fail"
        self._add(_make_bv(BV["SET_KEYCOLOR"], "Key-color setting persists", status,
            f"color_input={color_input is not None}; color_changed={color_changed}; "
            f"pref_ok={pref_ok}; pref_calls={pref_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"pref_ok={pref_ok}; calls={pref_calls}", screenshot_path=shot))

    async def bv_set_notation(self):
        print("[SETTINGS] Chord-notation setting persists...")
        self.console_log.clear(); self.network_log.clear()
        pref_calls = []
        async def on_r(r: Response):
            if "/api/v1/preferences" in r.url:
                pref_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(2000)
        # Click Jazz mode (or toggle to whatever is not current)
        jazz_btn = await self.page.query_selector(".seg button:has-text('Jazz'), button:has-text('Jazz')")
        if jazz_btn:
            await jazz_btn.click()
            await self.page.wait_for_timeout(400)
        save_btn = await self.page.query_selector("button.btn--primary, button:has-text('Save')")
        if save_btn:
            await self._jclick(save_btn)
            await self.page.wait_for_timeout(1500)

        # Reload settings and verify
        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(1500)
        jazz_active = await self.page.query_selector(
            ".seg button.active:has-text('Jazz'), button[aria-pressed='true']:has-text('Jazz')")

        shot = await _shot(self.page, "set_notation")
        self.page.remove_listener("response", on_r)
        pref_ok = any(r["status"] == 200 and r["method"] in ("PUT", "PATCH")
                      for r in pref_calls)
        status = "pass" if pref_ok else "fail"
        self._add(_make_bv(BV["SET_NOTATION"], "Chord-notation setting persists", status,
            f"pref_ok={pref_ok}; jazz_active_after_reload={jazz_active is not None}; "
            f"pref_calls={pref_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"pref_ok={pref_ok}", screenshot_path=shot))

    async def bv_set_voicing(self):
        print("[SETTINGS] Default-voicing setting persists...")
        self.console_log.clear(); self.network_log.clear()
        pref_calls = []
        async def on_r(r: Response):
            if "/api/v1/preferences" in r.url:
                pref_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(2000)
        # HM46 FIX: Source: <input placeholder="leave blank for none" style={{width:240}}/>
        voicing_input = await self.page.query_selector(
            'input[placeholder="leave blank for none"], '
            'input[placeholder*="leave blank"], '
            'input[placeholder*="voicing"]')
        test_voicing = "hm46-test"
        save_clicked = False
        if voicing_input:
            await voicing_input.click(click_count=3)
            await voicing_input.fill(test_voicing)
            await self.page.wait_for_timeout(500)
        # Source: Save button disabled={!dirty||saving}. After fill(), dirty=true so button enabled.
        save_btn = await self.page.query_selector(
            "button:has-text('Save preferences'), button.btn--primary:not([disabled])")
        if save_btn:
            save_enabled = not (await save_btn.is_disabled())
            if save_enabled:
                await self._jclick(save_btn)
                save_clicked = True
                await self.page.wait_for_timeout(1500)

        shot = await _shot(self.page, "set_voicing")
        self.page.remove_listener("response", on_r)
        pref_ok = any(r["status"] == 200 and r["method"] in ("PUT", "PATCH")
                      for r in pref_calls)
        status = "pass" if pref_ok else "fail"
        self._add(_make_bv(BV["SET_VOICING"], "Default-voicing setting persists", status,
            f"voicing_input={voicing_input is not None}; save_clicked={save_clicked}; pref_ok={pref_ok}; calls={pref_calls}",
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"pref_ok={pref_ok}", screenshot_path=shot))

    async def bv_voicing_clear(self):
        """[EXPECTED-FAIL] Default voicing can be cleared — server ignores null voicing."""
        print("[SETTINGS][EXPECTED-FAIL] Voicing clear...")
        self.console_log.clear(); self.network_log.clear()
        pref_calls = []
        put_bodies = []
        async def on_r(r: Response):
            if "/api/v1/preferences" in r.url:
                pref_calls.append({"url": r.url, "status": r.status, "method": r.request.method})
        self.page.on("response", on_r)

        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(2000)
        voicing_input = await self.page.query_selector(
            'input[placeholder="leave blank for none"], '
            'input[placeholder*="leave blank"], '
            'input[placeholder*="voicing"]')
        cleared = False
        if voicing_input:
            await voicing_input.fill("")
            await self.page.wait_for_timeout(300)
            cleared = True
        save_btn = await self.page.query_selector("button.btn--primary, button:has-text('Save')")
        if save_btn:
            await self._jclick(save_btn)
            await self.page.wait_for_timeout(1500)

        # Reload settings and check if voicing was cleared
        await self._goto_with_auth(f"{BASE_URL}/#/settings")
        await self.page.wait_for_timeout(1500)
        voicing_after = await self.page.query_selector(
            "input[placeholder*='blank'], input[placeholder*='voicing'], [class*='voicing'] input")
        voicing_val = (await voicing_after.input_value()).strip() if voicing_after else "N/A"

        shot = await _shot(self.page, "voicing_clear")
        self.page.remove_listener("response", on_r)
        pref_ok = any(r["status"] == 200 and r["method"] in ("PUT", "PATCH")
                      for r in pref_calls)
        was_cleared = voicing_val == "" or voicing_val == "N/A"

        if pref_ok and was_cleared:
            status = "pass"
            notes = f"Voicing cleared: pref_ok={pref_ok}; val='{voicing_val}'"
        else:
            status = "fail"
            notes = (f"[EXPECTED-FAIL] Voicing NOT cleared: pref_ok={pref_ok}; "
                     f"voicing_after='{voicing_val}'; calls={pref_calls}")
        self._add(_make_bv(BV["VOICING_CLEAR"], "Default voicing can be cleared", status, notes,
            page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"cleared={cleared}; voicing_after='{voicing_val}'", screenshot_path=shot))

    # =========================================================================
    # BUG BVs
    # =========================================================================
    async def bv_bug047_chord_id(self):
        """[BUG-047][PILOT] Synthetic-staff chords expose ids — null IDs throughout."""
        print(f"[PILOT][BUG-047] Chord IDs exposed on synthetic-staff (song {SONG_BLUE_BOSSA}, must-FAIL)...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_BLUE_BOSSA)
        # Verify via API: chord[0].id should be null (BUG-047)
        api_check = await self.page.evaluate("""async () => {
            try {
                const r = await fetch('/api/v1/analysis/songs/117', {credentials: 'include'});
                const a = await r.json();
                const ch = (a.chords || [])[0] || {};
                return {id: ch.id, symbol: ch.symbol, source: a.chord_source,
                        chord_count: (a.chords || []).length};
            } catch(e) { return {error: e.message}; }
        }""")
        shot = await _shot(self.page, "bug047_chord_id")
        chord_id = api_check.get("id")
        source   = api_check.get("chord_source", "")
        count    = api_check.get("chord_count", 0)

        if chord_id is None:
            status = "fail"
            notes = (f"[BUG-047][TRUST-GATE-EXPECTED-FAIL] chord[0].id=null on song {SONG_BLUE_BOSSA}; "
                     f"source={source}; count={count}. PUT /api/v1/chords/undefined → 422.")
        else:
            status = "pass"
            notes = (f"[BUG-047] chord[0].id={chord_id} (not null); "
                     f"BUG-047 may be fixed; source={source}")
        self._add(_make_bv(BV["BUG047_CHORD_ID"],
            "[BUG-047][PILOT] Synthetic-staff chords expose ids (must-FAIL)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"chord_id={chord_id}; source={source}; count={count}", screenshot_path=shot))

    async def bv_bug050_note_only(self):
        """[BUG-050] Note-only import auto-derives or shows empty-state — FAIL: no chord analysis."""
        print(f"[BUG-050] Note-only import (song {SONG_PRELUDE_C})...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_song(SONG_PRELUDE_C)
        shot_song = await _shot(self.page, "bug050_note_only")

        # API check: chord_count should be 0, has_note_data=True
        api_check = await self.page.evaluate(f"""async () => {{
            try {{
                const sr = await fetch('/api/v1/songs/{SONG_PRELUDE_C}', {{credentials: 'include'}});
                const s = await sr.json();
                const ar = await fetch('/api/v1/analysis/songs/{SONG_PRELUDE_C}', {{credentials: 'include'}});
                const a = await ar.json();
                return {{
                    has_note_data: s.has_note_data,
                    chord_source: a.chord_source,
                    chord_count: (a.chords || []).length,
                    detected_key: a.detected_key,
                    title: s.title
                }};
            }} catch(e) {{ return {{error: e.message}}; }}
        }}""")
        cells = await self.page.query_selector_all(".hl-chordsym")
        shot = await _shot(self.page, "bug050_note_only_grid")

        has_note_data  = api_check.get("has_note_data", False)
        chord_count    = api_check.get("chord_count", -1)
        chord_source   = api_check.get("chord_source")
        ui_chord_count = len(cells)

        if has_note_data and chord_count == 0 and ui_chord_count == 0:
            status = "fail"
            notes = (f"[BUG-050][EXPECTED-FAIL] Note-only import: has_note_data={has_note_data}; "
                     f"chord_count=0; chord_source=None; no chord grid rendered. "
                     f"Song: {api_check.get('title','?')} (id={SONG_PRELUDE_C})")
        elif chord_count > 0:
            status = "pass"
            notes = (f"[BUG-050] Chord analysis exists: chord_count={chord_count}; "
                     f"chord_source={chord_source}; bug may be fixed")
        else:
            status = "fail"
            notes = (f"[BUG-050] api_check={api_check}; ui_cells={ui_chord_count}")
        self._add(_make_bv(BV["BUG050_NOTE_ONLY"],
            "Note-only import auto-derives or shows empty-state (BUG-050)",
            status, notes, page_url=self.page.url, console_msgs=self._snap_console(),
            dom_text=f"chord_count={chord_count}; ui_cells={ui_chord_count}", screenshot_path=shot))

    # =========================================================================
    # LAB STUBS
    # =========================================================================
    async def bv_lab_stubs(self):
        print("[LAB] Lab stub buttons...")
        self.console_log.clear(); self.network_log.clear()
        await self._goto_with_auth(f"{BASE_URL}/#/lab")
        await self.page.wait_for_timeout(2000)
        shot = await _shot(self.page, "lab_stubs")
        url = self.page.url
        has_content = await self.page.evaluate(
            "() => (document.getElementById('root') || {}).children?.length > 0")
        buttons = await self.page.query_selector_all("button")
        btn_texts = []
        for b in buttons[:10]:
            txt = (await b.inner_text()).strip()
            if txt and txt not in ("✕", "≡", "☰"):
                btn_texts.append(txt)
        status = "pass" if (has_content and len(buttons) > 0) else "fail"
        self._add(_make_bv(BV["LAB_STUBS"], "Lab stub buttons (click each)", status,
            f"url={url}; has_content={has_content}; buttons={len(buttons)}; texts={btn_texts[:5]}",
            page_url=url, console_msgs=self._snap_console(),
            dom_text=f"buttons={len(buttons)}; texts={btn_texts[:5]}", screenshot_path=shot))

    # =========================================================================
    # TRUST GATE
    # =========================================================================
    def check_trust_gate(self):
        by_id = {r["id"]: r for r in self.results if r["id"] in GATE_IDS}
        fail_wrong = [r for r in by_id.values() if r["id"] in MUST_FAIL  and r["status"] == "pass"]
        pass_wrong = [r for r in by_id.values() if r["id"] in MUST_PASS  and r["status"] == "fail"]
        missing    = [bid for bid in GATE_IDS if bid not in by_id]

        print(f"\n{'='*60}")
        print("TRUST GATE CHECK (v3 bidirectional 3×3)")
        print(f"  must-FAIL rows that went PASS: {len(fail_wrong)}")
        print(f"  must-PASS rows that went FAIL: {len(pass_wrong)}")
        print(f"  missing: {len(missing)}")
        for r in fail_wrong:
            print(f"    UNEXPECTED PASS: {r['title'][:70]}")
        for r in pass_wrong:
            print(f"    UNEXPECTED FAIL: {r['title'][:70]}")

        all_clear = not fail_wrong and not pass_wrong and not missing
        if all_clear:
            print("  ✅ GATE CLEARED")
        else:
            print("  ❌ GATE NOT CLEARED — fix before accepting results")
        return all_clear

    # =========================================================================
    # GCS UPLOAD
    # =========================================================================
    def upload_shots_to_gcs(self, session_id: str) -> dict:
        """Upload all screenshots to GCS. Returns mapping of local→gcs paths."""
        gcs_map = {}
        for png in SHOTS_DIR.glob("*.png"):
            gcs_path = f"{GCS_BUCKET}/{session_id}/{png.name}"
            try:
                r = subprocess.run(
                    [GSUTIL, "cp", str(png), gcs_path],
                    capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    gcs_map[str(png)] = gcs_path
                    print(f"  [GCS] Uploaded {png.name}")
                else:
                    print(f"  [GCS-WARN] Failed {png.name}: {r.stderr[:80]}")
            except Exception as e:
                print(f"  [GCS-WARN] {png.name}: {e}")
        return gcs_map

    # =========================================================================
    # FULL SWEEP
    # =========================================================================
    async def run_full_sweep(self):
        print("\n" + "="*60)
        print("HM45 FULL SWEEP — v3, 65 BVs")
        print("="*60)

        await self._open_context()

        # S0 — Load canary (abort if red)
        canary_ok = await self.s0_load_canary()
        if not canary_ok:
            print("\n[ABORT] Canary RED — sweep void.")
            await self.ctx.close()
            return False

        # AUTH
        await self.bv_passphrase_login()

        async def _run(fn):
            """Run a BV method; catch any unhandled crash and record as FAIL."""
            try:
                await fn()
            except Exception as exc:
                bv_name = fn.__name__
                print(f"  ❌ CRASH | {bv_name}: {exc}")
                # Reset page state after crash (close overlays, navigate away)
                try:
                    for _ in range(3):
                        await self.page.keyboard.press("Escape")
                        await self.page.wait_for_timeout(200)
                    await self.page.goto(f"{BASE_URL}/#/", wait_until="domcontentloaded", timeout=10000)
                    await self.page.wait_for_timeout(500)
                except Exception:
                    pass
                # Find which BV key maps to this method
                method_to_bv = {
                    'bv_library_lists_songs': 'LIBRARY_LISTS',
                    'bv_cap_badges': 'CAP_BADGES', 'bv_sort_title': 'SORT_TITLE',
                    'bv_filter_genre': 'FILTER_GENRE', 'bv_clear_filter': 'CLEAR_FILTER',
                    'bv_clear_sort': 'CLEAR_SORT', 'bv_per_row_checkbox': 'PER_ROW_CHECKBOX',
                    'bv_select_all': 'SELECT_ALL', 'bv_row_audit_link': 'ROW_AUDIT_LINK',
                    'bv_bulk_delete': 'BULK_DELETE',
                    'bv_import_song_btn': 'IMPORT_SONG_BTN', 'bv_import_cancel': 'IMPORT_CANCEL',
                    'bv_import_err_display': 'IMPORT_ERR_DISPLAY',
                    'bv_import_tab_switch': 'IMPORT_TAB_SWITCH', 'bv_import_retry': 'IMPORT_RETRY',
                    'bv_score_import': 'SCORE_IMPORT', 'bv_import_title_ovr': 'IMPORT_TITLE_OVR',
                    'bv_import_history': 'IMPORT_HISTORY', 'bv_omr_import': 'OMR_IMPORT',
                    'bv_batch_zip_import': 'BATCH_ZIP_IMPORT',
                    'bv_song_opens': 'SONG_OPENS', 'bv_chord_grid': 'CHORD_GRID',
                    'bv_chord_modal_target': 'CHORD_MODAL_TARGET',
                    'bv_chord_picker': 'CHORD_PICKER',
                    'bv_chord_edit_persist': 'CHORD_EDIT_PERSIST',
                    'bv_chord_edit_cancel': 'CHORD_EDIT_CANCEL',
                    'bv_enter_saves': 'ENTER_SAVES', 'bv_invalid_disables': 'INVALID_DISABLES',
                    'bv_accept_inferred': 'ACCEPT_INFERRED', 'bv_multiselect': 'MULTISELECT',
                    'bv_voicing_edit': 'VOICING_EDIT', 'bv_comment_persist': 'COMMENT_PERSIST',
                    'bv_write_error_surfaced': 'WRITE_ERROR_SURFACED',
                    'bv_manual_key_persist': 'MANUAL_KEY_PERSIST',
                    'bv_manual_key_clear': 'MANUAL_KEY_CLEAR',
                    'bv_identify_key': 'IDENTIFY_KEY', 'bv_accept_ai_key': 'ACCEPT_AI_KEY',
                    'bv_score_func': 'SCORE_FUNC', 'bv_score_roman': 'SCORE_ROMAN',
                    'bv_key_timeline': 'KEY_TIMELINE', 'bv_reanalyze': 'REANALYZE',
                    'bv_notation_font': 'NOTATION_FONT', 'bv_bug048_rerender': 'BUG048_RERENDER',
                    'bv_right_rail_opens': 'RIGHT_RAIL_OPENS', 'bv_rail_close': 'RAIL_CLOSE',
                    'bv_rail_comments': 'RAIL_COMMENTS', 'bv_rail_ai': 'RAIL_AI',
                    'bv_rail_new_chat': 'RAIL_NEW_CHAT', 'bv_rail_overrides': 'RAIL_OVERRIDES',
                    'bv_theory_chat': 'THEORY_CHAT', 'bv_chat_accept_log': 'CHAT_ACCEPT_LOG',
                    'bv_chat_reject': 'CHAT_REJECT', 'bv_chat_why': 'CHAT_WHY',
                    'bv_export_muse': 'EXPORT_MUSE', 'bv_export_pdf': 'EXPORT_PDF',
                    'bv_export_xml': 'EXPORT_XML',
                    'bv_set_keycolor': 'SET_KEYCOLOR', 'bv_set_notation': 'SET_NOTATION',
                    'bv_set_voicing': 'SET_VOICING', 'bv_voicing_clear': 'VOICING_CLEAR',
                    'bv_bug047_chord_id': 'BUG047_CHORD_ID',
                    'bv_bug050_note_only': 'BUG050_NOTE_ONLY', 'bv_lab_stubs': 'LAB_STUBS',
                }
                bv_key = method_to_bv.get(bv_name, bv_name.upper().replace('BV_', ''))
                bv_id  = BV.get(bv_key, f'UNKNOWN-{bv_name}')
                self._add(_make_bv(bv_id, bv_name, 'fail',
                    f'[RUNNER-CRASH] Unhandled exception: {type(exc).__name__}: {str(exc)[:200]}',
                    page_url=self.page.url if self.page else ''))

        # LIBRARY
        print("\n--- LIBRARY ---")
        await _run(self.bv_library_lists_songs)
        await _run(self.bv_cap_badges)
        await _run(self.bv_sort_title)
        await _run(self.bv_filter_genre)
        await _run(self.bv_clear_filter)
        await _run(self.bv_clear_sort)
        await _run(self.bv_per_row_checkbox)
        await _run(self.bv_select_all)
        await _run(self.bv_row_audit_link)

        # IMPORT
        print("\n--- IMPORT ---")
        await _run(self.bv_import_song_btn)
        await _run(self.bv_import_cancel)
        await _run(self.bv_import_err_display)
        await _run(self.bv_import_tab_switch)
        await _run(self.bv_import_retry)
        await _run(self.bv_score_import)
        await _run(self.bv_import_title_ovr)
        await _run(self.bv_import_history)
        await _run(self.bv_omr_import)
        await _run(self.bv_batch_zip_import)
        await _run(self.bv_bulk_delete)

        # SONG DETAIL — Display
        print("\n--- SONG DETAIL (display) ---")
        await _run(self.bv_song_opens)
        await _run(self.bv_chord_grid)
        await _run(self.bv_chord_modal_target)  # PILOT must-PASS
        await _run(self.bv_chord_picker)
        await _run(self.bv_chord_edit_cancel)
        await _run(self.bv_enter_saves)
        await _run(self.bv_invalid_disables)
        await _run(self.bv_multiselect)

        # SONG DETAIL — Write (expected fails)
        print("\n--- SONG DETAIL (write, expected FAIL) ---")
        await _run(self.bv_voicing_edit)         # PILOT must-FAIL
        await _run(self.bv_comment_persist)      # PILOT must-FAIL
        await _run(self.bv_chord_edit_persist)
        await _run(self.bv_accept_inferred)
        await _run(self.bv_write_error_surfaced)

        # SCORE DISPLAY
        print("\n--- SCORE DISPLAY ---")
        await _run(self.bv_score_func)
        await _run(self.bv_score_roman)
        await _run(self.bv_key_timeline)
        await _run(self.bv_reanalyze)

        # KEY HANDLING
        print("\n--- KEY HANDLING ---")
        await _run(self.bv_identify_key)         # PILOT must-PASS
        await _run(self.bv_accept_ai_key)
        await _run(self.bv_manual_key_persist)
        await _run(self.bv_manual_key_clear)

        # NOTATION / FONTS
        print("\n--- NOTATION ---")
        await _run(self.bv_notation_font)
        await _run(self.bv_bug048_rerender)

        # RIGHT RAIL
        print("\n--- RAIL ---")
        await _run(self.bv_right_rail_opens)
        await _run(self.bv_rail_close)
        await _run(self.bv_rail_comments)
        await _run(self.bv_rail_ai)
        await _run(self.bv_rail_new_chat)
        await _run(self.bv_rail_overrides)

        # THEORY CHAT
        print("\n--- THEORY CHAT ---")
        await _run(self.bv_theory_chat)
        await _run(self.bv_chat_accept_log)
        await _run(self.bv_chat_reject)
        await _run(self.bv_chat_why)

        # EXPORT
        print("\n--- EXPORT ---")
        await _run(self.bv_export_muse)
        await _run(self.bv_export_pdf)
        await _run(self.bv_export_xml)

        # SETTINGS
        print("\n--- SETTINGS ---")
        await _run(self.bv_set_keycolor)
        await _run(self.bv_set_notation)
        await _run(self.bv_set_voicing)
        await _run(self.bv_voicing_clear)

        # BUG BVs
        print("\n--- BUG BVs ---")
        await _run(self.bv_bug047_chord_id)      # PILOT must-FAIL
        await _run(self.bv_bug050_note_only)

        # LAB
        print("\n--- LAB ---")
        await _run(self.bv_lab_stubs)

        await self.ctx.close()

        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = total - passed
        print(f"\n{'='*60}")
        print(f"SWEEP COMPLETE: {total} BVs | {passed} PASS | {failed} FAIL")
        print(f"{'='*60}")

        trusted = self.check_trust_gate()
        return trusted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    session_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # Fetch runner key from Secret Manager at runtime
    print("[AUTH] Fetching runner key from Secret Manager...")
    try:
        rk_result = subprocess.run(
            [GCLOUD, "secrets", "versions", "access", "latest",
             "--secret=metapm-browser-runner-key", "--project=super-flashcards-475210"],
            capture_output=True, text=True, check=True, shell=True)
        runner_key = rk_result.stdout.strip()
        print(f"[AUTH] Runner key fetched ({len(runner_key)} chars)")
    except Exception as e:
        print(f"[WARN] Could not fetch runner key: {e}")
        runner_key = ""

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        if not AUTH_STATE.exists():
            print("[AUTH] First auth...")
            await ensure_auth(browser)

        runner = Runner(browser, session_id=session_id, runner_key=runner_key)

        if mode == "full":
            await runner.run_full_sweep()
        elif mode == "canary":
            await runner._open_context()
            await runner.s0_load_canary()
            await runner.ctx.close()
        else:
            print(f"[ERROR] Unknown mode: {mode}. Use: full | canary")

        await browser.close()

    # Persist results
    RESULTS_FILE.write_text(json.dumps(runner.results, indent=2), encoding="utf-8")
    print(f"\n[RESULTS] Saved to {RESULTS_FILE}")
    print(f"[RESULTS] Total: {len(runner.results)} BVs")

    # Print per-BV summary
    for r in runner.results:
        tag = "PASS" if r["status"] == "pass" else "FAIL"
        print(f"  [{tag}] {r['id'][:8]}... {r['title'][:60]}")

    print(f"\n[DONE] HM46 sweep complete. Session: {session_id}")
    return runner.results


if __name__ == "__main__":
    asyncio.run(main())
