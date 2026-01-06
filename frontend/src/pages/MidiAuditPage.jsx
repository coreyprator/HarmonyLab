import { useState } from 'react'
import { Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'https://harmonylab-wmrla7fhwa-uc.a.run.app'

export default function MidiAuditPage() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [audit, setAudit] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleAudit = async () => {
    if (!file) {
      setError('Please select a MIDI file')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_URL}/api/v1/imports/midi/audit`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to audit MIDI file')
      }

      const data = await response.json()
      setAudit(data)
    } catch (err) {
      setError(err.message)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto">
      <Link to="/import" className="text-primary hover:underline mb-4 inline-block">
        ← Back to Import
      </Link>

      <h1 className="text-4xl font-bold mb-8">MIDI Parser Audit</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Upload MIDI File for Analysis</h2>
        <div className="flex gap-4">
          <input
            type="file"
            accept=".mid,.midi"
            onChange={handleFileChange}
            className="flex-1 px-4 py-2 border border-gray-300 rounded"
          />
          <button
            onClick={handleAudit}
            disabled={loading || !file}
            className="btn-primary"
          >
            {loading ? 'Analyzing...' : 'Audit File'}
          </button>
        </div>
        {error && (
          <p className="text-red-600 mt-2">{error}</p>
        )}
      </div>

      {audit && (
        <div className="space-y-6">
          {/* File Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">File Information</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <strong>Filename:</strong> {audit.filename?.split('/').pop() || 'Unknown'}
              </div>
              <div>
                <strong>Tempo:</strong> {audit.tempo} BPM
              </div>
              <div>
                <strong>Time Signature:</strong> {audit.time_signature}
              </div>
              <div>
                <strong>Total Measures:</strong> {audit.total_measures}
              </div>
              <div>
                <strong>Ticks/Beat:</strong> {audit.ticks_per_beat}
              </div>
              <div>
                <strong>Chords Detected:</strong> {audit.total_chords_detected}
              </div>
            </div>
          </div>

          {/* Tracks Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">Tracks Analysis</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">Track #</th>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-left">Note Events</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.tracks?.map((track) => (
                    <tr key={track.index} className="border-t">
                      <td className="px-4 py-2">{track.index}</td>
                      <td className="px-4 py-2">{track.name}</td>
                      <td className="px-4 py-2">{track.note_events}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Chord Progression */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">
              Chord Progression by Measure ({Object.keys(audit.measures || {}).length} measures with chords)
            </h2>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {Object.entries(audit.measures || {})
                .sort(([a], [b]) => parseInt(a) - parseInt(b))
                .map(([measureNum, chords]) => (
                  <div key={measureNum} className="border-l-4 border-primary pl-4">
                    <h3 className="font-bold text-lg mb-2">Measure {measureNum}</h3>
                    {chords.map((chord, idx) => (
                      <div key={idx} className="mb-3 bg-gray-50 p-3 rounded">
                        <div className="flex items-baseline gap-3 mb-1">
                          <span className="font-semibold text-primary">Beat {chord.beat}:</span>
                          <span className="text-xl font-bold">{chord.symbol}</span>
                          {chord.confidence < 1.0 && (
                            <span className="text-sm text-orange-600">
                              ({Math.round(chord.confidence * 100)}% confidence)
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600">
                          <span className="font-medium">Notes:</span> {chord.notes?.join(', ')}
                        </div>
                        <div className="text-xs text-gray-500">
                          MIDI: [{chord.midi_notes?.join(', ')}]
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
