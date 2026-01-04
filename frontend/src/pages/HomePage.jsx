import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function HomePage() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [genreFilter, setGenreFilter] = useState('all')

  useEffect(() => {
    loadSongs()
  }, [])

  const loadSongs = async () => {
    try {
      setLoading(true)
      const data = await api.getSongs()
      setSongs(data)
      setError(null)
    } catch (err) {
      setError('Failed to load songs. Please try again later.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (songId, songTitle, e) => {
    e.preventDefault() // Prevent navigation to song detail
    e.stopPropagation()
    
    if (!confirm(`Delete "${songTitle}"?`)) return
    
    try {
      await api.deleteSong(songId)
      setSongs(songs.filter(s => s.id !== songId))
    } catch (err) {
      alert('Failed to delete song')
      console.error(err)
    }
  }

  const genres = ['all', ...new Set(songs.map(s => s.genre).filter(Boolean))]
  
  const filteredSongs = songs.filter(song => {
    const matchesSearch = song.title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesGenre = genreFilter === 'all' || song.genre === genreFilter
    return matchesSearch && matchesGenre
  })

  if (loading) {
    return <div className="text-center py-12">Loading songs...</div>
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-error mb-4">{error}</p>
        <button onClick={loadSongs} className="btn-primary">Retry</button>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-6">Song Library</h1>
        
        <div className="flex gap-4 mb-6">
          <input
            type="text"
            placeholder="Search songs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
          />
          
          <select
            value={genreFilter}
            onChange={(e) => setGenreFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {genres.map(genre => (
              <option key={genre} value={genre}>
                {genre === 'all' ? 'All Genres' : genre}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        {filteredSongs.length === 0 ? (
          <p className="text-center py-12 text-gray-500">No songs found.</p>
        ) : (
          filteredSongs.map(song => (
            <div
              key={song.id || song.song_id}
              className="border-b border-gray-200 last:border-b-0 hover:bg-gray-50 transition flex items-center"
            >
              <Link
                to={`/songs/${song.id || song.song_id}`}
                className="flex-1 p-4 flex items-center justify-between"
              >
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{song.title}</h3>
                  <p className="text-gray-600 text-sm">{song.composer}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="px-3 py-1 bg-gray-100 rounded text-sm">
                    {song.genre || 'Standard'}
                  </span>
                  <span className="text-2xl">→</span>
                </div>
              </Link>
              <button
                onClick={(e) => handleDelete(song.id || song.song_id, song.title, e)}
                className="px-3 py-1 mx-2 text-red-600 hover:bg-red-50 rounded transition"
                title="Delete song"
              >
                🗑️
              </button>
            </div>
          ))
        )}
      </div>

      <p className="text-gray-600 mt-4">Showing {filteredSongs.length} songs</p>
    </div>
  )
}
