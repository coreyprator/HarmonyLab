import { useState, useEffect } from 'react'
import * as Tone from 'tone'
import { chordToNotes, getInversionLabel } from '../../utils/chordVoicings'

const ROOT_NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
const CHORD_QUALITIES = [
  { value: '', label: 'Major' },
  { value: 'm', label: 'Minor' },
  { value: 'dim', label: 'Diminished' },
  { value: 'aug', label: 'Augmented' },
  { value: 'Maj7', label: 'Major 7th' },
  { value: 'm7', label: 'Minor 7th' },
  { value: '7', label: 'Dominant 7th' },
  { value: 'ø7', label: 'Half Diminished' },
  { value: 'dim7', label: 'Diminished 7th' },
  { value: 'mMaj7', label: 'Minor Major 7th' },
  { value: '6', label: 'Major 6th' },
  { value: 'm6', label: 'Minor 6th' },
  { value: '9', label: 'Dominant 9th' },
  { value: 'Maj9', label: 'Major 9th' },
  { value: 'm9', label: 'Minor 9th' },
  { value: '11', label: 'Dominant 11th' },
  { value: 'm11', label: 'Minor 11th' },
  { value: '13', label: 'Dominant 13th' },
  { value: 'Maj13', label: 'Major 13th' },
  { value: 'sus4', label: 'Suspended 4th' },
  { value: 'sus2', label: 'Suspended 2nd' },
  { value: '7sus4', label: 'Dominant 7sus4' },
  { value: '7b9', label: 'Dominant 7♭9' },
  { value: '7#9', label: 'Dominant 7♯9' },
  { value: '7alt', label: 'Altered Dominant' },
]

const INVERSIONS = [
  { value: 0, label: 'Root position' },
  { value: 1, label: '1st inversion' },
  { value: 2, label: '2nd inversion' },
  { value: 3, label: '3rd inversion' },
]

const OCTAVES = [1, 2, 3, 4, 5]

export default function ChordEditModal({ chord, onSave, onCancel }) {
  // Parse existing chord symbol
  const parseChord = (symbol) => {
    const match = symbol.match(/^([A-G][#b]?)(.*)$/)
    return match ? { root: match[1], quality: match[2] || '' } : { root: 'C', quality: '' }
  }
  
  const initial = parseChord(chord.chord_symbol_override || chord.chord_symbol)
  
  const [root, setRoot] = useState(initial.root)
  const [quality, setQuality] = useState(initial.quality)
  const [inversion, setInversion] = useState(chord.inversion || 0)
  const [octave, setOctave] = useState(chord.playback_octave || 3)
  const [sampler, setSampler] = useState(null)
  
  const chordSymbol = `${root}${quality}`
  const previewNotes = chordToNotes(chordSymbol, octave, inversion)
  const inversionLabel = getInversionLabel(chordSymbol, inversion)
  
  useEffect(() => {
    // Load piano sampler for preview
    const loadSampler = async () => {
      const s = new Tone.Sampler({
        urls: {
          A0: 'A0.mp3', C1: 'C1.mp3', 'D#1': 'Ds1.mp3', 'F#1': 'Fs1.mp3',
          A1: 'A1.mp3', C2: 'C2.mp3', 'D#2': 'Ds2.mp3', 'F#2': 'Fs2.mp3',
          A2: 'A2.mp3', C3: 'C3.mp3', 'D#3': 'Ds3.mp3', 'F#3': 'Fs3.mp3',
          A3: 'A3.mp3', C4: 'C4.mp3', 'D#4': 'Ds4.mp3', 'F#4': 'Fs4.mp3',
          A4: 'A4.mp3', C5: 'C5.mp3', 'D#5': 'Ds5.mp3', 'F#5': 'Fs5.mp3',
          A5: 'A5.mp3', C6: 'C6.mp3', 'D#6': 'Ds6.mp3', 'F#6': 'Fs6.mp3',
          A6: 'A6.mp3', C7: 'C7.mp3', 'D#7': 'Ds7.mp3', 'F#7': 'Fs7.mp3',
        },
        release: 1,
        baseUrl: 'https://tonejs.github.io/audio/salamander/'
      }).toDestination()
      
      await Tone.loaded()
      setSampler(s)
    }
    
    loadSampler()
    
    return () => {
      if (sampler) {
        sampler.dispose()
      }
    }
  }, [])
  
  const handleSave = () => {
    onSave({
      chord_symbol_override: chordSymbol !== chord.chord_symbol ? chordSymbol : null,
      inversion: inversion,
      playback_octave: octave,
      is_manual_edit: true,
      confidence: 1.0  // Manual edits are 100% confidence
    })
  }
  
  const playPreview = async () => {
    if (!sampler) return
    await Tone.start()
    sampler.triggerAttackRelease(previewNotes, '2n')
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-bold mb-4">
          Edit Chord: Measure {chord.measure_number}, Beat {chord.beat_position}
        </h3>
        
        {/* Chord Symbol */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Chord Symbol</label>
          <div className="flex gap-2 items-center">
            <select 
              value={root} 
              onChange={(e) => setRoot(e.target.value)}
              className="border rounded px-3 py-2 flex-1"
            >
              {ROOT_NOTES.map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <select 
              value={quality} 
              onChange={(e) => setQuality(e.target.value)}
              className="border rounded px-3 py-2 flex-1"
            >
              {CHORD_QUALITIES.map(q => (
                <option key={q.value} value={q.value}>{q.label}</option>
              ))}
            </select>
          </div>
          <div className="mt-2 text-center">
            <span className="text-2xl font-mono font-bold text-primary">{chordSymbol}</span>
          </div>
        </div>
        
        {/* Playback Settings */}
        <div className="border-t pt-4 mb-4">
          <h4 className="font-semibold mb-3 text-gray-700">Playback Settings</h4>
          
          {/* Inversion */}
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Inversion</label>
            <select 
              value={inversion} 
              onChange={(e) => setInversion(Number(e.target.value))}
              className="border rounded px-3 py-2 w-full"
            >
              {INVERSIONS.map(inv => (
                <option key={inv.value} value={inv.value}>{inv.label}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">{inversionLabel}</p>
          </div>
          
          {/* Octave */}
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Octave</label>
            <select 
              value={octave} 
              onChange={(e) => setOctave(Number(e.target.value))}
              className="border rounded px-3 py-2 w-full"
            >
              {OCTAVES.map(o => (
                <option key={o} value={o}>Octave {o}</option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Preview */}
        <div className="mb-4 p-3 bg-gray-100 rounded">
          <div className="flex justify-between items-center">
            <div>
              <div className="text-xs text-gray-500 mb-1">Preview Notes:</div>
              <div className="text-sm font-mono">{previewNotes.join(', ')}</div>
            </div>
            <button 
              onClick={playPreview}
              disabled={!sampler}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
            >
              ▶ Play
            </button>
          </div>
        </div>
        
        {/* Original (if different) */}
        {(chord.chord_symbol !== chordSymbol || chord.is_manual_edit) && (
          <div className="mb-4 text-sm p-2 bg-yellow-50 border border-yellow-200 rounded">
            <div className="font-medium text-yellow-800">Original:</div>
            <div className="text-gray-700">
              {chord.chord_symbol}
              {chord.confidence && ` (${Math.round(chord.confidence * 100)}% confidence)`}
            </div>
          </div>
        )}
        
        {/* Actions */}
        <div className="flex justify-end gap-2 border-t pt-4">
          <button 
            onClick={onCancel}
            className="px-4 py-2 border rounded hover:bg-gray-100"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}
