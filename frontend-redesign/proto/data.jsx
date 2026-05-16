/* =====================================================================
   HarmonyLab interactive prototype — mock data + helpers
   ===================================================================== */

const KEY_COLOR_DEFAULTS = {
  "C maj":  "oklch(0.86 0.06 85)",
  "G maj":  "oklch(0.72 0.10 145)",
  "D maj":  "oklch(0.70 0.12 165)",
  "A maj":  "oklch(0.70 0.11 200)",
  "E maj":  "oklch(0.68 0.12 245)",
  "B maj":  "oklch(0.66 0.13 285)",
  "F# maj": "oklch(0.66 0.16 315)",
  "F maj":  "oklch(0.78 0.13 60)",
  "Bb maj": "oklch(0.80 0.14 80)",
  "Eb maj": "oklch(0.74 0.13 45)",
  "Ab maj": "oklch(0.66 0.13 25)",
  "Db maj": "oklch(0.62 0.15 5)",
  // minors inherit hue at lower lightness
  "A min":  "oklch(0.62 0.06 85)",
  "E min":  "oklch(0.55 0.10 145)",
  "B min":  "oklch(0.55 0.12 165)",
  "F# min": "oklch(0.55 0.11 200)",
  "C# min": "oklch(0.55 0.12 245)",
  "G# min": "oklch(0.55 0.13 285)",
  "D# min": "oklch(0.55 0.16 315)",
  "D min":  "oklch(0.60 0.13 60)",
  "G min":  "oklch(0.60 0.14 80)",
  "C min":  "oklch(0.55 0.13 45)",
  "F min":  "oklch(0.55 0.13 25)",
  "Bb min": "oklch(0.55 0.15 5)",
};

/* helper: chord id generator */
let __cid = 1000;
const cid = () => ++__cid;

/* helper: build a measure with chord array */
const M = (number, chords) => ({ number, chords });

/* helper: chord factory */
const C = (overrides = {}) => ({
  id: cid(),
  symbol: "C",
  roman: "I",
  romanCase: "major",   // "major"|"minor"
  function: "tonic",
  keyCenter: "C maj",
  voicing: "",
  comment: "",
  isInferred: false,
  isManualEdit: false,
  hasOverride: false,
  confidence: 0.92,
  beat: 1.0,
  ...overrides,
});

/* =====================================================================
   Chord vocabulary — mirrors /api/v1/vocabulary/chord-symbols (30 rows)
   Each row: { suffix, displayJazz, displayPlain, type, intervals, aliases }
   ===================================================================== */
