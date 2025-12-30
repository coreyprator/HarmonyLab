import { Link, useLocation } from 'react-router-dom'

export default function Header() {
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  return (
    <header className="bg-primary text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold flex items-center gap-2">
            🎹 HarmonyLab
          </Link>
          
          <div className="flex gap-6">
            <Link 
              to="/" 
              className={`hover:text-gray-200 transition ${isActive('/') ? 'border-b-2 border-white' : ''}`}
            >
              Songs
            </Link>
            <Link 
              to="/progress" 
              className={`hover:text-gray-200 transition ${isActive('/progress') ? 'border-b-2 border-white' : ''}`}
            >
              Progress
            </Link>
            <Link 
              to="/import" 
              className={`hover:text-gray-200 transition ${isActive('/import') ? 'border-b-2 border-white' : ''}`}
            >
              Import
            </Link>
            <a 
              href="https://github.com/coreyprator/HarmonyLab/blob/main/HarmonyLab-USER_GUIDE.md" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-200 transition"
            >
              Help
            </a>
          </div>
        </nav>
      </div>
    </header>
  )
}
