import { useState, useEffect } from 'react'
import { detectionsAPI } from '../lib/api'
import DetectionCard from '../components/DetectionCard'

export default function History({ refreshTrigger }) {
  const [detections, setDetections] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [limit] = useState(12)
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    loadDetections()
  }, [refreshTrigger, offset])

  const loadDetections = async () => {
    setLoading(true)
    try {
      const data = await detectionsAPI.list(limit, offset)
      setDetections(data.data)
      setTotal(data.total)
    } catch (error) {
      console.error('Failed to load detections:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить эту детекцию безвозвратно?')) return
    try {
      await detectionsAPI.delete(id)
      setDetections(detections.filter((d) => d.id !== id))
      setSelected(null)
      setTotal((t) => Math.max(0, t - 1))
    } catch (error) {
      console.error('Failed to delete detection:', error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-forest-800">История детекций</h1>
          <p className="text-sm text-forest-600/60">Всего записей: {total}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-24">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-forest-200 border-t-forest-600" />
        </div>
      ) : detections.length === 0 ? (
        <div className="glass flex flex-col items-center gap-3 rounded-3xl py-20 text-center">
          <span className="text-5xl">🪺</span>
          <p className="font-medium text-forest-700">История пуста</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {detections.map((d) => (
              <DetectionCard key={d.id} detection={d} onClick={() => setSelected(d)} />
            ))}
          </div>

          {total > limit && (
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="rounded-xl bg-white/70 px-4 py-2 font-medium text-forest-700 ring-1 ring-forest-200 transition hover:bg-white disabled:opacity-40"
              >
                ← Назад
              </button>
              <span className="text-sm font-medium text-forest-600/70">
                {offset + 1}–{Math.min(offset + limit, total)} из {total}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="rounded-xl bg-white/70 px-4 py-2 font-medium text-forest-700 ring-1 ring-forest-200 transition hover:bg-white disabled:opacity-40"
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}

      {/* Detail modal */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-forest-900/40 p-4 backdrop-blur-sm animate-fade-up"
          onClick={() => setSelected(null)}
        >
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="font-display text-xl font-bold text-forest-800">
                  Детекция #{selected.id}
                </h3>
                <p className="text-sm text-forest-600/60">
                  {selected.timestamp ? new Date(selected.timestamp).toLocaleString('ru-RU') : ''}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="grid h-9 w-9 place-items-center rounded-full bg-forest-50 text-forest-600 transition hover:bg-forest-100"
              >
                ✕
              </button>
            </div>

            <img
              src={selected.annotated_url || selected.original_url}
              alt="detection"
              className="w-full rounded-2xl"
            />

            <div className="mt-5 grid grid-cols-3 gap-3">
              <Info label="Воробьёв" value={selected.sparrow_count} />
              <Info label="Размер" value={`${selected.image_width}×${selected.image_height}`} />
              <Info label="Время" value={`${selected.processing_time_ms?.toFixed(0) || '-'} мс`} />
            </div>

            <button
              onClick={() => handleDelete(selected.id)}
              className="mt-5 w-full rounded-2xl bg-red-500 py-3 font-semibold text-white transition hover:bg-red-600"
            >
              🗑️ Удалить детекцию
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Info({ label, value }) {
  return (
    <div className="rounded-2xl bg-forest-50 p-3 text-center">
      <p className="text-xs font-medium text-forest-600/60">{label}</p>
      <p className="mt-1 font-display text-lg font-bold text-forest-800">{value}</p>
    </div>
  )
}
