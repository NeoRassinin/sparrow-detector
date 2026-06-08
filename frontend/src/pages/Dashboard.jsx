import { useState, useEffect } from 'react'
import { statsAPI, detectionsAPI } from '../lib/api'
import StatsChart from '../components/StatsChart'
import DetectionCard from '../components/DetectionCard'

export default function Dashboard({ refreshTrigger, onNavigate }) {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [refreshTrigger])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsData, detectionsData] = await Promise.all([
        statsAPI.get(),
        detectionsAPI.list(6, 0),
      ])
      setStats(statsData)
      setRecent(detectionsData.data)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-forest-200 border-t-forest-600" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-forest-600 via-forest-700 to-forest-800 p-8 text-white shadow-soft sm:p-10">
        <div className="absolute -right-10 -top-10 text-[12rem] opacity-10 animate-float select-none">
          🐦
        </div>
        <div className="relative max-w-xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
            <span className="h-2 w-2 animate-pulse rounded-full bg-lime-300" />
            Модель активна
          </span>
          <h1 className="mt-4 font-display text-3xl font-extrabold leading-tight sm:text-4xl">
            Считаем воробьёв<br />с точностью ИИ 🌿
          </h1>
          <p className="mt-3 text-forest-100/90">
            Загрузите снимок — нейросеть YOLO11x найдёт и обведёт каждую птицу за доли секунды.
          </p>
          <button
            onClick={() => onNavigate?.('detect')}
            className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-white px-6 py-3 font-semibold text-forest-700 shadow-lg transition-transform hover:scale-105"
          >
            🔍 Начать детекцию
          </button>
        </div>
      </section>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard title="Всего сканирований" value={stats?.total_detections || 0} icon="📊" tint="from-sky-400 to-sky-600" />
        <KPICard title="Найдено воробьёв" value={stats?.total_sparrows || 0} icon="🐦" tint="from-forest-400 to-forest-600" />
        <KPICard title="В среднем на фото" value={(stats?.avg_per_image || 0).toFixed(1)} icon="📈" tint="from-amber-400 to-orange-500" />
        <KPICard title="Среднее время" value={`${(stats?.avg_processing_time || 0).toFixed(0)} мс`} icon="⚡" tint="from-violet-400 to-purple-600" />
      </div>

      {/* Chart */}
      <section className="glass rounded-3xl p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-forest-100 text-xl">📅</span>
          <div>
            <h2 className="font-display text-xl font-bold text-forest-800">Динамика детекций</h2>
            <p className="text-sm text-forest-600/60">Количество найденных птиц во времени</p>
          </div>
        </div>
        <StatsChart />
      </section>

      {/* Recent */}
      <section className="glass rounded-3xl p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 text-xl">🕒</span>
          <h2 className="font-display text-xl font-bold text-forest-800">Последние сканирования</h2>
        </div>
        {recent.length > 0 ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {recent.map((detection) => (
              <DetectionCard key={detection.id} detection={detection} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <span className="text-5xl">🪺</span>
            <p className="font-medium text-forest-700">Пока нет ни одной детекции</p>
            <button
              onClick={() => onNavigate?.('detect')}
              className="rounded-xl bg-forest-600 px-5 py-2.5 font-semibold text-white transition hover:bg-forest-700"
            >
              Загрузить первое фото
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

function KPICard({ title, value, icon, tint }) {
  return (
    <div className="group glass relative overflow-hidden rounded-3xl p-6 transition-transform hover:-translate-y-1">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${tint}`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-forest-600/70">{title}</p>
          <p className="mt-2 font-display text-3xl font-extrabold text-forest-800">{value}</p>
        </div>
        <span
          className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${tint} text-2xl shadow-lg transition-transform group-hover:scale-110`}
        >
          {icon}
        </span>
      </div>
    </div>
  )
}
