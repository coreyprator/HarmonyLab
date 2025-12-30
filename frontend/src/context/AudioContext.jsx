import React, { createContext, useContext, useEffect, useState } from 'react'
import * as Tone from 'tone'

const AudioContext = createContext()

export function AudioProvider({ children }) {
  const [piano, setPiano] = useState(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // Initialize Tone.js piano sampler
    const sampler = new Tone.Sampler({
      urls: {
        A0: "A0.mp3",
        C1: "C1.mp3",
        "D#1": "Ds1.mp3",
        "F#1": "Fs1.mp3",
        A1: "A1.mp3",
        C2: "C2.mp3",
        "D#2": "Ds2.mp3",
        "F#2": "Fs2.mp3",
        A2: "A2.mp3",
        C3: "C3.mp3",
        "D#3": "Ds3.mp3",
        "F#3": "Fs3.mp3",
        A3: "A3.mp3",
        C4: "C4.mp3",
        "D#4": "Ds4.mp3",
        "F#4": "Fs4.mp3",
        A4: "A4.mp3",
        C5: "C5.mp3",
        "D#5": "Ds5.mp3",
        "F#5": "Fs5.mp3",
        A5: "A5.mp3",
        C6: "C6.mp3",
        "D#6": "Ds6.mp3",
        "F#6": "Fs6.mp3",
        A6: "A6.mp3",
        C7: "C7.mp3",
        "D#7": "Ds7.mp3",
        "F#7": "Fs7.mp3",
        A7: "A7.mp3",
        C8: "C8.mp3",
      },
      baseUrl: "https://tonejs.github.io/audio/salamander/",
      onload: () => {
        setIsLoaded(true)
      }
    }).toDestination()

    setPiano(sampler)

    return () => {
      sampler.dispose()
    }
  }, [])

  const playChord = async (chordSymbol) => {
    if (!piano || !isLoaded) return

    await Tone.start()
    const notes = parseChordToNotes(chordSymbol)
    piano.triggerAttackRelease(notes, "2n")
  }

  const playProgression = async (chords, tempo = 120, onChordChange = null) => {
    if (!piano || !isLoaded) return

    await Tone.start()
    Tone.Transport.bpm.value = tempo

    chords.forEach((chord, index) => {
      Tone.Transport.schedule((time) => {
        const notes = parseChordToNotes(chord.symbol)
        piano.triggerAttackRelease(notes, "2n", time)
        if (onChordChange) {
          onChordChange(index)
        }
      }, `${index * 2}:0:0`)
    })

    Tone.Transport.start()

    return () => {
      Tone.Transport.stop()
      Tone.Transport.cancel()
    }
  }

  return (
    <AudioContext.Provider value={{ piano, isLoaded, playChord, playProgression }}>
      {children}
    </AudioContext.Provider>
  )
}

export function useAudio() {
  const context = useContext(AudioContext)
  if (!context) {
    throw new Error('useAudio must be used within AudioProvider')
  }
  return context
}

// Helper function to parse chord symbols to notes
function parseChordToNotes(chordSymbol) {
  // Simplified chord parsing - expand this based on your chord vocabulary
  const rootMatch = chordSymbol.match(/^([A-G][b#]?)/)
  if (!rootMatch) return ['C4', 'E4', 'G4'] // Default to C major
  
  const root = rootMatch[1]
  const quality = chordSymbol.slice(root.length)
  
  // Map root notes to MIDI numbers (C4 = middle C = 60)
  const noteMap = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
    'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
  }
  
  const rootMidi = 60 + (noteMap[root] || 0) // Middle C + offset
  
  // Basic chord voicings
  let intervals = [0, 4, 7] // Major triad
  if (quality.includes('m7')) intervals = [0, 3, 7, 10]
  else if (quality.includes('7')) intervals = [0, 4, 7, 10]
  else if (quality.includes('Maj7')) intervals = [0, 4, 7, 11]
  else if (quality.includes('m')) intervals = [0, 3, 7]
  
  return intervals.map(i => Tone.Frequency(rootMidi + i, 'midi').toNote())
}
