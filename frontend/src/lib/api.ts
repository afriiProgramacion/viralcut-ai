import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
})

export type Project = {
  id: string
  name: string
  created_at: string
  updated_at: string
  status: string
  video_id?: string | null
  last_job_id?: string | null
  config?: any
}

export type Video = {
  id: string
  project_id?: string | null
  filename: string
  size_bytes: number
  duration: number
  width: number
  height: number
  mime: string
  created_at: string
}

export type Job = {
  id: string
  project_id?: string | null
  video_id?: string | null
  type: string
  status: string
  progress: number
  stage: string
  message: string
  result?: any
  error?: string | null
  created_at: string
  updated_at: string
}

export type Clip = {
  id: string
  project_id: string
  video_id: string
  start: number
  end: number
  duration: number
  title: string
  titles: string[]
  description: string
  hashtags: string[]
  hook: string
  category: string
  viral_score: number
  score_breakdown: Record<string, number>
  explanation: string
  subtitle_style: string
  subtitles: { start: number; end: number; text: string }[]
  file_path?: string | null
  thumb_path?: string | null
  status: string
  created_at: string
}

export const fileUrl = (rel?: string | null) =>
  rel ? `/files/${rel}` : ''
