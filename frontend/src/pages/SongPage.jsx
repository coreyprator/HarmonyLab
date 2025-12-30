import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'

export default function SongPage() {
  const { id } = useParams()
  const [song, setSong] = useState(null)
  const [progression, setProgression] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
        
        <div className="mt-4 flex gap-4">
          <Link to={`/quiz/${id}`} className="btn-primary">
            Start Quiz
          </Link>
          <button className="btn-secondary">▶ Play</button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Chord Progression</h2>
        
        {progression && progression.sections ? (
          progression.sections.map(section => (
            <div key={section.section_id} className="mb-6">
              <h3 className="text-xl font-semibold mb-3">
                {section.section_name} {section.repeat_count > 1 && `(×${section.repeat_count})`}
              </h3>
              
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
            </div>
          ))
        ) : (
          <p className="text-gray-500">No chord progression available.</p>
        )}
      </div>
    </div>
  )
}
