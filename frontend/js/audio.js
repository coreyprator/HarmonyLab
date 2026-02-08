/**
 * HarmonyLab Audio Service
 * Uses Tone.js with Salamander Grand Piano samples
 * Provides play, arpeggiate, and loop functionality for chords
 */

// Load Tone.js from CDN (loaded in HTML)
// <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"></script>

const HarmonyAudio = (function() {
    'use strict';

    // State
    let sampler = null;
    let isLoaded = false;
    let isLoading = false;
    let isPlaying = false;
    let loopId = null;
    let volume = 0.8;
    let audioUnlocked = false;

    // Salamander Grand Piano samples (hosted on CDN)
    const SALAMANDER_URL = 'https://nbrosowsky.github.io/tonern-instruments/samples/piano/';

    // Map chord symbols to MIDI notes
    // Base octave is 4 (middle C = C4)
    const NOTE_MAP = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
        'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    };

    // Common chord voicings (intervals from root)
    const CHORD_VOICINGS = {
        // Major family
        'maj': [0, 4, 7],
        'M': [0, 4, 7],
        '': [0, 4, 7],
        'maj7': [0, 4, 7, 11],
        'M7': [0, 4, 7, 11],
        'maj9': [0, 4, 7, 11, 14],
        '6': [0, 4, 7, 9],
        '6/9': [0, 4, 7, 9, 14],

        // Minor family
        'm': [0, 3, 7],
        'min': [0, 3, 7],
        '-': [0, 3, 7],
        'm7': [0, 3, 7, 10],
        'min7': [0, 3, 7, 10],
        '-7': [0, 3, 7, 10],
        'm9': [0, 3, 7, 10, 14],
        'm11': [0, 3, 7, 10, 14, 17],
        'm6': [0, 3, 7, 9],

        // Dominant family
        '7': [0, 4, 7, 10],
        'dom7': [0, 4, 7, 10],
        '9': [0, 4, 7, 10, 14],
        '13': [0, 4, 7, 10, 14, 21],
        '7#9': [0, 4, 7, 10, 15],
        '7b9': [0, 4, 7, 10, 13],
        '7#11': [0, 4, 7, 10, 18],
        '7alt': [0, 4, 8, 10, 13],

        // Diminished
        'dim': [0, 3, 6],
        'dim7': [0, 3, 6, 9],
        'o7': [0, 3, 6, 9],

        // Half-diminished
        'm7b5': [0, 3, 6, 10],
        'o': [0, 3, 6, 10],
        'half-dim': [0, 3, 6, 10],

        // Augmented
        'aug': [0, 4, 8],
        '+': [0, 4, 8],
        'aug7': [0, 4, 8, 10],

        // Suspended
        'sus4': [0, 5, 7],
        'sus2': [0, 2, 7],
        '7sus4': [0, 5, 7, 10],
    };

    /**
     * Initialize the audio system
     * Must be called after user interaction (for iOS)
     */
    async function init() {
        if (isLoaded || isLoading) return;
        isLoading = true;

        try {
            // Ensure audio context is started (required for iOS)
            await Tone.start();
            audioUnlocked = true;

            // Create the sampler with Salamander piano samples
            sampler = new Tone.Sampler({
                urls: {
                    'A0': 'A0.mp3',
                    'C1': 'C1.mp3',
                    'D#1': 'Ds1.mp3',
                    'F#1': 'Fs1.mp3',
                    'A1': 'A1.mp3',
                    'C2': 'C2.mp3',
                    'D#2': 'Ds2.mp3',
                    'F#2': 'Fs2.mp3',
                    'A2': 'A2.mp3',
                    'C3': 'C3.mp3',
                    'D#3': 'Ds3.mp3',
                    'F#3': 'Fs3.mp3',
                    'A3': 'A3.mp3',
                    'C4': 'C4.mp3',
                    'D#4': 'Ds4.mp3',
                    'F#4': 'Fs4.mp3',
                    'A4': 'A4.mp3',
                    'C5': 'C5.mp3',
                    'D#5': 'Ds5.mp3',
                    'F#5': 'Fs5.mp3',
                    'A5': 'A5.mp3',
                    'C6': 'C6.mp3',
                    'D#6': 'Ds6.mp3',
                    'F#6': 'Fs6.mp3',
                    'A6': 'A6.mp3',
                    'C7': 'C7.mp3',
                    'D#7': 'Ds7.mp3',
                    'F#7': 'Fs7.mp3',
                    'A7': 'A7.mp3',
                    'C8': 'C8.mp3',
                },
                baseUrl: SALAMANDER_URL,
                onload: () => {
                    console.log('HarmonyAudio: Piano samples loaded');
                    isLoaded = true;
                    isLoading = false;
                },
                onerror: (err) => {
                    console.error('HarmonyAudio: Failed to load samples', err);
                    isLoading = false;
                }
            }).toDestination();

            // Set initial volume
            sampler.volume.value = Tone.gainToDb(volume);

        } catch (err) {
            console.error('HarmonyAudio: Init failed', err);
            isLoading = false;
        }
    }

    /**
     * Parse a chord symbol into MIDI notes
     * @param {string} chordSymbol - e.g., "Cmaj7", "Dm7", "G7#9"
     * @param {number} octave - Base octave (default 3 for left hand)
     * @returns {string[]} Array of note names with octaves
     */
    function parseChord(chordSymbol, octave = 3) {
        if (!chordSymbol || chordSymbol === '?') return [];

        // Extract root note and quality
        const match = chordSymbol.match(/^([A-G][#b]?)(.*)$/);
        if (!match) return [];

        const root = match[1];
        let quality = match[2] || '';

        // Handle bass note (e.g., Dm7/A)
        const slashIndex = quality.indexOf('/');
        if (slashIndex > 0) {
            quality = quality.substring(0, slashIndex);
        }

        // Get root MIDI number
        const rootNum = NOTE_MAP[root];
        if (rootNum === undefined) return [];

        // Find matching voicing
        let intervals = CHORD_VOICINGS[quality] || CHORD_VOICINGS[''];

        // Build notes array
        const notes = intervals.map(interval => {
            const midiNote = rootNum + interval;
            const noteOctave = octave + Math.floor(midiNote / 12);
            const noteName = Object.keys(NOTE_MAP).find(k => NOTE_MAP[k] === midiNote % 12);
            return noteName + noteOctave;
        });

        return notes;
    }

    /**
     * Play a chord (all notes simultaneously)
     * @param {string} chordSymbol - Chord to play
     * @param {number} duration - Duration in seconds
     */
    async function play(chordSymbol, duration = 1.5) {
        if (!isLoaded) {
            await init();
            // Wait for load
            while (isLoading) {
                await new Promise(r => setTimeout(r, 100));
            }
        }

        stop();

        const notes = parseChord(chordSymbol);
        if (notes.length === 0) return;

        isPlaying = true;
        sampler.triggerAttackRelease(notes, duration);

        setTimeout(() => {
            isPlaying = false;
        }, duration * 1000);
    }

    /**
     * Play a chord as an arpeggio (bottom to top)
     * @param {string} chordSymbol - Chord to arpeggiate
     * @param {number} noteDelay - Delay between notes in seconds
     */
    async function arpeggiate(chordSymbol, noteDelay = 0.15) {
        if (!isLoaded) {
            await init();
            while (isLoading) {
                await new Promise(r => setTimeout(r, 100));
            }
        }

        stop();

        const notes = parseChord(chordSymbol);
        if (notes.length === 0) return;

        isPlaying = true;

        const now = Tone.now();
        notes.forEach((note, i) => {
            sampler.triggerAttackRelease(note, 1.5, now + i * noteDelay);
        });

        const totalDuration = notes.length * noteDelay * 1000 + 1500;
        setTimeout(() => {
            isPlaying = false;
        }, totalDuration);
    }

    /**
     * Loop a chord with arpeggiation
     * @param {string} chordSymbol - Chord to loop
     * @param {number} interval - Interval between repetitions in seconds
     */
    async function startLoop(chordSymbol, interval = 2) {
        if (!isLoaded) {
            await init();
            while (isLoading) {
                await new Promise(r => setTimeout(r, 100));
            }
        }

        stopLoop();

        isPlaying = true;

        // Play immediately
        arpeggiate(chordSymbol);

        // Set up loop
        loopId = setInterval(() => {
            arpeggiate(chordSymbol);
        }, interval * 1000);
    }

    /**
     * Stop the current loop
     */
    function stopLoop() {
        if (loopId) {
            clearInterval(loopId);
            loopId = null;
        }
        stop();
    }

    /**
     * Stop all sounds immediately
     */
    function stop() {
        if (sampler) {
            sampler.releaseAll();
        }
        isPlaying = false;
    }

    /**
     * Set volume (0-1)
     */
    function setVolume(val) {
        volume = Math.max(0, Math.min(1, val));
        if (sampler) {
            sampler.volume.value = Tone.gainToDb(volume);
        }
    }

    /**
     * Get current volume
     */
    function getVolume() {
        return volume;
    }

    /**
     * Check if audio is ready
     */
    function isReady() {
        return isLoaded;
    }

    /**
     * Check if currently playing
     */
    function getIsPlaying() {
        return isPlaying;
    }

    /**
     * Unlock audio on iOS (must be called from user gesture)
     */
    async function unlockAudio() {
        if (audioUnlocked) return true;
        try {
            await Tone.start();
            audioUnlocked = true;
            return true;
        } catch (err) {
            console.error('Failed to unlock audio:', err);
            return false;
        }
    }

    // Public API
    return {
        init,
        play,
        arpeggiate,
        startLoop,
        stopLoop,
        stop,
        setVolume,
        getVolume,
        isReady,
        isPlaying: getIsPlaying,
        unlockAudio,
        parseChord
    };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HarmonyAudio;
}
