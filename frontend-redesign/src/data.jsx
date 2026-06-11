/* =====================================================================
   HarmonyLab — data helpers (HM44.1 live app, no mock songs)
   Provides KEY_COLOR_DEFAULTS, CHORD_QUALITIES, ROOT_NOTES, keyCss.
   API transforms and data hooks live in api.jsx.
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

const CHORD_QUALITIES = [
  { suffix: "",      displayJazz: "",        displayPlain: "",        type: "major",       intervals: "1-3-5",              aliases: ["maj"] },
  { suffix: "m",     displayJazz: "m",       displayPlain: "m",       type: "minor",       intervals: "1-♭3-5",             aliases: ["min","-"] },
  { suffix: "7",     displayJazz: "7",       displayPlain: "7",       type: "dominant 7",  intervals: "1-3-5-♭7",           aliases: ["dom7"] },
  { suffix: "△7",    displayJazz: "△7",      displayPlain: "maj7",    type: "major 7",     intervals: "1-3-5-7",            aliases: ["maj7","M7","Δ7"] },
  { suffix: "m7",    displayJazz: "m7",      displayPlain: "m7",      type: "minor 7",     intervals: "1-♭3-5-♭7",          aliases: ["min7","-7"] },
  { suffix: "m△7",   displayJazz: "m△7",     displayPlain: "mMaj7",   type: "minor-major", intervals: "1-♭3-5-7",           aliases: ["mMaj7","mM7","-Δ7"] },
  { suffix: "ø7",    displayJazz: "ø7",      displayPlain: "m7♭5",    type: "half-dim",    intervals: "1-♭3-♭5-♭7",         aliases: ["m7b5","ø","-7♭5"] },
  { suffix: "°7",    displayJazz: "°7",      displayPlain: "dim7",    type: "diminished 7",intervals: "1-♭3-♭5-♭♭7",        aliases: ["dim7","o7"] },
  { suffix: "°",     displayJazz: "°",       displayPlain: "dim",     type: "diminished",  intervals: "1-♭3-♭5",            aliases: ["dim","o"] },
  { suffix: "+",     displayJazz: "+",       displayPlain: "aug",     type: "augmented",   intervals: "1-3-♯5",             aliases: ["aug","+5","♯5"] },
  { suffix: "+7",    displayJazz: "+7",      displayPlain: "aug7",    type: "augmented 7", intervals: "1-3-♯5-♭7",          aliases: ["7♯5","aug7"] },
  { suffix: "7♭5",   displayJazz: "7♭5",     displayPlain: "7b5",     type: "dominant ♭5", intervals: "1-3-♭5-♭7",          aliases: ["7b5"] },
  { suffix: "7♭9",   displayJazz: "7♭9",     displayPlain: "7b9",     type: "dom 7♭9",     intervals: "1-3-5-♭7-♭9",        aliases: ["7b9"] },
  { suffix: "7♯9",   displayJazz: "7♯9",     displayPlain: "7#9",     type: "dom 7♯9",     intervals: "1-3-5-♭7-♯9",        aliases: ["7#9"] },
  { suffix: "7♯11",  displayJazz: "7♯11",    displayPlain: "7#11",    type: "dom 7♯11",    intervals: "1-3-5-♭7-♯11",       aliases: ["7#11"] },
  { suffix: "7♭13",  displayJazz: "7♭13",    displayPlain: "7b13",    type: "dom 7♭13",    intervals: "1-3-5-♭7-♭13",       aliases: ["7b13"] },
  { suffix: "7alt",  displayJazz: "7alt",    displayPlain: "7alt",    type: "altered dom", intervals: "1-3-♭5/♯5-♭7-♭9/♯9", aliases: ["alt"] },
  { suffix: "9",     displayJazz: "9",       displayPlain: "9",       type: "dom 9",       intervals: "1-3-5-♭7-9",         aliases: [] },
  { suffix: "△9",    displayJazz: "△9",      displayPlain: "maj9",    type: "major 9",     intervals: "1-3-5-7-9",          aliases: ["maj9","M9"] },
  { suffix: "m9",    displayJazz: "m9",      displayPlain: "m9",      type: "minor 9",     intervals: "1-♭3-5-♭7-9",        aliases: ["-9"] },
  { suffix: "11",    displayJazz: "11",      displayPlain: "11",      type: "dom 11",      intervals: "1-3-5-♭7-9-11",      aliases: [] },
  { suffix: "13",    displayJazz: "13",      displayPlain: "13",      type: "dom 13",      intervals: "1-3-5-♭7-9-11-13",   aliases: [] },
  { suffix: "△13",   displayJazz: "△13",     displayPlain: "maj13",   type: "major 13",    intervals: "1-3-5-7-9-11-13",    aliases: ["maj13"] },
  { suffix: "6",     displayJazz: "6",       displayPlain: "6",       type: "major 6",     intervals: "1-3-5-6",            aliases: [] },
  { suffix: "m6",    displayJazz: "m6",      displayPlain: "m6",      type: "minor 6",     intervals: "1-♭3-5-6",           aliases: [] },
  { suffix: "6/9",   displayJazz: "6/9",     displayPlain: "6/9",     type: "6/9",         intervals: "1-3-5-6-9",          aliases: [] },
  { suffix: "sus2",  displayJazz: "sus2",    displayPlain: "sus2",    type: "sus 2",       intervals: "1-2-5",              aliases: [] },
  { suffix: "sus4",  displayJazz: "sus4",    displayPlain: "sus4",    type: "sus 4",       intervals: "1-4-5",              aliases: ["sus"] },
  { suffix: "7sus4", displayJazz: "7sus4",   displayPlain: "7sus4",   type: "dom 7sus4",   intervals: "1-4-5-♭7",           aliases: ["7sus"] },
  { suffix: "add9",  displayJazz: "add9",    displayPlain: "add9",    type: "add 9",       intervals: "1-3-5-9",            aliases: [] },
];

const ROOT_NOTES = ["C","C♯","D♭","D","D♯","E♭","E","F","F♯","G♭","G","G♯","A♭","A","A♯","B♭","B"];

window.HL_DATA = {
  KEY_COLOR_DEFAULTS,
  CHORD_QUALITIES,
  ROOT_NOTES,
};
