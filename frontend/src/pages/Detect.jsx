import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { detectAPI } from '../lib/api'
import BoundingBoxCanvas from '../components/BoundingBoxCanvas'

export default function Detect({ onSuccess }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0]
      setFile(selectedFile)
      setError(null)
      setResult(null)
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target.result)
      reader.readAsDataURL(selectedFile)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.gif', '.webp'] },
  })

  const handleDetect = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const detectionResult = await detectAPI.upload(file)
      setResult(detectionResult)
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось обработать изображение. Попробуйте снова.')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
      {/* Left: upload */}
      <div className="space-y-5">
        <div
          {...getRootProps()}
          className={`group relative cursor-pointer overflow-hidden rounded-3xl border-2 border-dashed p-10 text-center transition-all ${
            isDragActive
              ? 'border-forest-500 bg-forest-50/80 scale-[1.01]'
              : 'border-forest-300 bg-white/60 hover:border-forest-400 hover:bg-white/80'
          }`}
        >
          <input {...getInputProps()} />
          <div className={`mx-auto mb-4 grid h-20 w-20 place-items-center rounded-3xl bg-gradient-to-br from-forest-400 to-forest-600 text-4xl shadow-glow transition-transform ${isDragActive ? 'scale-110' : 'group-hover:scale-105'}`}>
            📸
          </div>
          {isDragActive ? (
            <p className="font-display text-lg font-bold text-forest-700">Отпустите фото здесь…</p>
          ) : (
            <>
              <p className="font-display text-lg font-bold text-forest-800">
                Перетащите фото сюда
              </p>
              <p className="mt-1 text-sm text-forest-600/60">или нажмите, чтобы выбрать файл</p>
              <p className="mt-3 text-xs text-forest-600/40">JPG · PNG · WEBP · GIF</p>
            </>
          )}
        </div>

        {preview && !result && (
          <div className="glass overflow-hidden rounded-3xl p-3 animate-fade-up">
            <img src={preview} alt="preview" className="w-full rounded-2xl" />
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700 animate-fade-up">
            <span className="text-xl">⚠️</span>
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleDetect}
            disabled={!file || loading}
            className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-forest-500 to-forest-700 py-4 font-display font-bold text-white shadow-glow transition-all hover:shadow-lg disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none"
          >
            {loading ? (
              <>
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Анализируем…
              </>
            ) : (
              <>🔍 Найти воробьёв</>
            )}
          </button>
          {(file || result) && (
            <button
              onClick={reset}
              className="rounded-2xl bg-white/70 px-5 font-semibold text-forest-700 ring-1 ring-forest-200 transition hover:bg-white"
            >
              Сброс
            </button>
          )}
        </div>
      </div>

      {/* Right: results */}
      <div className="space-y-5">
        {result ? (
          <div className="animate-fade-up space-y-5">
            <div className="glass overflow-hidden rounded-3xl p-3">
              <BoundingBoxCanvas
                imageUrl={result.original_url}
                detections={result.detections}
                imageWidth={result.image_width}
                imageHeight={result.image_height}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <StatBox label="Найдено воробьёв" value={result.sparrow_count} icon="🐦" tint="from-forest-400 to-forest-600" />
              <StatBox label="Время обработки" value={`${result.processing_time_ms.toFixed(0)} мс`} icon="⚡" tint="from-sky-400 to-sky-600" />
            </div>

            {result.detections.length > 0 && (
              <div className="glass rounded-3xl p-5">
                <p className="mb-3 font-display font-bold text-forest-800">
                  Список находок ({result.detections.length})
                </p>
                <div className="grid max-h-64 grid-cols-2 gap-2 overflow-y-auto pr-1">
                  {result.detections.map((det, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-xl bg-forest-50 px-3 py-2 text-sm"
                    >
                      <span className="font-medium text-forest-700">#{idx + 1}</span>
                      <span className="font-bold text-forest-600">
                        {(det.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="glass flex h-full min-h-[20rem] flex-col items-center justify-center rounded-3xl p-10 text-center">
            <span className="mb-4 text-6xl opacity-60 animate-float">🌳</span>
            <p className="font-display text-lg font-bold text-forest-700">Результаты появятся здесь</p>
            <p className="mt-1 text-sm text-forest-600/60">
              Загрузите фото и нажмите «Найти воробьёв»
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function StatBox({ label, value, icon, tint }) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${tint}`} />
      <div className="flex items-center gap-3">
        <span className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${tint} text-2xl shadow-lg`}>
          {icon}
        </span>
        <div>
          <p className="text-xs font-medium text-forest-600/60">{label}</p>
          <p className="font-display text-2xl font-extrabold text-forest-800">{value}</p>
        </div>
      </div>
    </div>
  )
}
