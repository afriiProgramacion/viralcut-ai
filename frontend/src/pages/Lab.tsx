import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Job, Clip } from '../lib/api'
import { Loader2, CheckCircle2, AlertCircle, XCircle } from 'lucide-react'

const STAGES = [
  'Extracting audio',
  'Transcribing',
  'Analyzing content',
  'Detecting moments',
  'Generating clips',
  'Preparing exports',
  'Done',
]

export default function Lab() {
  const { jobId } = useParams()
  const navigate = useNavigate()

  const { data: job } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: async () => (await api.get(`/jobs/${jobId}`)).data,
    refetchInterval: (q) => {
      const d = q.state.data as Job | undefined
      if (!d || d.status === 'running' || d.status === 'queued') return 2000
      return false
    },
  })

  const qc = useQueryClient()
  const { data: clips = [] } = useQuery<Clip[]>({
    queryKey: ['clips', job?.project_id],
    queryFn: async () => (await api.get(`/clips?project_id=${job?.project_id}`)).data,
    enabled: !!job?.project_id,
    refetchInterval: job?.status === 'running' || job?.status === 'queued' ? 3000 : false,
  })

  const cancelMut = useMutation({
    mutationFn: async () => api.post(`/jobs/${jobId}/cancel`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job', jobId] })
      navigate('/')
    },
  })

  const progress = job?.progress ?? 0
  const stage = job?.stage ?? 'queued'
  const stageIndex = STAGES.findIndex((s) => stage.toLowerCase().includes(s.toLowerCase().split(' ')[0]))
  const effectiveIndex = stageIndex >= 0 ? stageIndex : 0

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-1">AI Lab</h1>
      <p className="text-sm text-[#8A93A6] mb-6">Analyzing your video and generating clips.</p>

      <div className="rounded-2xl border border-[#1F2737] bg-[#111622] p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium">{job?.message || 'Starting...'}</div>
          <div className="text-sm text-[#8A93A6]">{progress}%</div>
        </div>
        <div className="h-2 bg-[#1F2737] rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>

        <div className="mt-6 space-y-2">
          {STAGES.map((s, i) => {
            const done = i < effectiveIndex || job?.status === 'done'
            const active = i === effectiveIndex && job?.status !== 'done' && job?.status !== 'error'
            return (
              <div key={s} className="flex items-center gap-3 text-sm">
                {job?.status === 'error' && i === effectiveIndex ? (
                  <AlertCircle size={16} className="text-red-400" />
                ) : done ? (
                  <CheckCircle2 size={16} className="text-green-400" />
                ) : active ? (
                  <Loader2 size={16} className="text-[#7C5CFF] animate-spin" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-[#2A3348]" />
                )}
                <span className={done ? 'text-white' : active ? 'text-white' : 'text-[#5A6378]'}>{s}</span>
              </div>
            )
          })}
        </div>

        {(job?.status === 'running' || job?.status === 'queued') && (
          <div className="mt-4">
            <button onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}
              className="px-4 py-2 rounded-lg bg-[#161C2C] border border-[#1F2737] text-sm flex items-center gap-2 hover:bg-red-500/10 hover:border-red-500/30 text-red-300 disabled:opacity-50">
              <XCircle size={14} /> {cancelMut.isPending ? 'Cancelling...' : 'Cancel project'}
            </button>
          </div>
        )}

        {job?.status === 'error' && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-300">
            {job.error}
          </div>
        )}

        {job?.status === 'done' && (
          <div className="mt-6 flex gap-3">
            <button
              onClick={() => navigate(`/library?project=${job.project_id}`)}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium"
            >
              View {clips.length} clips
            </button>
          </div>
        )}
      </div>

      {clips.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold mb-3">Generated clips</h2>
          <div className="grid grid-cols-4 gap-3">
            {clips.map((c) => (
              <div key={c.id} className="aspect-[9/16] rounded-lg bg-[#0B0F1A] border border-[#1F2737] overflow-hidden relative">
                {c.thumb_path && <img src={`/files/${c.thumb_path}`} className="w-full h-full object-cover" />}
                <div className="absolute bottom-0 inset-x-0 p-2 bg-gradient-to-t from-black/90">
                  <div className="text-[10px] truncate">{c.title}</div>
                  <div className="text-[9px] text-[#8A93A6]">{c.viral_score}/100</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
