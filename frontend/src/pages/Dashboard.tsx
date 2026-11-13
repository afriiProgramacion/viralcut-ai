import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Project, Clip } from '../lib/api'
import { Link } from 'react-router-dom'
import { Film, Scissors, Clock, FolderOpen, ArrowRight } from 'lucide-react'

export default function Dashboard() {
  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => (await api.get('/projects')).data,
  })
  const { data: clips = [] } = useQuery<Clip[]>({
    queryKey: ['clips'],
    queryFn: async () => (await api.get('/clips')).data,
  })
  const processing = projects.filter((p) => p.status === 'processing').length

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-sm text-[#8A93A6] mt-1">Turn long videos into viral short-form clips.</p>
        </div>
        <Link to="/upload" className="px-4 py-2 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium hover:opacity-90">
          New project
        </Link>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Projects', value: projects.length, icon: FolderOpen },
          { label: 'Clips generated', value: clips.length, icon: Scissors },
          { label: 'Processing', value: processing, icon: Film },
          { label: 'Clips ready', value: clips.filter((c) => c.status !== 'error').length, icon: Clock },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <div className="flex items-center justify-between text-[#8A93A6] text-xs">
              {s.label}
              <s.icon size={14} />
            </div>
            <div className="text-2xl font-semibold mt-2">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold">Recent projects</h2>
            <Link to="/upload" className="text-xs text-[#7C5CFF] flex items-center gap-1">New <ArrowRight size={12} /></Link>
          </div>
          <div className="space-y-2">
            {projects.slice(0, 6).map((p) => (
              <Link key={p.id} to={p.status === 'processing' && p.last_job_id ? `/lab/${p.last_job_id}` : `/library?project=${p.id}`} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#161C2C]">
                <div>
                  <div className="text-sm">{p.name}</div>
                  <div className="text-[10px] text-[#8A93A6]">{new Date(p.created_at).toLocaleString()}</div>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${p.status === 'done' ? 'bg-green-500/10 text-green-400' : p.status === 'processing' ? 'bg-blue-500/10 text-blue-400' : 'bg-[#1F2737] text-[#8A93A6]'}`}>
                  {p.status}
                </span>
              </Link>
            ))}
            {projects.length === 0 && <div className="text-xs text-[#8A93A6] py-6 text-center">No projects yet.</div>}
          </div>
        </div>

        <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-5">
          <h2 className="text-sm font-semibold mb-4">Recent clips</h2>
          <div className="grid grid-cols-3 gap-2">
            {clips.slice(0, 6).map((c) => (
              <Link key={c.id} to={`/editor/${c.id}`} className="aspect-[9/16] rounded-lg bg-[#0B0F1A] border border-[#1F2737] overflow-hidden relative group">
                {c.thumb_path && <img src={`/files/${c.thumb_path}`} className="w-full h-full object-cover" />}
                <div className="absolute bottom-0 inset-x-0 p-1.5 bg-gradient-to-t from-black/80">
                  <div className="text-[9px] truncate">{c.title}</div>
                </div>
              </Link>
            ))}
            {clips.length === 0 && <div className="col-span-3 text-xs text-[#8A93A6] py-6 text-center">No clips yet.</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
