import React, { useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import mockData from '../data/db_mock.json';
import './DateRangeAnalytics.css';

// ── Constants ────────────────────────────────────────────────────────────────

const SOURCES = ['All Sources', 'Google News', 'Times of India', 'NDTV', 'The Hindu', 'Indian Express', 'NewsData.io'];

const GRANULARITIES = [
  { label: 'By Week',  value: 'week' },
  { label: 'By Month', value: 'month' },
  { label: 'By Year',  value: 'year' },
];

const SOURCE_COLORS = {
  'Google News':    '#3498db',
  'Times of India': '#e74c3c',
  'NDTV':           '#2ecc71',
  'The Hindu':      '#9b59b6',
  'Indian Express': '#f39c12',
  'NewsData.io':    '#1abc9c',
  'All Sources':    '#3498db',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function getBucketKey(dateStr, granularity) {
  const d = new Date(dateStr);
  if (isNaN(d)) return null;

  if (granularity === 'year') {
    return `${d.getFullYear()}`;
  }
  if (granularity === 'month') {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  }
  // week: ISO week label  YYYY-Www
  const jan1 = new Date(d.getFullYear(), 0, 1);
  const week = Math.ceil(((d - jan1) / 86400000 + jan1.getDay() + 1) / 7);
  return `${d.getFullYear()}-W${String(week).padStart(2, '0')}`;
}

function buildChartData(docs, granularity) {
  const counts = {};
  for (const doc of docs) {
    const key = getBucketKey(doc.date, granularity);
    if (!key) continue;
    counts[key] = (counts[key] || 0) + 1;
  }
  return Object.entries(counts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([label, count]) => ({ label, count }));
}

// ── Custom Tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="tooltip-label">{label}</p>
      <p className="tooltip-value">{payload[0].value} article{payload[0].value !== 1 ? 's' : ''}</p>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function DateRangeAnalytics() {
  const [selectedSource, setSelectedSource] = useState('All Sources');
  const [granularity, setGranularity] = useState('month');

  const filtered = useMemo(() => {
    return selectedSource === 'All Sources'
      ? mockData
      : mockData.filter(d => d.source === selectedSource);
  }, [selectedSource]);

  const chartData = useMemo(() => buildChartData(filtered, granularity), [filtered, granularity]);

  const stats = useMemo(() => {
    if (!chartData.length) return null;
    const max = Math.max(...chartData.map(d => d.count));
    const peak = chartData.find(d => d.count === max);
    return {
      total: filtered.length,
      buckets: chartData.length,
      peak: peak?.label,
      peakCount: max,
      earliest: chartData[0]?.label,
      latest: chartData[chartData.length - 1]?.label,
    };
  }, [chartData, filtered]);

  const barColor = SOURCE_COLORS[selectedSource] || '#3498db';

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h2>Article Date Distribution</h2>
        <p className="analytics-subtitle">
          Understand which date ranges are covered per source — helps decide where to focus future extractions.
        </p>
      </div>

      {/* Controls */}
      <div className="controls-row">
        <div className="control-group">
          <label>Source</label>
          <div className="source-buttons">
            {SOURCES.map(src => (
              <button
                key={src}
                className={`source-btn ${selectedSource === src ? 'active' : ''}`}
                style={selectedSource === src ? { background: SOURCE_COLORS[src], borderColor: SOURCE_COLORS[src] } : {}}
                onClick={() => setSelectedSource(src)}
              >
                {src}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>Granularity</label>
          <div className="granularity-buttons">
            {GRANULARITIES.map(g => (
              <button
                key={g.value}
                className={`gran-btn ${granularity === g.value ? 'active' : ''}`}
                onClick={() => setGranularity(g.value)}
              >
                {g.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats strip */}
      {stats && (
        <div className="stats-strip">
          <div className="stat-card">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">Total Articles</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.buckets}</span>
            <span className="stat-label">Buckets</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.earliest}</span>
            <span className="stat-label">Earliest</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.latest}</span>
            <span className="stat-label">Latest</span>
          </div>
          <div className="stat-card highlight">
            <span className="stat-value">{stats.peak}</span>
            <span className="stat-label">Peak ({stats.peakCount} articles)</span>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="chart-wrapper">
        {chartData.length === 0 ? (
          <div className="no-data">No articles found for this source.</div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis
                dataKey="label"
                angle={-45}
                textAnchor="end"
                tick={{ fontSize: 11, fill: '#555' }}
                interval={0}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 12, fill: '#555' }}
                label={{ value: 'Articles', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 12, fill: '#888' } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={barColor} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <p className="mock-notice">
        ⚠ Showing mock data — replace <code>src/data/db_mock.json</code> with a real API call to connect MongoDB.
      </p>
    </div>
  );
}
