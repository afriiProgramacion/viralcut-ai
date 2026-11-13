import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Upload as UploadIcon, Film, X } from 'lucide-react'

const CLIP_COUNTS = [3, 5, 10, 0]
const DURATIONS = [15, 30, 45, 60, 90]
const STYLES = ['hormozi', 'mrbeast', 'minimal', 'karaoke', 'bold_yellow', 'clean_podcast']

export default function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'file' | 'youtube'>('file')
  const [ytUrl, setYtUrl] = useState('')
  const [drag, setDrag] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [status, setStatus] = useState('')
  const [config, setConfig] = useState({
    clip_count: 5,
    clip_duration: 30,
    platform: 'tiktok',
    language: 'auto',
    subtitle_style: 'hormozi',
    cut_aggressiveness: 'balanced',
    priority: 'mixed',
  })
  const inputRef = useRef<HTMLInputElement>(null)

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  const formatSize = (b: number) => (b / (1024 * 1024)).toFixed(1) + ' MB'

  const start = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setStatus('Creating project...')
    try {
      const proj = (await api.post('/projects', { name: file.name.replace(/\.[^.]+$/, '') })).data
      setStatus('Uploading video...')
      const fd = new FormData()
      fd.append('file', file)
      await api.post(`/projects/${proj.id}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      setStatus('Starting analysis...')
      const job = (await api.post(`/projects/${proj.id}/start`, config)).data
      navigate(`/lab/${job.job_id}`)
    } catch (e: any) {
      setStatus('Error: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-1">New project</h1>
      <p className="text-sm text-[#8A93A6] mb-6">Upload a long video and let AI do the rest.</p>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode('file')} className={`px-4 py-2 rounded-lg text-sm border ${mode === 'file' ? 'bg-[#7C5CFF] border-[#7C5CFF] text-white' : 'bg-[#111622] border-[#1F2737] text-[#8A93A6]'}`}>Archivo local</button>
        <button onClick={() => setMode('youtube')} className={`px-4 py-2 rounded-lg text-sm border ${mode === 'youtube' ? 'bg-[#7C5CFF] border-[#7C5CFF] text-white' : 'bg-[#111622] border-[#1F2737] text-[#8A93A6]'}`}>YouTube URL</button>
      </div>

      {mode === 'youtube' ? (
        <div className="rounded-2xl border border-[#1F2737] bg-[#111622] p-5">
          <label className="text-xs text-[#8A93A6] block mb-1">URL de YouTube</label>
          <input value={ytUrl} onChange={(e) => setYtUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..."
            className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm mb-4" />

          {/* config grid same as below */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Clip count</label>
              <select value={config.clip_count} onChange={(e) => setConfig({ ...config, clip_count: +e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {CLIP_COUNTS.map((n) => <option key={n} value={n}>{n === 0 ? 'Auto' : n}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Target duration</label>
              <select value={config.clip_duration} onChange={(e) => setConfig({ ...config, clip_duration: +e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {DURATIONS.map((n) => <option key={n} value={n}>{n}s</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Platform</label>
              <select value={config.platform} onChange={(e) => setConfig({ ...config, platform: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="tiktok">TikTok</option>
                <option value="reels">Instagram Reels</option>
                <option value="shorts">YouTube Shorts</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Subtitle style</label>
              <select value={config.subtitle_style} onChange={(e) => setConfig({ ...config, subtitle_style: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          {!uploading && (
            <button onClick={async () => {
              if (!ytUrl) return
              setUploading(true); setStatus('Downloading from YouTube...')
              try {
                const res = await api.post('/projects/youtube', { url: ytUrl, config })
                navigate(`/lab/${res.data.job_id}`)
              } catch (e: any) {
                setStatus('Error: ' + (e?.response?.data?.detail || e.message))
              } finally { setUploading(false) }
            }} className="w-full py-2.5 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium hover:opacity-90">
              Download & analyze
            </button>
          )}
          {status && <div className="text-xs text-red-400 mt-2">{status}</div>}
        </div>
      ) : !file ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition ${
            drag ? 'border-[#7C5CFF] bg-[#7C5CFF]/5' : 'border-[#1F2737] bg-[#111622] hover:border-[#3B82F6]'
          }`}
        >
          <UploadIcon size={32} className="mx-auto text-[#7C5CFF] mb-3" />
          <div className="text-sm font-medium">Drop your video here or click to browse</div>
          <div className="text-xs text-[#8A93A6] mt-1">MP4, MOV, WebM · up to 2GB</div>
          <input ref={inputRef} type="file" accept="video/*" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f) }} />
        </div>
      ) : (
        <div className="rounded-2xl border border-[#1F2737] bg-[#111622] p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#161C2C] flex items-center justify-center">
              <Film size={18} className="text-[#7C5CFF]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{file.name}</div>
              <div className="text-xs text-[#8A93A6]">{formatSize(file.size)}</div>
            </div>
            <button onClick={() => setFile(null)} className="text-[#8A93A6] hover:text-white">
              <X size={16} />
            </button>
          </div>

          {uploading && (
            <div className="mb-4">
              <div className="h-1.5 bg-[#1F2737] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] transition-all" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-xs text-[#8A93A6] mt-1">{status} {progress > 0 && progress < 100 ? `${progress}%` : ''}</div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Clip count</label>
              <select value={config.clip_count} onChange={(e) => setConfig({ ...config, clip_count: +e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {CLIP_COUNTS.map((n) => <option key={n} value={n}>{n === 0 ? 'Auto' : n}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Target duration</label>
              <select value={config.clip_duration} onChange={(e) => setConfig({ ...config, clip_duration: +e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {DURATIONS.map((n) => <option key={n} value={n}>{n}s</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Platform</label>
              <select value={config.platform} onChange={(e) => setConfig({ ...config, platform: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="tiktok">TikTok</option>
                <option value="reels">Instagram Reels</option>
                <option value="shorts">YouTube Shorts</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Subtitle language</label>
              <select value={config.language} onChange={(e) => setConfig({ ...config, language: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="auto">Auto detect</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="pt">Portuguese</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Subtitle style</label>
              <select value={config.subtitle_style} onChange={(e) => setConfig({ ...config, subtitle_style: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                {STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Cut aggressiveness</label>
              <select value={config.cut_aggressiveness} onChange={(e) => setConfig({ ...config, cut_aggressiveness: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="soft">Soft</option>
                <option value="balanced">Balanced</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-[#8A93A6] block mb-1">Priority</label>
              <select value={config.priority} onChange={(e) => setConfig({ ...config, priority: e.target.value })}
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="mixed">Mixed</option>
                <option value="entertainment">Entertainment</option>
                <option value="controversy">Controversy</option>
                <option value="education">Education</option>
                <option value="humor">Humor</option>
                <option value="storytelling">Storytelling</option>
              </select>
            </div>
          </div>

          {!uploading && (
            <button onClick={start} className="w-full py-2.5 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium hover:opacity-90">
              Analyze & generate clips
            </button>
          )}
          {status && !uploading && <div className="text-xs text-red-400 mt-2">{status}</div>}
        </div>
      )}
    </div>
  )
}
