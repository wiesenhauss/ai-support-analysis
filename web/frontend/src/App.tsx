import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Analyze from '@/pages/Analyze'
import Explore from '@/pages/Explore'
import Insights from '@/pages/Insights'
import Talk from '@/pages/Talk'
import Settings from '@/pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="analyze" element={<Analyze />} />
        <Route path="explore" element={<Explore />} />
        <Route path="insights" element={<Insights />} />
        <Route path="talk" element={<Talk />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
