import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import SongPage from './pages/SongPage'
import QuizPage from './pages/QuizPage'
import ProgressPage from './pages/ProgressPage'
import ImportPage from './pages/ImportPage'
import MidiAuditPage from './pages/MidiAuditPage'
import { AudioProvider } from './context/AudioContext'

function App() {
  return (
    <AudioProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/songs/:id" element={<SongPage />} />
            <Route path="/quiz/:id" element={<QuizPage />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/import/audit" element={<MidiAuditPage />} />
          </Routes>
        </Layout>
      </Router>
    </AudioProvider>
  )
}

export default App
