import axios from 'axios'

const API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

export const detectAPI = {
  upload: async (file: File, opts?: { patch?: boolean }) => {
    const patch = opts?.patch ?? false
    const formData = new FormData()
    formData.append('file', file)
    formData.append('patch', String(patch))
    const response = await api.post('/detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // Tiled inference runs many forward passes — give it more headroom.
      timeout: patch ? 180000 : 60000,
    })
    return response.data
  },
}

export const detectionsAPI = {
  list: async (limit = 50, offset = 0, minCount?: number) => {
    const response = await api.get('/detections', {
      params: { limit, offset, min_count: minCount },
    })
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get(`/detections/${id}`)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/detections/${id}`)
    return response.data
  },
}

export const statsAPI = {
  get: async () => {
    const response = await api.get('/stats')
    return response.data
  },

  timeseries: async (period = 'day') => {
    const response = await api.get('/stats/timeseries', { params: { period } })
    return response.data
  },
}
