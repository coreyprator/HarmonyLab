import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import PlaybackControls from '../components/playback/PlaybackControls'
import ChordEditModal from '../components/chords/ChordEditModal'

export default function SongPage() {
  const { id } = useParams()
  const [song, setSong] = useState(null)
  const [progression, setProgression] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [chordToEdit, setChordToEdit] = useState(null)

  useEffect(() => {
    loadSong()
  }, [id])

  const loadSong = async () => {
    try {
      setLoading(true)
      const [songData, progressionData] = await Promise.all([
        api.getSong(id),
        api.getSongProgression(id)
      ])
      setSong(songData)
      setProgression(progressionData)
      setError(null)
    } catch (err) {
      setError('Failed to load song details.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const startEditChord = (chord) => {
    console.log('Editing chord:', chord)
    setChordToEdit(chord)
  }

  const saveChordEdit = async (chordId, updates) => {
    try {
      console.log('Updating chord:', chordId, 'with updates:', updates)
      await api.updateChord(chordId, updates)
      // Refresh progression data
      const progressionData = await api.getSongProgression(id)
      setProgression(progressionData)
      setChordToEdit(null)
    } catch (err) {
      console.error('Failed to update chord:', err)
      alert(`Failed to update chord: ${err.message}`)
    }
  }

  const cancelEdit = () => {
    setChordToEdit(null)
  }

  const midiNoteToName = (midiNote) => {
    const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    const octave = Math.floor(midiNote / 12) - 1
    const noteName = noteNames[midiNote % 12]
    return `${noteName}${octave}`
  }

  const parseIntervals = (midiNotes) => {
    if (!midiNotes || midiNotes.length === 0) return 'No notes'
    const notes = typeof midiNotes === 'string' ? JSON.parse(midiNotes) : midiNotes
    if (notes.length === 0) return 'No notes'
    
    const root = notes[0]
    const intervals = notes.map(note => (note - root) % 12)
    return intervals.join(', ') + ' semitones from root'
  }

  const getRootNote = (midiNotes) => {
    if (!midiNotes) return 'Unknown'
    const notes = typeof midiNotes === 'string' ? JSON.parse(midiNotes) : midiNotes
    if (notes.length === 0) return 'Unknown'
    return midiNoteToName(notes[0])
  }

  const getMidiNotesList = (midiNotes) => {
    if (!midiNotes) return 'No MIDI data'
    try {
      const notes = typeof midiNotes === 'string' ? JSON.parse(midiNotes) : midiNotes
      if (notes.length === 0) return 'No notes recorded'
      return notes.map(n => midiNoteToName(n)).join(', ')
    } catch {
      return 'Invalid data'
    }
  }

  if (loading) return <div className="text-center py-12">Loading...</div>
  if (error) return <div className="text-center py-12 text-error">{error}</div>
  if (!song) return <div className="text-center py-12">Song not found.</div>

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-primary hover:underline mb-4 inline-block">
          ← Back to Songs
        </Link>
        
        <h1 className="text-4xl font-bold mb-2">{song.title}</h1>
        <p className="text-gray-600 text-lg">
          {song.composer} {song.genre && `• ${song.genre}`}
        </p>
        
        <div className="mt-4">
          <div className="flex gap-4 mb-4">
            <Link to={`/quiz/${id}`} className="btn-primary">
              Start Quiz
            </Link>
          </div>
          <PlaybackControls progression={progression} />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Chord Progression</h2>
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded transition"
          >
            {showAnalysis ? '📊 Hide Analysis' : '🔍 Show Analysis'}
          </button>
        </div>
        
        {progression && progression.sections ? (
          progression.sections.map(section => (
            <div key={section.section_id} className="mb-6">
              <h3 className="text-xl font-semibold mb-3">
                {section.section_name} {section.repeat_count > 1 && `(×${section.repeat_count})`}
              </h3>
              
              {showAnalysis ? (
                <div className="space-y-2">
                  {section.measures.map(measure => (
                    <div key={measure.measure_id} className="border border-gray-200 rounded p-3">
                      <div className="flex items-start gap-4">
                        <div className="font-semibold text-gray-600 min-w-[80px]">
                          Measure {measure.measure_number}
                        </div>
                        <div className="flex-1 space-y-2">
                          {measure.chords.length > 0 ? (
                            measure.chords.map((chord, idx) => (
                              <div key={idx} className="bg-gray-50 p-3 rounded">
                                <div className="flex items-center gap-3 mb-2">
                                  <span className="text-xl font-bold text-primary">
                                    {chord.chord_symbol_override || chord.chord_symbol}
                                  </span>
                                  <span className="text-sm text-gray-500">
                                    Beat {chord.beat_position || 1}
                                  </span>
                                  <button
                                    onClick={() => startEditChord(chord)}
                                    className="text-blue-600 hover:text-blue-800 text-sm"
                                  >
                                    ✏️ Edit
                                  </button>
                                </div>
                                <div className="text-sm text-gray-600">
                                  <strong>Analysis:</strong>
                                  <div className="mt-1 space-y-1 ml-3">
                                    <div>• <strong>Method:</strong> {chord.midi_notes ? 'MIDI Analysis' : 'Manual Override'}</div>
                                    <div>• <strong>Root Note:</strong> {getRootNote(chord.midi_notes)}</div>
                                    <div>• <strong>Intervals:</strong> {parseIntervals(chord.midi_notes)}</div>
                                    <div>• <strong>Notes in analysis:</strong> {getMidiNotesList(chord.midi_notes)}</div>
                                  </div>
                                </div>
                              </div>
                            ))
                          ) : (
                            <span className="text-gray-400">No chords</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-1">
                  {section.measures.map(measure => (
                    <div key={measure.measure_id} className="chord-cell">
                      {measure.chords.length > 0 ? (
                        measure.chords.map((chord, idx) => (
                          <span key={idx} className="block">
                            {chord.chord_symbol_override || chord.chord_symbol}
                          </span>
                        ))
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <p className="text-gray-500">No chord progression available.</p>
        )}
      </div>
      
      {/* Chord Edit Modal */}
      {chordToEdit && (
        <ChordEditModal
          chord={chordToEdit}
          onSave={(updates) => saveChordEdit(chordToEdit.id, updates)}
          onCancel={cancelEdit}
        />
      )}
    </div>
  )
}