const CHORD_QUALITIES = [
  { suffix: "",       displayJazz: "",        displayPlain: "",        type: "major",       intervals: "1-3-5",         aliases: ["maj"] },
  { suffix: "m",      displayJazz: "m",       displayPlain: "m",       type: "minor",       intervals: "1-♭3-5",        aliases: ["min","-"] },
  { suffix: "7",      displayJazz: "7",       displayPlain: "7",       type: "dominant 7",  intervals: "1-3-5-♭7",      aliases: ["dom7"] },
  { suffix: "△7",     displayJazz: "△7",      displayPlain: "maj7",    type: "major 7",     intervals: "1-3-5-7",       aliases: ["maj7","M7","Δ7"] },
  { suffix: "m7",     displayJazz: "m7",      displayPlain: "m7",      type: "minor 7",     intervals: "1-♭3-5-♭7",     aliases: ["min7","-7"] },
  { suffix: "m△7",    displayJazz: "m△7",     displayPlain: "mMaj7",   type: "minor-major", intervals: "1-♭3-5-7",      aliases: ["mMaj7","mM7","-Δ7"] },
  { suffix: "ø7",     displayJazz: "ø7",      displayPlain: "m7♭5",    type: "half-dim",    intervals: "1-♭3-♭5-♭7",    aliases: ["m7b5","ø","-7♭5"] },
  { suffix: "°7",     displayJazz: "°7",      displayPlain: "dim7",    type: "diminished 7",intervals: "1-♭3-♭5-♭♭7",   aliases: ["dim7","o7"] },
  { suffix: "°",      displayJazz: "°",       displayPlain: "dim",     type: "diminished",  intervals: "1-♭3-♭5",       aliases: ["dim","o"] },
  { suffix: "+",      displayJazz: "+",       displayPlain: "aug",     type: "augmented",   intervals: "1-3-♯5",        aliases: ["aug","+5","♯5"] },
  { suffix: "+7",     displayJazz: "+7",      displayPlain: "aug7",    type: "augmented 7", intervals: "1-3-♯5-♭7",     aliases: ["7♯5","aug7"] },
  { suffix: "7♭5",    displayJazz: "7♭5",     displayPlain: "7b5",     type: "dominant ♭5", intervals: "1-3-♭5-♭7",     aliases: ["7b5"] },
  { suffix: "7♭9",    displayJazz: "7♭9",     displayPlain: "7b9",     type: "dom 7♭9",     intervals: "1-3-5-♭7-♭9",   aliases: ["7b9"] },
  { suffix: "7♯9",    displayJazz: "7♯9",     displayPlain: "7#9",     type: "dom 7♯9",     intervals: "1-3-5-♭7-♯9",   aliases: ["7#9"] },
  { suffix: "7♯11",   displayJazz: "7♯11",    displayPlain: "7#11",    type: "dom 7♯11",    intervals: "1-3-5-♭7-♯11",  aliases: ["7#11"] },
  { suffix: "7♭13",   displayJazz: "7♭13",    displayPlain: "7b13",    type: "dom 7♭13",    intervals: "1-3-5-♭7-♭13",  aliases: ["7b13"] },
  { suffix: "7alt",   displayJazz: "7alt",    displayPlain: "7alt",    type: "altered dom", intervals: "1-3-♭5/♯5-♭7-♭9/♯9", aliases: ["alt"] },
  { suffix: "9",      displayJazz: "9",       displayPlain: "9",       type: "dom 9",       intervals: "1-3-5-♭7-9",    aliases: [] },
  { suffix: "△9",     displayJazz: "△9",      displayPlain: "maj9",    type: "major 9",     intervals: "1-3-5-7-9",     aliases: ["maj9","M9"] },
  { suffix: "m9",     displayJazz: "m9",      displayPlain: "m9",      type: "minor 9",     intervals: "1-♭3-5-♭7-9",   aliases: ["-9"] },
  { suffix: "11",     displayJazz: "11",      displayPlain: "11",      type: "dom 11",      intervals: "1-3-5-♭7-9-11", aliases: [] },
  { suffix: "13",     displayJazz: "13",      displayPlain: "13",      type: "dom 13",      intervals: "1-3-5-♭7-9-11-13", aliases: [] },
  { suffix: "△13",    displayJazz: "△13",     displayPlain: "maj13",   type: "major 13",    intervals: "1-3-5-7-9-11-13", aliases: ["maj13"] },
  { suffix: "6",      displayJazz: "6",       displayPlain: "6",       type: "major 6",     intervals: "1-3-5-6",       aliases: [] },
  { suffix: "m6",     displayJazz: "m6",      displayPlain: "m6",      type: "minor 6",     intervals: "1-♭3-5-6",      aliases: [] },
  { suffix: "6/9",    displayJazz: "6/9",     displayPlain: "6/9",     type: "6/9",         intervals: "1-3-5-6-9",     aliases: [] },
  { suffix: "sus2",   displayJazz: "sus2",    displayPlain: "sus2",    type: "sus 2",       intervals: "1-2-5",         aliases: [] },
  { suffix: "sus4",   displayJazz: "sus4",    displayPlain: "sus4",    type: "sus 4",       intervals: "1-4-5",         aliases: ["sus"] },
  { suffix: "7sus4",  displayJazz: "7sus4",   displayPlain: "7sus4",   type: "dom 7sus4",   intervals: "1-4-5-♭7",      aliases: ["7sus"] },
  { suffix: "add9",   displayJazz: "add9",    displayPlain: "add9",    type: "add 9",       intervals: "1-3-5-9",       aliases: [] },
];

