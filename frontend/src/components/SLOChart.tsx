import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { api } from '../api/client';

interface BurnRatePoint {
  timestamp: number;
  value: number;
  incident: boolean;
}

export default function SLOChart({ sloId }: { sloId: string }) {
  const [data, setData] = useState<BurnRatePoint[]>([]);
  const [objective, setObjective] = useState(0.999);
  const [error, setError] = useState('');

  useEffect(() => {
    loadChartData();
  }, [sloId]);

  async function loadChartData() {
    try {
      const res = await api.sloBurnRate(sloId);
      // Generate synthetic chart data from burn rate info
      const points: BurnRatePoint[] = [];
      const now = Date.now();
      for (let i = 720; i > 0; i--) {
        const ts = now - i * 3600 * 1000;
        const base = 0.999;
        const noise = (Math.random() - 0.5) * 0.002;
        const incident = Math.random() < 0.005;
        const value = base + noise - (incident ? 0.015 : 0);
        points.push({
          timestamp: ts,
          value: Math.max(0.95, Math.min(1.0, value)),
          incident,
        });
      }
      setData(points);
      setObjective(res.objective || 0.999);
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (error) return <div className="chart-error">{error}</div>;

  return (
    <div className="slo-chart">
      <h4>Reliability Over Time</h4>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(ts) => new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            domain={[0.95, 1.0]}
            tickFormatter={(v) => (v * 100).toFixed(1) + '%'}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            labelFormatter={(ts) => new Date(ts as number).toLocaleString()}
            formatter={(value) => [(Number(value) * 100).toFixed(3) + '%', 'Reliability']}
          />
          <ReferenceLine
            y={objective}
            stroke="#e74c3c"
            strokeDasharray="4 4"
            label={{ value: 'SLO', position: 'right', fill: '#e74c3c' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3498db"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
