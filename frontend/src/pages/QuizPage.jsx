import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import * as Tone from 'tone'

export default function QuizPage() {
  const { id: songId } = useParams()
  const [song, setSong] = useState(null)
  const [mode, setMode] = useState('recognition') // recognition, progression, interval
  const [difficulty, setDifficulty] = useState('easy')
  const [quizStarted, setQuizStarted] = useState(false)
  const [questions, setQuestions] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [userAnswers, setUserAnswers] = useState([])
  const [score, setScore] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sampler, setSampler] = useState(null)

  useEffect(() => {
    // Load piano sampler
    const initSampler = async () => {
      const s = new Tone.Sampler({
        urls: {
          A0: 'A0.mp3', C1: 'C1.mp3', 'D#1': 'Ds1.mp3', 'F#1': 'Fs1.mp3',
          A1: 'A1.mp3', C2: 'C2.mp3', 'D#2': 'Ds2.mp3', 'F#2': 'Fs2.mp3',
          A2: 'A2.mp3', C3: 'C3.mp3', 'D#3': 'Ds3.mp3', 'F#3': 'Fs3.mp3',
          A3: 'A3.mp3', C4: 'C4.mp3', 'D#4': 'Ds4.mp3', 'F#4': 'Fs4.mp3',
          A4: 'A4.mp3', C5: 'C5.mp3', 'D#5': 'Ds5.mp3', 'F#5': 'Fs5.mp3',
          A5: 'A5.mp3', C6: 'C6.mp3', 'D#6': 'Ds6.mp3', 'F#6': 'Fs6.mp3',
          A6: 'A6.mp3', C7: 'C7.mp3', 'D#7': 'Ds7.mp3', 'F#7': 'Fs7.mp3',
          A7: 'A7.mp3', C8: 'C8.mp3'
        },
        release: 1,
        baseUrl: 'https://tonejs.github.io/audio/salamander/'
      }).toDestination()
      await Tone.loaded()
      setSampler(s)
    }
    initSampler()
    loadSong()
    return () => {
      if (sampler) sampler.dispose()
    }
  }, [songId])

  const loadSong = async () => {
    try {
      const songData = await api.getSong(songId)
      setSong(songData)
    } catch (err) {
      console.error('Failed to load song:', err)
    } finally {
      setLoading(false)
    }
  }

  const startQuiz = async () => {
    try {
      setLoading(true)
      const progression = await api.getSongProgression(songId)
      const generatedQuestions = generateQuestions(progression, mode, difficulty)
      setQuestions(generatedQuestions)
      setQuizStarted(true)
      setCurrentQuestion(0)
      setUserAnswers([])
      setScore(null)
    } catch (err) {
      console.error('Failed to start quiz:', err)
      alert('Failed to start quiz')
    } finally {
      setLoading(false)
    }
  }

  const generateQuestions = (progression, mode, difficulty) => {
    const allChords = []
    progression.sections?.forEach(section => {
      section.measures?.forEach(measure => {
        measure.chords?.forEach(chord => {
          allChords.push({
            symbol: chord.chord_symbol,
            measureNum: measure.measure_number,
            section: section.section_name
          })
        })
      })
    })

    if (allChords.length === 0) return []

    // Generate 10 questions (or fewer if not enough chords)
    const numQuestions = Math.min(10, allChords.length)
    const selectedChords = []
    
    // Randomly select chords
    const shuffled = [...allChords].sort(() => 0.5 - Math.random())
    for (let i = 0; i < numQuestions; i++) {
      selectedChords.push(shuffled[i])
    }

    // Generate questions based on mode
    return selectedChords.map((chord, idx) => {
      if (mode === 'recognition') {
        // Chord recognition: play chord, identify symbol
        const options = generateOptions(chord.symbol, allChords, difficulty)
        return {
          id: idx,
          type: 'recognition',
          chord: chord.symbol,
          question: `What chord is this?`,
          options: options,
          correctAnswer: chord.symbol,
          section: chord.section,
          measure: chord.measureNum
        }
      } else if (mode === 'progression') {
        // Progression: show section, user fills in chords
        return {
          id: idx,
          type: 'progression',
          chord: chord.symbol,
          question: `What chord appears in measure ${chord.measureNum} of the ${chord.section} section?`,
          correctAnswer: chord.symbol,
          section: chord.section,
          measure: chord.measureNum
        }
      }
      return null
    })
  }

  const generateOptions = (correctAnswer, allChords, difficulty) => {
    const options = [correctAnswer]
    const otherChords = [...new Set(allChords.map(c => c.symbol))].filter(c => c !== correctAnswer)
    
    const numOptions = difficulty === 'easy' ? 4 : difficulty === 'medium' ? 6 : 8
    
    while (options.length < Math.min(numOptions, otherChords.length + 1)) {
      const random = otherChords[Math.floor(Math.random() * otherChords.length)]
      if (!options.includes(random)) {
        options.push(random)
      }
    }
    
    return options.sort(() => 0.5 - Math.random())
  }

  const playChord = async (chordSymbol) => {
    if (!sampler) return
    await Tone.start()
    const notes = parseChordSymbol(chordSymbol)
    sampler.triggerAttackRelease(notes, '2n')
  }

  const parseChordSymbol = (symbol) => {
    const rootMap = {
      'C': 'C4', 'Db': 'Db4', 'D': 'D4', 'Eb': 'Eb4', 'E': 'E4', 'F': 'F4',
      'Gb': 'Gb4', 'G': 'G4', 'Ab': 'Ab4', 'A': 'A4', 'Bb': 'Bb4', 'B': 'B4'
    }

    let root = symbol.match(/^[A-G][b#]?/)?.[0] || 'C'
    const rootNote = rootMap[root] || 'C4'

    if (symbol.includes('m') && !symbol.includes('maj')) {
      return [rootNote, Tone.Frequency(rootNote).transpose(3).toNote(), Tone.Frequency(rootNote).transpose(7).toNote()]
    } else if (symbol.includes('dim')) {
      return [rootNote, Tone.Frequency(rootNote).transpose(3).toNote(), Tone.Frequency(rootNote).transpose(6).toNote()]
    } else if (symbol.includes('aug')) {
      return [rootNote, Tone.Frequency(rootNote).transpose(4).toNote(), Tone.Frequency(rootNote).transpose(8).toNote()]
    } else {
      return [rootNote, Tone.Frequency(rootNote).transpose(4).toNote(), Tone.Frequency(rootNote).transpose(7).toNote()]
    }
  }

  const submitAnswer = (answer) => {
    setUserAnswers([...userAnswers, answer])
    
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    } else {
      calculateScore([...userAnswers, answer])
    }
  }

  const calculateScore = (answers) => {
    let correct = 0
    questions.forEach((q, idx) => {
      if (answers[idx] === q.correctAnswer) {
        correct++
      }
    })
    setScore({ correct, total: questions.length, percentage: Math.round((correct / questions.length) * 100) })
  }

  const resetQuiz = () => {
    setQuizStarted(false)
    setQuestions([])
    setCurrentQuestion(0)
    setUserAnswers([])
    setScore(null)
  }

  if (loading) return <div className="text-center py-12">Loading...</div>
  if (!song) return <div className="text-center py-12">Song not found</div>

  if (score !== null) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Quiz Complete!</h1>
        
        <div className="bg-white rounded-lg shadow p-8 mb-6">
          <h2 className="text-3xl font-bold text-center mb-4">
            {score.percentage}%
          </h2>
          <p className="text-center text-xl text-gray-600 mb-6">
            {score.correct} out of {score.total} correct
          </p>
          
          <div className="space-y-4">
            <h3 className="text-xl font-semibold">Review:</h3>
            {questions.map((q, idx) => (
              <div key={idx} className={`p-4 rounded ${userAnswers[idx] === q.correctAnswer ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className="font-medium">{q.question}</p>
                <p className="text-sm text-gray-600 mt-1">
                  Your answer: <span className="font-semibold">{userAnswers[idx]}</span>
                </p>
                {userAnswers[idx] !== q.correctAnswer && (
                  <p className="text-sm text-green-700 mt-1">
                    Correct answer: <span className="font-semibold">{q.correctAnswer}</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <button onClick={resetQuiz} className="btn-primary">Try Again</button>
          <Link to={`/songs/${songId}`} className="btn-secondary">Back to Song</Link>
        </div>
      </div>
    )
  }

  if (!quizStarted) {
    return (
      <div className="max-w-2xl mx-auto">
        <Link to={`/songs/${songId}`} className="text-primary hover:underline mb-4 inline-block">
          ← Back to Song
        </Link>
        
        <h1 className="text-4xl font-bold mb-8">Start Quiz: {song.title}</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Quiz Mode</h2>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                value="recognition"
                checked={mode === 'recognition'}
                onChange={(e) => setMode(e.target.value)}
                className="w-4 h-4"
              />
              <span>Chord Recognition - Listen and identify the chord</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                value="progression"
                checked={mode === 'progression'}
                onChange={(e) => setMode(e.target.value)}
                className="w-4 h-4"
              />
              <span>Chord Progression - Answer questions about the song's chords</span>
            </label>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Difficulty</h2>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="difficulty"
                value="easy"
                checked={difficulty === 'easy'}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-4 h-4"
              />
              <span>Easy - 4 options</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="difficulty"
                value="medium"
                checked={difficulty === 'medium'}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-4 h-4"
              />
              <span>Medium - 6 options</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="difficulty"
                value="hard"
                checked={difficulty === 'hard'}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-4 h-4"
              />
              <span>Hard - 8 options</span>
            </label>
          </div>
        </div>

        <button onClick={startQuiz} className="btn-primary">Start Quiz</button>
      </div>
    )
  }

  const question = questions[currentQuestion]

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <p className="text-sm text-gray-600 mb-2">
          Question {currentQuestion + 1} of {questions.length}
        </p>
        <div className="bg-gray-200 rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all"
            style={{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-8 mb-6">
        <h2 className="text-2xl font-bold mb-4">{question.question}</h2>
        <p className="text-gray-600 mb-6">
          {question.section} - Measure {question.measure}
        </p>

        {question.type === 'recognition' && (
          <div className="mb-6">
            <button
              onClick={() => playChord(question.chord)}
              className="btn-primary"
            >
              🔊 Play Chord
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {question.options ? (
            question.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => submitAnswer(option)}
                className="p-4 border-2 border-gray-300 rounded-lg hover:border-primary hover:bg-primary/10 transition text-lg font-semibold"
              >
                {option}
              </button>
            ))
          ) : (
            <div className="col-span-2">
              <input
                type="text"
                placeholder="Enter chord symbol (e.g., Cmaj7)"
                className="w-full px-4 py-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-primary"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    submitAnswer(e.target.value)
                  }
                }}
              />
              <button
                onClick={() => {
                  const input = document.querySelector('input[type="text"]')
                  submitAnswer(input.value)
                }}
                className="btn-primary mt-4"
              >
                Submit Answer
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

