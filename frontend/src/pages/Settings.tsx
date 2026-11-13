import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useState, useEffect } from 'react'
import { CheckCircle2 } from 'lucide-react'

export default function SettingsPage() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['settings'], queryFn: async () => (await api.get('/settings')).data })

  const [anthropic, setAnthropic] = useState('')
  const [openai, setOpenai] = useState('')
  const [provider, setProvider] = useState('anthropic')
  const [model, setModel] = useState('')
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')
  const [ollamaModel, setOllamaModel] = useState('llama3.2')
  const [whisperModel, setWhisperModel] = useState('small')
  const [whisperDevice, setWhisperDevice] = useState('cpu')
  const [computeType, setComputeType] = useState('int8')
  const [maxUpload, setMaxUpload] = useState(2048)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setProvider(data.ai_provider)
      setModel(data.ai_model || '')
      setOllamaUrl(data.ollama_url || 'http://localhost:11434')
      setOllamaModel(data.ollama_model || 'llama3.2')
      setWhisperModel(data.whisper_model)
      setWhisperDevice(data.whisper_device)
      setComputeType(data.whisper_compute_type)
      setMaxUpload(data.max_upload_mb)
    }
  }, [data])

  const mut = useMutation({
    mutationFn: async () => {
      const body: any = {
        ai_provider: provider,
        ai_model: model,
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel,
        whisper_model: whisperModel,
        whisper_device: whisperDevice,
        whisper_compute_type: computeType,
        max_upload_mb: maxUpload,
      }
      if (anthropic) body.anthropic_api_key = anthropic
      if (openai) body.openai_api_key = openai
      await api.put('/settings', body)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      setAnthropic('')
      setOpenai('')
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-1">Settings</h1>
      <p className="text-sm text-[#8A93A6] mb-6">Configure AI providers and processing.</p>

      <div className="space-y-4">
        <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-5">
          <h2 className="text-sm font-semibold mb-3">AI provider</h2>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Provider</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)} className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI</option>
                <option value="ollama">Ollama (local, free)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Model (optional)</label>
              <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="claude-sonnet-4-20250514 / gpt-4o-mini"
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Anthropic API key {data?.has_anthropic && <span className="text-green-400">({data.anthropic_api_key_masked})</span>}</label>
              <input type="password" value={anthropic} onChange={(e) => setAnthropic(e.target.value)} placeholder="sk-ant-..."
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">OpenAI API key {data?.has_openai && <span className="text-green-400">({data.openai_api_key_masked})</span>}</label>
              <input type="password" value={openai} onChange={(e) => setOpenai(e.target.value)} placeholder="sk-..."
                className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        {provider === 'ollama' && (
          <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-5">
            <h2 className="text-sm font-semibold mb-3">Ollama (local LLM)</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[#8A93A6] block mb-1">Server URL</label>
                <input value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} placeholder="http://localhost:11434"
                  className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[#8A93A6] block mb-1">Model</label>
                <input value={ollamaModel} onChange={(e) => setOllamaModel(e.target.value)} placeholder="llama3.2"
                  className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="text-xs text-[#8A93A6] mt-2">
              Install Ollama from https://ollama.com, then run: <code className="text-[#7C5CFF]">ollama pull llama3.2</code>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-[#1F2737] bg-[#111622] p-5">
          <h2 className="text-sm font-semibold mb-3">Whisper (local transcription)</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Model</label>
              <select value={whisperModel} onChange={(e) => setWhisperModel(e.target.value)} className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="tiny">tiny (fast)</option>
                <option value="base">base</option>
                <option value="small">small (recommended)</option>
                <option value="medium">medium (accurate)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Device</label>
              <select value={whisperDevice} onChange={(e) => setWhisperDevice(e.target.value)} className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="cpu">CPU</option>
                <option value="cuda">CUDA</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-[#8A93A6] block mb-1">Compute type</label>
              <select value={computeType} onChange={(e) => setComputeType(e.target.value)} className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm">
                <option value="int8">int8</option>
                <option value="float16">float16</option>
                <option value="float32">float32</option>
              </select>
            </div>
          </div>
          <div className="mt-3">
            <label className="text-xs text-[#8A93A6] block mb-1">Max upload (MB)</label>
            <input type="number" value={maxUpload} onChange={(e) => setMaxUpload(+e.target.value)}
              className="w-full bg-[#0B0F1A] border border-[#1F2737] rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        <button onClick={() => mut.mutate()} disabled={mut.isPending}
          className="w-full py-2.5 rounded-lg bg-gradient-to-r from-[#7C5CFF] to-[#3B82F6] text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2">
          {mut.isPending ? 'Saving...' : saved ? <><CheckCircle2 size={14} /> Saved</> : 'Save settings'}
        </button>

        <div className="text-xs text-[#8A93A6]">
          Transcription runs locally with faster-whisper (no API key needed). Semantic analysis and metadata generation require an AI API key.
        </div>
      </div>
    </div>
  )
}
