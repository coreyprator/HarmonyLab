const API_URL = import.meta.env.VITE_API_URL || 'https://harmonylab-wmrla7fhwa-uc.a.run.app'

export async function apiClient(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      let errorMessage = 'API request failed'
      try {
        const error = await response.json()
        errorMessage = error.detail || error.message || errorMessage
      } catch {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`
      }
      throw new Error(errorMessage)
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
      return null
    }

    return await response.json()
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

// API methods
export const api = {
  // Songs
  getSongs: () => apiClient('/api/songs'),
  getSong: (id) => apiClient(`/api/songs/${id}`),
  getSongProgression: (id) => apiClient(`/api/songs/${id}/progression`),
  createSong: (data) => apiClient('/api/songs', { method: 'POST', body: JSON.stringify(data) }),
  updateSong: (id, data) => apiClient(`/api/songs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSong: (id) => apiClient(`/api/songs/${id}`, { method: 'DELETE' }),

  // Vocabulary
  getChords: () => apiClient('/api/vocabulary/chords'),
  
  // Quiz
  generateQuiz: (songId, mode, difficulty) => 
    apiClient(`/api/quiz/generate/${songId}?mode=${mode}&difficulty=${difficulty}`),
  submitQuiz: (data) => apiClient('/api/quiz/submit', { method: 'POST', body: JSON.stringify(data) }),
  
  // Progress
  getProgress: () => apiClient('/api/progress'),
  getStats: () => apiClient('/api/progress/stats'),
  
  // Import
  importMidi: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetch(`${API_URL}/api/imports/midi`, {
      method: 'POST',
      body: formData,
    }).then(res => res.json())
  },
}
