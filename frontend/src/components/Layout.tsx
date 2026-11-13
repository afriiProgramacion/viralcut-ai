import { NavLink, Outlet } from 'react-router-dom'
import { Home, Library, Settings, Upload, Zap } from 'lucide-react'

const nav = [
  { to: '/', label: 'Dashboard', icon: Home },
  { to: '/upload', label: 'New Project', icon: Upload },
  { to: '/library', label: 'Library', icon: Library },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#080B12]">
      <aside className="w-60 border-r border-[#1F2737] bg-[#0B0F1A] flex flex-col">
        <div className="px-5 py-5 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#7C5CFF] to-[#3B82F6] flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">ViralCut AI</div>
            <div className="text-[10px] text-[#8A93A6]">Short-form factory</div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  isActive
                    ? 'bg-[#161C2C] text-white'
                    : 'text-[#8A93A6] hover:text-white hover:bg-[#111622]'
                }`
              }
            >
              <n.icon size={16} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-[10px] text-[#5A6378] border-t border-[#1F2737]">
          Local mode · FFmpeg powered
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
