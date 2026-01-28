import { useState, useEffect, useRef } from 'react'
import * as Tone from 'tone'
import { chordToNotes } from '../../utils/chordVoicings'

const INSTRUMENTS = {
  piano: {
    name: 'Grand Piano',
    type: 'sampler',
    options: {
      urls: {
        A0: 'A0.mp3', C1: 'C1.mp3', 'D#1': 'Ds1.mp3', 'F#1': 'Fs1.mp3',
        A1: 'A1.mp3', C2: 'C2.mp3', 'D#2': 'Ds2.mp3', 'F#2': 'Fs2.mp3',
        A2: 'A2.mp3', C3: 'C3.mp3', 'D#3': 'Ds3.mp3', 'F#3': 'Fs3.mp3',
        A3: 'A3.mp3', C4: 'C4.mp3', 'D#4': 'Ds4.mp3', 'F#4': 'Fs4.mp3',
        A4: 'A4.mp3', C5: 'C5.mp3', 'D#5': 'Ds5.mp3', 'F#5': 'Fs5.mp3',
        A5: 'A5.mp3', C6: 'C6.mp3', 'D#6': 'Ds6.mp3', 'F#6': 'Fs6.mp3',
        A6: 'A6.mp3', C7: 'C7.mp3', 'D#7': 'Ds7.mp3', 'F#7': 'Fs7.mp3',
        A7: 'A7.mp3', C8: 'C8.mp3'
      },
      release: 1,
      baseUrl: 'https://tonejs.github.io/audio/salamander/'
    }
  },
  epiano: {
    name: 'Electric Piano',
    type: 'synth',
    options: {
      oscillator: { type: 'fmsine', modulationType: 'sine', modulationIndex: 12 },
      envelope: { attack: 0.001, decay: 2, sustain: 0.1, release: 2 }
    }
  },
  guitar: {
    name: 'Jazz Guitar',
    type: 'synth',
    options: {
      oscillator: { type: 'triangle' },
      envelope: { attack: 0.008, decay: 0.5, sustain: 0.2, release: 1.5 }
    }
  }
}

export default function PlaybackControls({ progression }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentChord, setCurrentChord] = useState(null)
  const [tempo, setTempo] = useState(120)
  const [instrument, setInstrument] = useState('piano')
  const [loading, setLoading] = useState(true)
  const instrumentRef = useRef(null)

  // Initialize instrument
  useEffect(() => {
    const initInstrument = async () => {
      if (instrumentRef.current) {
        instrumentRef.current.dispose()
      }

      const config = INSTRUMENTS[instrument]
      if (config.type === 'sampler') {
        instrumentRef.current = new Tone.Sampler(config.options).toDestination()
        await Tone.loaded()
      } else {
        instrumentRef.current = new Tone.PolySynth(Tone.Synth, config.options).toDestination()
      }
      setLoading(false)
    }

    setLoading(true)
    initInstrument()

    return () => {
      if (instrumentRef.current) {
        instrumentRef.current.dispose()
      }
      Tone.Transport.stop()
      Tone.Transport.cancel()
    }
  }, [instrument])

  const playProgression = async () => {
    if (!progression?.sections || !instrumentRef.current) return

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
            // Use override symbol if present, otherwise use detected symbol
            const chordSymbol = chord.chord_symbol_override || chord.chord_symbol
            const inversion = chord.inversion || 0
            const octave = chord.playback_octave || 3
            
            const chordNotes = chordToNotes(chordSymbol, octave, inversion)
            Tone.Transport.schedule((scheduleTime) => {
              instrumentRef.current.triggerAttackRelease(chordNotes, '2n', scheduleTime)
              setCurrentChord(chordSymbol)
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

  return (
    <div className="flex items-center gap-4 flex-wrap">
      <button
        onClick={isPlaying ? stopPlayback : playProgression}
        className={isPlaying ? 'btn-secondary' : 'btn-primary'}
        disabled={!progression?.sections?.length || loading}
      >
        {loading ? '⏳ Loading...' : isPlaying ? '⏹ Stop' : '▶ Play'}
      </button>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">Instrument:</label>
        <select
          value={instrument}
          onChange={(e) => setInstrument(e.target.value)}
          disabled={isPlaying}
          className="px-3 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {Object.entries(INSTRUMENTS).map(([key, config]) => (
            <option key={key} value={key}>{config.name}</option>
          ))}
        </select>
      </div>

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
