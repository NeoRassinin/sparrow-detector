import { useState, useEffect } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { statsAPI } from '../lib/api'

const PERIODS = [
  { id: 'day', label: 'День' },
  { id: 'week', label: 'Неделя' },
  { id: 'month', label: 'Месяц' },
]

export default function StatsChart() {
  const [data, setData] = useState([])
  const [period, setPeriod] = useState('day')

  useEffect(() => {
    loadTimeseries()
  }, [period])

  const loadTimeseries = async () => {
    try {
      const result = await statsAPI.timeseries(period)
      setData(result.data)
    } catch (error) {
      console.error('Failed to load timeseries:', error)
    }
  }

  return (
    <div className="space-y-4">
      <div className="inline-flex gap-1 rounded-xl bg-forest-900/5 p-1">
        {PERIODS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPeriod(p.id)}
            className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition ${
              period === p.id
                ? 'bg-white text-forest-700 shadow-soft'
                : 'text-forest-700/50 hover:text-forest-700'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {data.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="sparrowGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#34955b" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#34955b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#dcf2e3" />
            <XAxis dataKey="period" stroke="#247848" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#247848" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                borderRadius: '14px',
                border: '1px solid #bce4cb',
                boxShadow: '0 10px 40px -12px rgba(21,62,42,0.25)',
                fontFamily: 'Inter, sans-serif',
              }}
              labelStyle={{ color: '#194c31', fontWeight: 700 }}
            />
            <Area
              type="monotone"
              dataKey="sparrows"
              stroke="#247848"
              strokeWidth={3}
              fill="url(#sparrowGrad)"
              name="Воробьёв"
              dot={{ fill: '#34955b', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-72 flex-col items-center justify-center gap-2 text-forest-600/50">
          <span className="text-4xl">📭</span>
          <span className="text-sm">Пока нет данных</span>
        </div>
      )}
    </div>
  )
}
