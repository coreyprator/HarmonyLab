import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function HomePage() {
  const [songs, setSongs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [genreFilter, setGenreFilter] = useState('all')
  const [sortBy, setSortBy] = useState('title')
  const [editingSongId, setEditingSongId] = useState(null)
  const [editTitle, setEditTitle] = useState('')

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

  const startEdit = (song, e) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingSongId(song.id || song.song_id)
    setEditTitle(song.title)
  }

  const cancelEdit = () => {
    setEditingSongId(null)
    setEditTitle('')
  }

  const saveEdit = async (songId, e) => {
    e.preventDefault()
    e.stopPropagation()
    
    try {
      await api.updateSong(songId, { title: editTitle })
      setSongs(songs.map(s => 
        (s.id || s.song_id) === songId ? { ...s, title: editTitle } : s
      ))
      setEditingSongId(null)
      setEditTitle('')
    } catch (err) {
      alert('Failed to update song')
      console.error(err)
    }
  }

  const genres = ['all', ...new Set(songs.map(s => s.genre).filter(Boolean))]
  
  const filteredSongs = songs
    .filter(song => {
      const matchesSearch = song.title.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesGenre = genreFilter === 'all' || song.genre === genreFilter
      return matchesSearch && matchesGenre
    })
    .sort((a, b) => {
      if (sortBy === 'title') {
        return a.title.localeCompare(b.title)
      } else if (sortBy === 'date') {
        return new Date(b.created_at || 0) - new Date(a.created_at || 0)
      } else if (sortBy === 'genre') {
        return (a.genre || '').localeCompare(b.genre || '')
      }
      return 0
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

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="title">Sort by Title</option>
            <option value="date">Sort by Date</option>
            <option value="genre">Sort by Genre</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        {filteredSongs.length === 0 ? (
          <p className="text-center py-12 text-gray-500">No songs found.</p>
        ) : (
          filteredSongs.map(song => {
            const songId = song.id || song.song_id
            const isEditing = editingSongId === songId
            
            return (
              <div
                key={songId}
                className="border-b border-gray-200 last:border-b-0 hover:bg-gray-50 transition flex items-center"
              >
                {isEditing ? (
                  <div className="flex-1 p-4 flex items-center gap-4">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
                      autoFocus
                    />
                    <button
                      onClick={(e) => saveEdit(songId, e)}
                      className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition"
                    >
                      ✓ Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-3 py-1 bg-gray-300 rounded hover:bg-gray-400 transition"
                    >
                      ✕ Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <Link
                      to={`/songs/${songId}`}
                      className="flex-1 p-4 flex items-center justify-between"
                    >
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold">{song.title}</h3>
                        <p className="text-gray-600 text-sm">
                          {song.composer}
                          {song.created_at && (
                            <span className="ml-2 text-gray-400">
                              • {new Date(song.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="px-3 py-1 bg-gray-100 rounded text-sm">
                          {song.genre || 'Standard'}
                        </span>
                        <span className="text-2xl">→</span>
                      </div>
                    </Link>
                    <button
                      onClick={(e) => startEdit(song, e)}
                      className="px-3 py-1 mx-2 text-blue-600 hover:bg-blue-50 rounded transition"
                      title="Edit song"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={(e) => handleDelete(songId, song.title, e)}
                      className="px-3 py-1 mx-2 text-red-600 hover:bg-red-50 rounded transition"
                      title="Delete song"
                    >
                      🗑️
                    </button>
                  </>
                )}
              </div>
            )
          })
        )}
      </div>

      <p className="text-gray-600 mt-4">Showing {filteredSongs.length} songs</p>
    </div>
  )
}
