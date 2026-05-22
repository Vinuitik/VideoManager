import { Routes, Route, NavLink } from 'react-router-dom'
import DownloadPoll from './pages/DownloadPoll'
import DownloadWS from './pages/DownloadWS'
import Library from './pages/Library'

// NavLink automatically adds an "active" class when its route is current
function Nav() {
  const base = 'px-4 py-2 rounded text-sm font-medium transition-colors'
  const active = `${base} bg-zinc-700 text-white`
  const inactive = `${base} text-zinc-400 hover:text-white`

  return (
    <nav className="flex gap-2 p-4 bg-zinc-900 border-b border-zinc-800">
      <span className="text-white font-bold mr-4 self-center">VideoManager</span>
      <NavLink to="/"          className={({ isActive }) => isActive ? active : inactive}>Library</NavLink>
      <NavLink to="/poll"      className={({ isActive }) => isActive ? active : inactive}>Download (Poll)</NavLink>
      <NavLink to="/websocket" className={({ isActive }) => isActive ? active : inactive}>Download (WS)</NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Nav />
      <main className="max-w-3xl mx-auto p-6">
        {/* Routes renders the first <Route> that matches the current URL */}
        <Routes>
          <Route path="/"          element={<Library />} />
          <Route path="/poll"      element={<DownloadPoll />} />
          <Route path="/websocket" element={<DownloadWS />} />
        </Routes>
      </main>
    </div>
  )
}
