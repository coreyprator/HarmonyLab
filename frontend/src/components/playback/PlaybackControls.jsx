import { useState, useEffect } from 'react'
import * as Tone from 'tone'

export default function PlaybackControls({ progression }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentChord, setCurrentChord] = useState(null)
  const [tempo, setTempo] = useState(120)

  // Initialize Tone.js synth
  const [synth] = useState(() => 
    new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'sine' },
      envelope: {
        attack: 0.02,
        decay: 0.1,
        sustain: 0.3,
        release: 1,
      },
    }).toDestination()
  )

  useEffect(() => {
    return () => {
      synth.dispose()
      Tone.Transport.stop()
      Tone.Transport.cancel()
    }
  }, [synth])

  const playProgression = async () => {
    if (!progression?.sections) return

    // Start Tone.js context (required for audio)
    await Tone.start()

    setIsPlaying(true)
    Tone.Transport.bpm.value = tempo

    let time = 0
    const beatDuration = 60 / tempo // seconds per beat

    progression.sections.forEach(section => {
      for (let repeat = 0; repeat < (section.repeat_count || 1); repeat++) {
        section.measures.forEach(measure => {
          measure.chords.forEach(chord => {
            const chordNotes = parseChordSymbol(chord.chord_symbol)
            Tone.Transport.schedule((scheduleTime) => {
              synth.triggerAttackRelease(chordNotes, '2n', scheduleTime)
              setCurrentChord(chord.chord_symbol)
            }, time)
            time += beatDuration * 4 // 4 beats per measure (simplified)
          })
        })
      }
    })

    // Schedule stop at the end
    Tone.Transport.schedule(() => {
      setIsPlaying(false)
      setCurrentChord(null)
      Tone.Transport.stop()
      Tone.Transport.cancel()
    }, time)

    Tone.Transport.start()
  }

  const stopPlayback = () => {
    Tone.Transport.stop()
    Tone.Transport.cancel()
    setIsPlaying(false)
    setCurrentChord(null)
  }

  // Simple chord symbol parser (converts chord symbols to MIDI notes)
  const parseChordSymbol = (symbol) => {
    // Remove extensions for now, just get root and quality
    const rootMap = {
      'C': 'C4', 'Db': 'Db4', 'D': 'D4', 'Eb': 'Eb4', 'E': 'E4', 'F': 'F4',
      'Gb': 'Gb4', 'G': 'G4', 'Ab': 'Ab4', 'A': 'A4', 'Bb': 'Bb4', 'B': 'B4'
    }

    // Parse root note
    let root = symbol.match(/^[A-G][b#]?/)?.[0] || 'C'
    const rootNote = rootMap[root] || 'C4'

    // Determine chord quality and build intervals
    if (symbol.includes('m') && !symbol.includes('maj')) {
      // Minor chord: root, minor 3rd, perfect 5th
      return [rootNote, Tone.Frequency(rootNote).transpose(3).toNote(), Tone.Frequency(rootNote).transpose(7).toNote()]
    } else if (symbol.includes('dim')) {
      // Diminished: root, minor 3rd, diminished 5th
      return [rootNote, Tone.Frequency(rootNote).transpose(3).toNote(), Tone.Frequency(rootNote).transpose(6).toNote()]
    } else if (symbol.includes('aug')) {
      // Augmented: root, major 3rd, augmented 5th
      return [rootNote, Tone.Frequency(rootNote).transpose(4).toNote(), Tone.Frequency(rootNote).transpose(8).toNote()]
    } else {
      // Major chord: root, major 3rd, perfect 5th
      return [rootNote, Tone.Frequency(rootNote).transpose(4).toNote(), Tone.Frequency(rootNote).transpose(7).toNote()]
    }
  }

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={isPlaying ? stopPlayback : playProgression}
        className={isPlaying ? 'btn-secondary' : 'btn-primary'}
        disabled={!progression?.sections?.length}
      >
        {isPlaying ? '⏹ Stop' : '▶ Play'}
      </button>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">Tempo:</label>
        <input
          type="range"
          min="60"
          max="200"
          value={tempo}
          onChange={(e) => setTempo(Number(e.target.value))}
          className="w-32"
          disabled={isPlaying}
        />
        <span className="text-sm w-12">{tempo} BPM</span>
      </div>

      {currentChord && (
        <div className="px-4 py-2 bg-primary text-white rounded-lg font-semibold">
          {currentChord}
        </div>
      )}
    </div>
  )
}
