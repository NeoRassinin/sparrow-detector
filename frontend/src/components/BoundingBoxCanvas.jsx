import { useEffect, useRef } from 'react'

const COLORS = ['#34955b', '#02a4f0', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6']

export default function BoundingBoxCanvas({ imageUrl, detections, imageWidth, imageHeight }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)

      const lw = Math.max(2, Math.round(img.width / 400))
      const fontSize = Math.max(13, Math.round(img.width / 55))
      ctx.font = `600 ${fontSize}px Inter, sans-serif`

      detections.forEach((det, idx) => {
        const color = COLORS[idx % COLORS.length]
        const w = det.x2 - det.x1
        const h = det.y2 - det.y1

        // box
        ctx.strokeStyle = color
        ctx.lineWidth = lw
        ctx.strokeRect(det.x1, det.y1, w, h)

        // label
        const text = `${(det.confidence * 100).toFixed(0)}%`
        const padX = fontSize * 0.4
        const tw = ctx.measureText(text).width + padX * 2
        const th = fontSize * 1.4
        const ly = Math.max(0, det.y1 - th)
        ctx.fillStyle = color
        ctx.fillRect(det.x1, ly, tw, th)
        ctx.fillStyle = '#fff'
        ctx.fillText(text, det.x1 + padX, ly + th * 0.72)
      })
    }
    img.src = imageUrl
  }, [imageUrl, detections])

  return (
    <div className="flex max-h-[28rem] w-full items-center justify-center overflow-auto rounded-2xl bg-forest-50">
      <canvas ref={canvasRef} className="max-h-full max-w-full rounded-2xl" />
    </div>
  )
}
