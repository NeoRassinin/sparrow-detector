import { useState } from 'react'

export default function DetectionCard({ detection, onClick }) {
  const [broken, setBroken] = useState(false)
  // Clean original photo for the thumbnail — annotated boxes live in the detail view
  const imageUrl = detection.original_url

  return (
    <button
      onClick={onClick}
      className="group block w-full overflow-hidden rounded-2xl bg-white text-left shadow-soft ring-1 ring-forest-100 transition-all hover:-translate-y-1 hover:shadow-glow"
    >
      <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-forest-50 to-sky-50">
        {imageUrl && !broken ? (
          <img
            src={imageUrl}
            alt=""
            loading="lazy"
            onError={() => setBroken(true)}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="grid h-full place-items-center text-4xl opacity-40">🌿</div>
        )}

        {/* count badge */}
        <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-forest-700/90 px-3 py-1 text-xs font-bold text-white shadow-lg backdrop-blur">
          🐦 {detection.sparrow_count}
        </span>

        {/* subtle gradient for legibility */}
        <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/30 to-transparent" />
      </div>

      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <p className="truncate text-sm font-medium text-forest-700/80">
          {detection.filename}
        </p>
        <span className="shrink-0 text-xs text-forest-600/50">
          {detection.timestamp
            ? new Date(detection.timestamp).toLocaleDateString('ru-RU')
            : ''}
        </span>
      </div>
    </button>
  )
}
