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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <strong>Filename:</strong> {audit.filename}
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
                <strong>Ticks per Beat:</strong> {audit.ticks_per_beat}
              </div>
              <div>
                <strong>Total Beats:</strong> {audit.total_beats.toFixed(2)}
              </div>
            </div>

            {audit.parser_issues.length > 0 && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
                <strong className="text-red-800">Parser Issues:</strong>
                <ul className="list-disc ml-6 mt-2">
                  {audit.parser_issues.map((issue, idx) => (
                    <li key={idx} className="text-red-700">{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Tracks Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">Tracks Analysis</h2>
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Track #</th>
                  <th className="text-left p-2">Name</th>
                  <th className="text-right p-2">Total Events</th>
                  <th className="text-right p-2">Note Events</th>
                  <th className="text-right p-2">Max Polyphony</th>
                </tr>
              </thead>
              <tbody>
                {audit.tracks_analyzed.map((track) => (
                  <tr key={track.track_number} className="border-b">
                    <td className="p-2">{track.track_number}</td>
                    <td className="p-2">{track.track_name}</td>
                    <td className="text-right p-2">{track.total_events}</td>
                    <td className="text-right p-2">{track.note_events}</td>
                    <td className="text-right p-2 font-bold">{track.polyphony}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Measure by Measure Analysis */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">
              Measure-by-Measure Analysis ({audit.measures.length} measures)
            </h2>
            <div className="space-y-4">
              {audit.measures.filter(m => m.all_notes_played.length > 0).map((measure) => (
                <div key={measure.measure_number} className="border border-gray-200 rounded p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-bold">Measure {measure.measure_number}</h3>
                    <span className="text-sm text-gray-500">
                      Beats {measure.start_beat.toFixed(1)} - {measure.end_beat.toFixed(1)}
                    </span>
                  </div>

                  <div className="mb-3">
                    <strong>All Notes Played:</strong>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {measure.all_notes_played.map((note, idx) => (
                        <span key={idx} className="px-2 py-1 bg-blue-100 rounded text-sm">
                          {note}
                        </span>
                      ))}
                    </div>
                  </div>

                  {measure.simultaneous_note_groups.length > 0 && (
                    <div className="mb-3">
                      <strong>Simultaneous Note Groups:</strong>
                      <div className="mt-1 space-y-1">
                        {measure.simultaneous_note_groups.map((group, idx) => (
                          <div key={idx} className="text-sm bg-gray-50 p-2 rounded">
                            <span className="font-medium">Beat {group.beat}:</span>{' '}
                            {group.notes.join(', ')}
                            <span className="text-gray-500 ml-2">
                              (MIDI: {group.midi_notes.join(', ')})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <details className="mt-2">
                    <summary className="cursor-pointer text-sm text-primary hover:underline">
                      Show All MIDI Events ({measure.events.length})
                    </summary>
                    <div className="mt-2 max-h-60 overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left p-1">Time (ticks)</th>
                            <th className="text-left p-1">Beat</th>
                            <th className="text-left p-1">Event</th>
                            <th className="text-left p-1">Note</th>
                            <th className="text-left p-1">Velocity</th>
                          </tr>
                        </thead>
                        <tbody>
                          {measure.events.map((event, idx) => (
                            <tr key={idx} className="border-b">
                              <td className="p-1">{event.time_ticks}</td>
                              <td className="p-1">{event.beat_in_measure}</td>
                              <td className="p-1">{event.event_type}</td>
                              <td className="p-1">{event.note_name}</td>
                              <td className="p-1">{event.velocity}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