const ROOT_NOTES = ["C","C♯","D♭","D","D♯","E♭","E","F","F♯","G♭","G","G♯","A♭","A","A♯","B♭","B"];

/* =====================================================================
   Songs — five hand-curated for plausibility
   ===================================================================== */
const SONGS = [
  {
    id: 12,
    title: "Corcovado",
    composer: "A. C. Jobim",
    year: 1960,
    genre: "Bossa Nova",
    originalKey: "Bb maj",
    tempo: "♩=84",
    timeSig: "4/4",
    form: "AABA",
    detectedKey: "Bb maj",
    manualKeyOverride: null,
    confidence: 0.94,
    hasXml: true,
    hasNotes: true,
    hasLyrics: true,
    measureCount: 32,
    chordCount: 64,
    importedAt: "2025-08-12 14:02",
    fsModifiedAt: "2024-11-04 09:31",
    sourceFileName: "corcovado-v2.mscz",
    sourceFileType: "mscz",
    overrideCount: 2,
    sections: [
      {
        id: 101, name: "A1", subtitle: "Tonic statement",
        measures: [
          M(1, [C({ symbol:"Gm7",    roman:"vi", romanCase:"minor", superscript:"7", function:"pre-V · inferred", keyCenter:"Bb maj", isInferred:true, confidence:0.55 })]),
          M(2, [C({ symbol:"F♯m7♭5", roman:"♯v", romanCase:"minor", superscript:"ø7", function:"chromatic · inferred", keyCenter:"Bb maj", isInferred:true, confidence:0.51 })]),
          M(3, [C({ symbol:"Am7",    roman:"vii", romanCase:"minor", superscript:"7/iii", function:"secondary ii", keyCenter:"Bb maj" })]),
          M(4, [C({ symbol:"D7♭9",   roman:"V", romanCase:"major", superscript:"7♭9/iii", function:"secondary V", keyCenter:"Bb maj" })]),
          M(5, [C({ symbol:"Gm7",    roman:"vi", romanCase:"minor", superscript:"7", function:"tonic substitute", keyCenter:"Bb maj", voicing:"rootless A · 3-7-9", comment:"Bill Evans uses this exact rootless voicing on Riverside take 2.", hasOverride:true, isManualEdit:true })]),
          M(6, [C({ symbol:"G♭7",    roman:"♭V", romanCase:"major", superscript:"7/ii", function:"tritone sub of C7", keyCenter:"Bb maj", comment:"Tritone sub — bass walks chromatically G → G♭ → F" })]),
          M(7, [C({ symbol:"F7♭9",   roman:"V", romanCase:"major", superscript:"7♭9", function:"dominant", keyCenter:"Bb maj" })]),
          M(8, [C({ symbol:"B♭△7",   roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Bb maj" })]),
        ]
      },
      {
        id: 102, name: "A2", subtitle: "Repeat → pivot",
        measures: [
          M(9,  [C({ symbol:"Am7",  roman:"vii", romanCase:"minor", superscript:"7/iii", function:"secondary ii", keyCenter:"Bb maj" })]),
          M(10, [C({ symbol:"D7♭9", roman:"V",  romanCase:"major", superscript:"7♭9/iii", function:"secondary V", keyCenter:"Bb maj" })]),
          M(11, [C({ symbol:"Gm7",  roman:"vi", romanCase:"minor", superscript:"7", function:"tonic sub", keyCenter:"Bb maj" })]),
          M(12, [C({ symbol:"G♭7",  roman:"♭V", romanCase:"major", superscript:"7/ii", function:"tritone sub", keyCenter:"Bb maj" })]),
          M(13, [C({ symbol:"Fm7",  roman:"v",  romanCase:"minor", superscript:"7", function:"predominant · ii of E♭", keyCenter:"Bb maj" })]),
          M(14, [C({ symbol:"B♭7♭9", roman:"I", romanCase:"major", superscript:"7♭9", function:"→ pivot · V/E♭", keyCenter:"Bb maj" })]),
          M(15, [C({ symbol:"E♭△7", roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic · key change", keyCenter:"Eb maj" })]),
          M(16, [C({ symbol:"A♭7",  roman:"IV", romanCase:"major", superscript:"7", function:"backdoor", keyCenter:"Eb maj" })]),
        ]
      },
      {
        id: 103, name: "B", subtitle: "Bridge in E♭",
        measures: [
          M(17, [C({ symbol:"E♭△7", roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Eb maj" })]),
          M(18, [C({ symbol:"A♭7",  roman:"IV", romanCase:"major", superscript:"7", function:"plagal", keyCenter:"Eb maj" })]),
          M(19, [C({ symbol:"B♭△7", roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Bb maj" })]),
          M(20, [C({ symbol:"Gm7",  roman:"vi", romanCase:"minor", superscript:"7", function:"tonic sub", keyCenter:"Bb maj" })]),
          M(21, [C({ symbol:"Cm7",  roman:"ii", romanCase:"minor", superscript:"7", function:"ii of V", keyCenter:"Bb maj" })]),
          M(22, [C({ symbol:"F7",   roman:"V",  romanCase:"major", superscript:"7", function:"dominant", keyCenter:"Bb maj" })]),
          M(23, [C({ symbol:"B♭△7", roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Bb maj" })]),
          M(24, [C({ symbol:"Gm7",  roman:"vi", romanCase:"minor", superscript:"7", function:"tonic sub", keyCenter:"Bb maj" })]),
        ]
      },
      {
        id: 104, name: "A3", subtitle: "Return + tag",
        measures: [
          M(25, [C({ symbol:"Cm7",  roman:"ii", romanCase:"minor", superscript:"7", function:"predominant", keyCenter:"Bb maj" })]),
          M(26, [C({ symbol:"F7",   roman:"V",  romanCase:"major", superscript:"7", function:"dominant", keyCenter:"Bb maj" })]),
          M(27, [C({ symbol:"B♭△7", roman:"I", romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Bb maj" })]),
          M(28, [C({ symbol:"Dm7♭5",roman:"iii",romanCase:"minor", superscript:"ø7", function:"chromatic", keyCenter:"Bb maj" })]),
          M(29, [C({ symbol:"G7♭9", roman:"VI", romanCase:"major", superscript:"7♭9", function:"secondary V/ii", keyCenter:"Bb maj" })]),
          M(30, [C({ symbol:"Cm7",  roman:"ii", romanCase:"minor", superscript:"7", function:"predominant", keyCenter:"Bb maj" })]),
          M(31, [C({ symbol:"F7♭13",roman:"V",  romanCase:"major", superscript:"7♭13", function:"dominant", keyCenter:"Bb maj" })]),
          M(32, [C({ symbol:"B♭6",  roman:"I", romanCase:"major", superscript:"6", function:"tonic", keyCenter:"Bb maj" })]),
        ]
      },
    ],
    keyRegions: [
      { startMeasure: 1,  endMeasure: 14, key:"Bb maj", weight: 14 },
      { startMeasure: 15, endMeasure: 18, key:"Eb maj", weight: 4 },
      { startMeasure: 19, endMeasure: 32, key:"Bb maj", weight: 14 },
    ],
    patterns: [
      { name:"ii–V–I in B♭", range:"m.25–27", confidence:0.96 },
      { name:"Tritone sub",   range:"m.6 · ♭V/ii" },
      { name:"Backdoor cadence", range:"m.16 → m.17" },
      { name:"Pivot modulation", range:"B♭7♭9 = V/E♭ · m.14" },
    ],
    phrases: [
      { range:"m.1–8",   name:"tonic statement" },
      { range:"m.9–16",  name:"repeat → pivot" },
      { range:"m.17–24", name:"B section in E♭" },
      { range:"m.25–32", name:"return + tag" },
    ],
    aiExchanges: [
      { date:"2025-08-10", question:"Why ♭V/ii instead of bII7?", outcome:"accepted" },
      { date:"2025-08-09", question:"Is m.5–8 a turnaround variant?", outcome:"rejected" },
      { date:"2025-08-03", question:"Explain the modulation at m.15.", outcome:"accepted" },
    ],
    importHistory: [
      { v:2, when:"2025-08-12 14:02:18", source:"corcovado-v2.mscz",     format:"mscz", chords:64, notes:412, status:"ok · 1842 ms",  warningCount:0 },
      { v:1, when:"2025-07-04 11:18:55", source:"corcovado-fakebook.pdf",format:"omr",  chords:58, notes:0,   status:"ok · 2 warnings", warningCount:2 },
    ],
  },

  {
    id: 7,
    title: "Autumn Leaves",
    composer: "J. Kosma",
    year: 1945,
    genre: "Standard",
    originalKey: "G min",
    tempo: "♩=132",
    timeSig: "4/4",
    form: "AABC",
    detectedKey: "G min",
    manualKeyOverride: null,
    confidence: 0.91,
    hasXml: true, hasNotes: true, hasLyrics: true,
    measureCount: 32, chordCount: 48,
    importedAt: "2025-07-30 09:18",
    fsModifiedAt: "2023-04-17 22:55",
    sourceFileName: "autumn-leaves.mscz", sourceFileType: "mscz",
    overrideCount: 0,
    sections: [
      { id:201, name:"A1", subtitle:"ii–V–I in B♭", measures: [
        M(1, [C({ symbol:"Cm7",  roman:"iv",  romanCase:"minor", superscript:"7", function:"ii of B♭", keyCenter:"Bb maj" })]),
        M(2, [C({ symbol:"F7",   roman:"♭VII",romanCase:"major", superscript:"7", function:"V of B♭", keyCenter:"Bb maj" })]),
        M(3, [C({ symbol:"B♭△7", roman:"♭III",romanCase:"major", superscript:"Δ7", function:"relative major tonic", keyCenter:"Bb maj" })]),
        M(4, [C({ symbol:"E♭△7", roman:"♭VI", romanCase:"major", superscript:"Δ7", function:"plagal", keyCenter:"Bb maj" })]),
        M(5, [C({ symbol:"Am7♭5",roman:"ii", romanCase:"minor", superscript:"ø7", function:"ii of G min", keyCenter:"G min" })]),
        M(6, [C({ symbol:"D7♭9", roman:"V",  romanCase:"major", superscript:"7♭9", function:"dominant", keyCenter:"G min" })]),
        M(7, [C({ symbol:"Gm7",  roman:"i",  romanCase:"minor", superscript:"7", function:"tonic", keyCenter:"G min" })]),
        M(8, [C({ symbol:"Gm7",  roman:"i",  romanCase:"minor", superscript:"7", function:"tonic", keyCenter:"G min" })]),
      ]},
    ],
    keyRegions: [
      { startMeasure: 1, endMeasure: 4, key:"Bb maj", weight: 4 },
      { startMeasure: 5, endMeasure: 8, key:"G min", weight: 4 },
    ],
    patterns: [
      { name:"ii–V–I in B♭", range:"m.1–3", confidence: 0.99 },
      { name:"ii–V–i in G min", range:"m.5–7", confidence: 0.97 },
    ],
    phrases: [{ range:"m.1–8", name:"A1 head" }],
    aiExchanges: [],
    importHistory: [{ v:1, when:"2025-07-30 09:18:00", source:"autumn-leaves.mscz", format:"mscz", chords:48, notes:280, status:"ok · 1102 ms", warningCount:0 }],
  },

  {
    id: 4,
    title: "All The Things You Are",
    composer: "J. Kern",
    year: 1939,
    genre: "Standard",
    originalKey: "Ab maj",
    tempo: "♩=140",
    timeSig: "4/4",
    form: "—",
    detectedKey: "Ab maj",
    manualKeyOverride: null,
    confidence: 0.88,
    hasXml: false, hasNotes: false, hasLyrics: false,
    measureCount: 36, chordCount: 72,
    importedAt: "2025-07-22 13:44",
    fsModifiedAt: null,
    sourceFileName: "all-the-things.mid", sourceFileType: "midi",
    overrideCount: 0,
    sections: [
      { id:301, name:"A1", subtitle:"Descent into F min", measures: [
        M(1, [C({ symbol:"Fm7",   roman:"vi", romanCase:"minor", superscript:"7", function:"relative minor", keyCenter:"Ab maj" })]),
        M(2, [C({ symbol:"B♭m7",  roman:"ii", romanCase:"minor", superscript:"7", function:"ii of E♭", keyCenter:"Ab maj" })]),
        M(3, [C({ symbol:"E♭7",   roman:"V",  romanCase:"major", superscript:"7", function:"V of A♭", keyCenter:"Ab maj" })]),
        M(4, [C({ symbol:"A♭△7",  roman:"I",  romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Ab maj" })]),
      ]},
    ],
    keyRegions: [{ startMeasure: 1, endMeasure: 4, key:"Ab maj", weight: 4 }],
    patterns: [], phrases: [], aiExchanges: [],
    importHistory: [{ v:1, when:"2025-07-22 13:44:00", source:"all-the-things.mid", format:"midi", chords:72, notes:0, status:"ok · 612 ms", warningCount:0 }],
  },

  {
    id: 22,
    title: "Giant Steps",
    composer: "J. Coltrane",
    year: 1960,
    genre: "Bebop",
    originalKey: "B maj",
    tempo: "♩=288",
    timeSig: "4/4",
    form: "cycle",
    detectedKey: "B maj",
    manualKeyOverride: null,
    confidence: 0.84,
    hasXml: true, hasNotes: false, hasLyrics: false,
    measureCount: 16, chordCount: 32,
    importedAt: "2025-06-01 19:40",
    fsModifiedAt: "2025-05-29 11:10",
    sourceFileName: "giant-steps.mscz", sourceFileType: "mscz",
    overrideCount: 3,
    sections: [
      { id:401, name:"A", subtitle:"Coltrane changes — 3-key cycle", measures: [
        M(1, [C({ symbol:"B△7",  roman:"I",  romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"B maj" })]),
        M(2, [C({ symbol:"D7",   roman:"♭III",romanCase:"major", superscript:"7", function:"V of G", keyCenter:"B maj" })]),
        M(3, [C({ symbol:"G△7",  roman:"I",  romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"G maj" })]),
        M(4, [C({ symbol:"B♭7",  roman:"♭III",romanCase:"major", superscript:"7", function:"V of E♭", keyCenter:"G maj" })]),
        M(5, [C({ symbol:"E♭△7", roman:"I",  romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"Eb maj" })]),
        M(6, [C({ symbol:"Am7",  roman:"ii", romanCase:"minor", superscript:"7", function:"ii of G", keyCenter:"G maj" })]),
        M(7, [C({ symbol:"D7",   roman:"V",  romanCase:"major", superscript:"7", function:"V of G", keyCenter:"G maj" })]),
        M(8, [C({ symbol:"G△7",  roman:"I",  romanCase:"major", superscript:"Δ7", function:"tonic", keyCenter:"G maj" })]),
      ]},
    ],
    keyRegions: [
      { startMeasure: 1, endMeasure: 2, key:"B maj", weight: 2 },
      { startMeasure: 3, endMeasure: 4, key:"G maj", weight: 2 },
      { startMeasure: 5, endMeasure: 5, key:"Eb maj", weight: 1 },
      { startMeasure: 6, endMeasure: 8, key:"G maj", weight: 3 },
    ],
    patterns: [{ name:"3-tonic cycle", range:"m.1–5", confidence:0.99 }],
    phrases: [{ range:"m.1–8", name:"A cycle" }],
    aiExchanges: [],
    importHistory: [{ v:1, when:"2025-06-01 19:40:00", source:"giant-steps.mscz", format:"mscz", chords:32, notes:0, status:"ok · 802 ms", warningCount:0 }],
  },

  {
    id: 31,
    title: "Stella By Starlight",
    composer: "V. Young",
    year: 1944,
    genre: "Standard",
    originalKey: "Bb maj",
    tempo: "♩=120",
    timeSig: "4/4",
    form: "—",
    detectedKey: "Bb maj",
    manualKeyOverride: null,
    confidence: 0.86,
    hasXml: true, hasNotes: false, hasLyrics: false,
    measureCount: 32, chordCount: 56,
    importedAt: "2025-07-08 11:12",
    fsModifiedAt: "2022-09-09 15:00",
    sourceFileName: "stella.mscz", sourceFileType: "mscz",
    overrideCount: 0,
    sections: [
      { id:501, name:"A", subtitle:"Opening", measures: [
        M(1, [C({ symbol:"Em7♭5", roman:"iv", romanCase:"minor", superscript:"ø7", function:"ii of D min", keyCenter:"D min" })]),
        M(2, [C({ symbol:"A7♭9",  roman:"V",  romanCase:"major", superscript:"7♭9", function:"V of D min", keyCenter:"D min" })]),
        M(3, [C({ symbol:"Cm7",   roman:"ii", romanCase:"minor", superscript:"7", function:"ii of B♭", keyCenter:"Bb maj" })]),
        M(4, [C({ symbol:"F7",    roman:"V",  romanCase:"major", superscript:"7", function:"V of B♭", keyCenter:"Bb maj" })]),
      ]},
    ],
    keyRegions: [
      { startMeasure: 1, endMeasure: 2, key:"D min", weight: 2 },
      { startMeasure: 3, endMeasure: 4, key:"Bb maj", weight: 2 },
    ],
    patterns: [], phrases: [], aiExchanges: [],
    importHistory: [{ v:1, when:"2025-07-08 11:12:00", source:"stella.mscz", format:"mscz", chords:56, notes:0, status:"ok · 1108 ms", warningCount:0 }],
  },
];

/* "rest of library" — 37 more songs as compact rows (table only) */
const LIBRARY_EXTRA = [
  { id: 5, title:"Body And Soul", composer:"J. Green", genre:"Standard", key:"Db maj", form:"AABA", measureCount:32, chordCount:60, importedAt:"2025-05-19 08:55", fsModifiedAt:"2024-02-11 18:22", hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 8, title:"'Round Midnight", composer:"T. Monk", genre:"Standard", key:"Eb min", form:"AABA", measureCount:32, chordCount:68, importedAt:"2025-04-30 23:11", fsModifiedAt:"2024-06-04 10:05", hasXml:true, hasNotes:true, hasLyrics:false, overrideCount:1 },
  { id: 9, title:"Misty", composer:"E. Garner", genre:"Standard", key:"Eb maj", form:"AABA", measureCount:32, chordCount:54, importedAt:"2025-04-12 17:30", fsModifiedAt:null, hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 10, title:"Solar", composer:"M. Davis", genre:"Modal", key:"C min", form:"—", measureCount:12, chordCount:24, importedAt:"2025-03-22 12:08", fsModifiedAt:"2023-11-19 14:48", hasXml:true, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 11, title:"Blue Bossa", composer:"K. Dorham", genre:"Bossa Nova", key:"C min", form:"AB", measureCount:16, chordCount:16, importedAt:"2025-03-04 18:00", fsModifiedAt:"2024-08-22 09:00", hasXml:true, hasNotes:true, hasLyrics:false, overrideCount:0 },
  { id: 13, title:"Take Five", composer:"P. Desmond", genre:"Standard", key:"Eb min", form:"AABA", measureCount:32, chordCount:32, importedAt:"2025-02-22 14:11", fsModifiedAt:null, hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 14, title:"So What", composer:"M. Davis", genre:"Modal", key:"D min", form:"AABA", measureCount:32, chordCount:8,  importedAt:"2025-02-10 12:22", fsModifiedAt:"2023-02-04 11:32", hasXml:true, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 15, title:"Beautiful Love", composer:"V. Young", genre:"Standard", key:"D min", form:"—", measureCount:32, chordCount:44, importedAt:"2025-01-28 09:30", fsModifiedAt:null, hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 16, title:"Have You Met Miss Jones", composer:"R. Rodgers", genre:"Standard", key:"F maj", form:"AABA", measureCount:32, chordCount:62, importedAt:"2025-01-15 11:45", fsModifiedAt:"2024-09-13 19:18", hasXml:true, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 17, title:"There Will Never Be Another You", composer:"H. Warren", genre:"Standard", key:"Eb maj", form:"—", measureCount:32, chordCount:48, importedAt:"2025-01-04 17:22", fsModifiedAt:null, hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 18, title:"In A Sentimental Mood", composer:"D. Ellington", genre:"Standard", key:"D min", form:"AABA", measureCount:32, chordCount:54, importedAt:"2024-12-22 14:00", fsModifiedAt:"2023-10-21 08:00", hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
  { id: 19, title:"Satin Doll", composer:"D. Ellington", genre:"Standard", key:"C maj", form:"AABA", measureCount:32, chordCount:60, importedAt:"2024-12-08 19:14", fsModifiedAt:null, hasXml:false, hasNotes:false, hasLyrics:false, overrideCount:0 },
];

/* helper: flat list of all songs for the library page */
const ALL_LIBRARY_ROWS = [
  ...SONGS.map(s => ({
    id: s.id, title: s.title, composer: s.composer, genre: s.genre,
    key: s.detectedKey, form: s.form,
    measureCount: s.measureCount, chordCount: s.chordCount,
    importedAt: s.importedAt, fsModifiedAt: s.fsModifiedAt,
    hasXml: s.hasXml, hasNotes: s.hasNotes, hasLyrics: s.hasLyrics,
    overrideCount: s.overrideCount,
  })),
  ...LIBRARY_EXTRA,
];

/* helper: flatten chords across sections with 0-based chord_index */
function flattenChords(song) {
  let idx = 0;
  const out = [];
  for (const sec of song.sections) {
    for (const meas of sec.measures) {
      for (const ch of meas.chords) {
        out.push({ ...ch, chordIndex: idx, sectionId: sec.id, measureNumber: meas.number });
        idx++;
      }
    }
  }
  return out;
}

/* helper: key class for chord cell strip — maps song's keyCenter to k-XX */
function keyCss(keyCenter) {
  const map = {
    "C maj":"k-C", "G maj":"k-G", "D maj":"k-D", "A maj":"k-A", "E maj":"k-E",
    "B maj":"k-B", "F# maj":"k-Fs", "F maj":"k-F", "Bb maj":"k-Bb", "Eb maj":"k-Eb",
    "Ab maj":"k-Ab", "Db maj":"k-Db",
    "A min":"k-C", "E min":"k-G", "B min":"k-D", "F# min":"k-A", "C# min":"k-E",
    "G# min":"k-B", "D# min":"k-Fs", "D min":"k-F", "G min":"k-Bb", "C min":"k-Eb",
    "F min":"k-Ab", "Bb min":"k-Db",
  };
  return map[keyCenter] || "";
}

/* localStorage persistence helpers */
const LS_KEY = "harmonylab_prototype_state_v1";
function loadState() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; }
  catch (e) { return {}; }
}
function saveState(patch) {
  const cur = loadState();
  const next = { ...cur, ...patch };
  try { localStorage.setItem(LS_KEY, JSON.stringify(next)); } catch (e) {}
  return next;
}

/* export to global */
Object.assign(window, {
  HL_DATA: { SONGS, LIBRARY_EXTRA, ALL_LIBRARY_ROWS, KEY_COLOR_DEFAULTS, CHORD_QUALITIES, ROOT_NOTES },
  hlFlattenChords: flattenChords,
  hlKeyCss: keyCss,
  hlLoadState: loadState,
  hlSaveState: saveState,
});
