import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import PlaybackControls from '../components/playback/PlaybackControls'

export default function SongPage() {
  const { id } = useParams()
  const [song, setSong] = useState(null)
  const [progression, setProgression] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAnalysis, setShowAnalysis] = useState(false)

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

  if (loading) return <div className="text-center py-12">Loading...</div>
  if (error) return <div className="text-center py-12 text-error">{error}</div>
  if (!song) return <div className="text-center py-12">Song not found.</div>

  const getChordTemplate = (symbol) => {
    if (symbol.includes('Maj7')) return 'Major 7th (root, M3, P5, M7)'
    if (symbol.includes('m7')) return 'Minor 7th (root, m3, P5, m7)'
    if (symbol.includes('7') && !symbol.includes('Maj')) return 'Dominant 7th (root, M3, P5, m7)'
    if (symbol.includes('m') && !symbol.includes('Maj')) return 'Minor triad (root, m3, P5)'
    if (symbol.includes('dim')) return 'Diminished (root, m3, d5)'
    if (symbol.includes('aug')) return 'Augmented (root, M3, A5)'
    return 'Major triad (root, M3, P5)'
  }

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
                                    {chord.chord_symbol}
                                  </span>
                                  <span className="text-sm text-gray-500">
                                    Beat {chord.beat_position || 1}
                                  </span>
                                </div>
                                <div className="text-sm text-gray-600">
                                  <strong>Parsing Algorithm:</strong>
                                  <div className="mt-1 space-y-1 ml-3">
                                    <div>• <strong>Method:</strong> Template matching from MIDI note intervals</div>
                                    <div>• <strong>Root Detection:</strong> Lowest MIDI note in chord voicing</div>
                                    <div>• <strong>Intervals:</strong> {getChordTemplate(chord.chord_symbol)}</div>
                                    <div>• <strong>Source:</strong> Extracted from simultaneous notes in MIDI track</div>
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
                            {chord.chord_symbol}
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
    </div>
  )
}
