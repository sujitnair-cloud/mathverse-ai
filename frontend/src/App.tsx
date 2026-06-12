import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Home from './pages/Home'
import Solver from './pages/Solver'
import FormulaLibrary from './pages/FormulaLibrary'
import TopicWiki from './pages/TopicWiki'
import GraphCalculator from './pages/GraphCalculator'
import Quiz from './pages/Quiz'
import History from './pages/History'
import Profile from './pages/Profile'
import Admin from './pages/Admin'
import Settings from './pages/Settings'
import About from './pages/About'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/solver" element={<Solver />} />
              <Route path="/formulas" element={<FormulaLibrary />} />
              <Route path="/topics" element={<TopicWiki />} />
              <Route path="/graph" element={<GraphCalculator />} />
              <Route path="/quiz" element={<Quiz />} />
              <Route path="/history" element={<History />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </GoogleOAuthProvider>
  )
}
