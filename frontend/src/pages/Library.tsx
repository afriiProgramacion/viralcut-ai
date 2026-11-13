import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Clip } from '../lib/api'
import { useState } from 'react'
import { Filter, Download } from 'lucide-react'

const SORTS = [
  { v: 'score', l: 'Highest viral score' },
  { v: 'short', l: 'Shortest' },
  { v: 'long', l: 'Longest' },
]
const CATS = ['all', 'humor', 'controversy', 'education', 'storytelling', 'entertainment', 'mixed']

export default function Library() {
  const [sp] = useSearchParams()
  const projectId = sp.get('project')
  const navigate = useNavigate()
  const [sort, setSort] = useState('score')
  const [cat, setCat] = useState('all')

  const { data: clips = [] } = useQuery<Clip[]>({
    queryKey: ['clips', projectId],
    queryFn: async () => (await api.get(`/clips${projectId ? `?project_id=${projectId}` : ''}`)).data,
  })

  const filtered = clips
    .filter((c) => cat === 'all' || c.category === cat)
    .sort((a, b) => {
      if (sort === 'score') return b.viral_score - a.viral_score
      if (sort === 'short') return a.duration - b.duration
      if (sort === 'long') return b.duration - a.duration
      return 0
    })

  const downloadAll = async () => {
    if (!projectId) return
    window.open(`/api/clips/project/${projectId}/zip`, '_blank')
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clip library</h1>
          <p className="text-sm text-[#8A93A6] mt-1">{filtered.length} clips</p>
        </div>
        {projectId && (
          <button onClick={downloadAll} className="px-4 py-2 rounded-lg bg-[#161C2C] border border-[#1F2737] text-sm flex items-center gap-2 hover:bg-[#1F2737]">
            <Download size={14} /> Download all (ZIP)
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <Filter size={14} className="text-[#8A93A6]" />
        <select value={sort} onChange={(e) => setSort(e.target.value)} className="bg-[#111622] border border-[#1F2737] rounded-lg px-3 py-1.5 text-xs">
          {SORTS.map((s) => <option key={s.v} value={s.v}>{s.l}</option>)}
        </select>
        <div className="flex gap-1 flex-wrap">
          {CATS.map((c) => (
            <button key={c} onClick={() => setCat(c)}
              className={`px-3 py-1.5 rounded-lg text-xs border ${cat === c ? 'bg-[#7C5CFF] border-[#7C5CFF] text-white' : 'bg-[#111622] border-[#1F2737] text-[#8A93A6] hover:text-white'}`}>
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {filtered.map((c) => (
          <button key={c.id} onClick={() => navigate(`/editor/${c.id}`)}
            className="text-left rounded-xl border border-[#1F2737] bg-[#111622] overflow-hidden hover:border-[#7C5CFF] transition group">
            <div className="aspect-[9/16] bg-[#0B0F1A] relative">
              {c.thumb_path && <img src={`/files/${c.thumb_path}`} className="w-full h-full object-cover" />}
              <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-black/60 text-[10px] font-medium">
                {c.viral_score}
              </div>
            </div>
            <div className="p-3">
              <div className="text-xs font-medium truncate">{c.title}</div>
              <div className="text-[10px] text-[#8A93A6] mt-0.5">{Math.round(c.duration)}s · {c.category}</div>
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-center text-sm text-[#8A93A6] py-12">No clips yet.</div>
        )}
      </div>
    </div>
  )
}
