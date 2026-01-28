/**
 * Chord Voicing Utilities for HarmonyLab
 * Converts chord symbols to full voicings with all chord tones.
 */

/**
 * Chord quality to intervals (semitones from root).
 * These create proper jazz voicings with all chord tones.
 */
const CHORD_INTERVALS = {
  // Triads
  'Maj': [0, 4, 7],
  'm': [0, 3, 7],
  'min': [0, 3, 7],
  'dim': [0, 3, 6],
  'aug': [0, 4, 8],
  
  // Sixth chords - IMPORTANT: includes the 6th!
  '6': [0, 4, 7, 9],           // Maj6: root, 3, 5, 6
  'm6': [0, 3, 7, 9],          // min6: root, b3, 5, 6
  'min6': [0, 3, 7, 9],
  
  // Seventh chords
  'Maj7': [0, 4, 7, 11],       // root, 3, 5, 7
  'maj7': [0, 4, 7, 11],
  'M7': [0, 4, 7, 11],
  'm7': [0, 3, 7, 10],         // root, b3, 5, b7
  'min7': [0, 3, 7, 10],
  '-7': [0, 3, 7, 10],
  '7': [0, 4, 7, 10],          // dominant: root, 3, 5, b7
  'dom7': [0, 4, 7, 10],
  'ø7': [0, 3, 6, 10],         // half-dim: root, b3, b5, b7
  'm7b5': [0, 3, 6, 10],
  'dim7': [0, 3, 6, 9],        // full dim: root, b3, b5, bb7
  'mMaj7': [0, 3, 7, 11],      // minor-major7
  
  // Ninth chords
  '9': [0, 4, 7, 10, 14],      // dominant 9
  'Maj9': [0, 4, 7, 11, 14],   // major 9
  'M9': [0, 4, 7, 11, 14],
  'm9': [0, 3, 7, 10, 14],     // minor 9
  'min9': [0, 3, 7, 10, 14],
  'add9': [0, 4, 7, 14],       // add9 (no 7th)
  'm(add9)': [0, 3, 7, 14],
  
  // 11th chords
  '11': [0, 4, 7, 10, 14, 17],
  'm11': [0, 3, 7, 10, 14, 17],
  
  // 13th chords
  '13': [0, 4, 7, 10, 14, 21],
  'Maj13': [0, 4, 7, 11, 14, 21],
  'm13': [0, 3, 7, 10, 14, 21],
  
  // Suspended
  'sus4': [0, 5, 7],
  'sus2': [0, 2, 7],
  '7sus4': [0, 5, 7, 10],
  '9sus4': [0, 5, 7, 10, 14],
  
  // Altered dominants
  '7b9': [0, 4, 7, 10, 13],
  '7#9': [0, 4, 7, 10, 15],
  '7#11': [0, 4, 7, 10, 18],
  '7alt': [0, 4, 8, 10, 13],   // altered (b5/#5, b9/#9)
  '7b5': [0, 4, 6, 10],
  '7#5': [0, 4, 8, 10],
  'aug7': [0, 4, 8, 10],
  
  // Power chord
  '5': [0, 7],
}

/**
 * Note name to semitone offset (C = 0)
 */
const NOTE_TO_MIDI = {
  'C': 0, 'C#': 1, 'Db': 1,
  'D': 2, 'D#': 3, 'Eb': 3,
  'E': 4, 'Fb': 4, 'E#': 5,
  'F': 5, 'F#': 6, 'Gb': 6,
  'G': 7, 'G#': 8, 'Ab': 8,
  'A': 9, 'A#': 10, 'Bb': 10,
  'B': 11, 'B#': 0, 'Cb': 11,
}

/**
 * Parse chord symbol into root and quality.
 * Handles: C, Cm, Cmaj7, Cm7, C7, Cdim, Caug, Cm6, C6, Cm9, etc.
 */
export function parseChordSymbol(symbol) {
  if (!symbol) return { root: null, quality: null }
  
  // Match root note (with optional sharp/flat)
  const rootMatch = symbol.match(/^([A-G][#b]?)/)
  if (!rootMatch) return { root: null, quality: null }
  
  const root = rootMatch[1]
  const quality = symbol.slice(root.length) || 'Maj'
  
  return { root, quality }
}

/**
 * Convert MIDI note number to note name with octave.
 */
function midiToNoteName(midi) {
  const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  const octave = Math.floor(midi / 12) - 1
  const note = noteNames[midi % 12]
  return `${note}${octave}`
}

/**
 * Convert a chord symbol to an array of MIDI note names for Tone.js playback.
 * Returns jazz-appropriate voicings with all chord tones.
 * 
 * @param {string} chordSymbol - e.g., "Am6", "Dm7", "G7", "Cmaj7"
 * @param {number} octave - Base octave (default 3 for left-hand voicing)
 * @param {number} inversion - 0=root, 1=1st, 2=2nd, 3=3rd (default 0)
 * @returns {string[]} - Array of note names like ["A3", "C4", "E4", "F#4"]
 */
export function chordToNotes(chordSymbol, octave = 3, inversion = 0) {
  // Parse the chord symbol
  const { root, quality } = parseChordSymbol(chordSymbol)
  
  if (!root) return ['C4', 'E4', 'G4'] // Default fallback
  
  // Get intervals for this chord quality
  const intervals = CHORD_INTERVALS[quality] || CHORD_INTERVALS['Maj']
  
  // Convert root to MIDI base
  const rootMidi = NOTE_TO_MIDI[root]
  if (rootMidi === undefined) return ['C4', 'E4', 'G4']
  
  // Build voicing
  const baseMidi = rootMidi + (octave + 1) * 12 // +1 because MIDI octave -1 starts at 0
  
  // Generate notes with intervals
  let midiNotes = intervals.map(interval => baseMidi + interval)
  
  // Apply inversion
  if (inversion > 0 && inversion < midiNotes.length) {
    // Move the first N notes up an octave
    for (let i = 0; i < inversion; i++) {
      midiNotes[i] += 12
    }
    // Re-sort so bass note is first
    midiNotes.sort((a, b) => a - b)
  }
  
  // Convert to note names
  const notes = midiNotes.map(midi => midiToNoteName(midi))
  
  return notes
}

/**
 * Get inversion label with bass note.
 */
export function getInversionLabel(chordSymbol, inversion) {
  const notes = chordToNotes(chordSymbol, 3, inversion)
  if (!notes.length) return ''
  
  const bassNote = notes[0].replace(/\d+$/, '') // Remove octave
  
  switch (inversion) {
    case 0: return `Root position (${bassNote} in bass)`
    case 1: return `1st inversion (${bassNote} in bass)`
    case 2: return `2nd inversion (${bassNote} in bass)`
    case 3: return `3rd inversion (${bassNote} in bass)`
    default: return 'Root position'
  }
}

export default { chordToNotes, parseChordSymbol, getInversionLabel }
