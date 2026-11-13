import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Clip } from '../lib/api'
import { useState, useEffect } from 'react'
import { Download, Save, ArrowLeft } from 'lucide-react'

const STYLES = ['hormozi', 'mrbeast', 'minimal', 'karaoke', 'bold_yellow', 'clean_podcast']

export default function Editor() {
  const { clipId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: clip } = useQuery<Clip>({
    queryKey: ['clip', clipId],
    queryFn: async () => (await api.get(`/clips/${clipId}`)).data,
  })

  const [title, setTitle] = useState('')
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(0)
  const [style, setStyle] = useState('hormozi')
  const [subs, setSubs] = useState<Clip['subtitles']>([])
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (clip) {
      setTitle(clip.title)
      setStart(clip.start)
      setEnd(clip.end)
      setStyle(clip.subtitle_style)
      setSubs(clip.subtitles || [])
      setDirty(false)
    }
  }, [clip])

  const saveMut = useMutation({
    mutationFn: async () => {
      await api.patch(`/clips/${clipId}`, { title, start, end, subtitle_style: style, subtitles: subs })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clip', clipId] })
      setDirty(false)
    },
  })

  const exportMut = useMutation({
    mutationFn: async () => {
      await api.post(`/clips/${clipId}/export`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clip', clipId] })
    },
  })

  if (!clip) return <div className="p-8 text-[#8A93A6]">Loading...</div>

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-[#8A93A6] hover:text-white mb-4">
        <ArrowLeft size={14} /> Back
      </button>
      <h1 className="text-2xl font-semibold tracking-tight mb-6">Clip editor</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="aspect-[9/16] max-h-[70vh] mx-auto rounded-xl overflow-hidden bg-black border border-[#1F2737]">
            <video
              key={clip.file_path}
              src={`/files/${clip.file_path}`}
              controls
              className="w-full h-full object-contain"
            />
          </div>
          <div className="flex gap-2 mt-4">
            <a href={`/api/clips/${clip.id}/file`} className="flex-1 py-2 rounded-lg bg-[#161C2C] border border-[#1F2737] text-sm flex items-center justify-center gap-2 hover:bg-[#1F2737]">
              <Download size={14} /> Download
            </a>
            <button
              onClick={() => exportMut.mutate()}
              disabled={exportMut.isPending}
              className="flex-1 py-2 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium disabled:opacity-50"
            >
              {exportMut.isPending ? 'Exporting...' : 'Re-export'}
            </button>
          </div>
          <div className="mt-2 text-xs text-[#8A93A6]">
            Viral score: <span className="text-white font-medium">{clip.viral_score}/100</span> · {clip.category}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <label className="text-xs text-[#8A93A6] block mb-1">Title</label>
            <input value={title} onChange={(e) => { setTitle(e.target.value); setDirty(true) }}
              className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
            {clip.titles?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {clip.titles.map((t, i) => (
                  <button key={i} onClick={() => { setTitle(t); setDirty(true) }}
                    className="text-[10px] px-2 py-1 rounded bg-[#161C2C] border border-[#1F2737] text-[#8A93A6] hover:text-white">
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <label className="text-xs text-[#8A93A6] block mb-2">Trim (seconds in source)</label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-[#5A6378]">Start</label>
                <input type="number" step="0.1" value={start} onChange={(e) => { setStart(+e.target.value); setDirty(true) }}
                  className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-[10px] text-[#5A6378]">End</label>
                <input type="number" step="0.1" value={end} onChange={(e) => { setEnd(+e.target.value); setDirty(true) }}
                  className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="text-[10px] text-[#8A93A6] mt-1">Duration: {(end - start).toFixed(1)}s</div>
          </div>

          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <label className="text-xs text-[#8A93A6] block mb-1">Subtitle style</label>
            <select value={style} onChange={(e) => { setStyle(e.target.value); setDirty(true) }}
              className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
              {STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <label className="text-xs text-[#8A93A6] block mb-2">Subtitles</label>
            <div className="space-y-2 max-h-60 overflow-auto scrollbar-thin">
              {subs.map((s, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <div className="text-[10px] text-[#5A6378] w-20 shrink-0 pt-2">{s.start.toFixed(1)}-{s.end.toFixed(1)}</div>
                  <input value={s.text} onChange={(e) => {
                    const next = [...subs]; next[i] = { ...next[i], text: e.target.value }; setSubs(next); setDirty(true)
                  }} className="flex-1 bg-[#0B0F1A] border border-[#1F2737] rounded px-2 py-1 text-xs" />
                </div>
              ))}
              {subs.length === 0 && <div className="text-xs text-[#8A93A6]">No subtitles</div>}
            </div>
          </div>

          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-4">
            <div className="text-xs text-[#8A93A6] mb-1">Explanation</div>
            <div className="text-xs text-[#C8CEDA]">{clip.explanation}</div>
            {clip.description && <div className="text-xs text-[#8A93A6] mt-2">{clip.description}</div>}
            {clip.hashtags?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {clip.hashtags.map((h, i) => <span key={i} className="text-[10px] text-[#7C5CFF]">{h}</span>)}
              </div>
            )}
          </div>

          <button
            onClick={() => saveMut.mutate()}
            disabled={!dirty || saveMut.isPending}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium disabled:opacity-40 flex items-center justify-center gap-2"
          >
            <Save size={14} /> {saveMut.isPending ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
