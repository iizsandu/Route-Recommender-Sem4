import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { 
  extractArticles, 
  extractGoogleNews,
  extractTimesOfIndia,
  extractNewsData,
  extractHindu,
  extractNDTV,
  extractIndianExpress,
  cancelExtraction,
  getNewsDataCredits,
  getArticles, 
  getArticles2, 
  getArticleStats 
} from '../services/api';
import mockData from '../data/db_mock.json';
import './ArticleExtractor.css';

// ── Chart helpers ─────────────────────────────────────────────────────────────
// DATA SOURCE: currently reads from src/data/db_mock.json (static import).
// To connect MongoDB, replace `mockData` with an API response:
//   const [chartDocs, setChartDocs] = useState([]);
//   useEffect(() => { fetch('/articles/date-stats').then(r=>r.json()).then(setChartDocs) }, []);
// The API should return an array of { url, date: "YYYY-MM-DD", source } objects.
// Then pass `chartDocs` instead of `mockData` into buildChartData().

const CHART_SOURCES = ['All Sources', 'Google News', 'Times of India', 'NDTV', 'The Hindu', 'Indian Express', 'NewsData.io'];
const CHART_GRANULARITIES = [{ label: 'Week', value: 'week' }, { label: 'Month', value: 'month' }, { label: 'Year', value: 'year' }];
const SOURCE_COLORS = {
  'Google News': '#3498db', 'Times of India': '#e74c3c', 'NDTV': '#2ecc71',
  'The Hindu': '#9b59b6', 'Indian Express': '#f39c12', 'NewsData.io': '#1abc9c', 'All Sources': '#3498db',
};

function getBucketKey(dateStr, granularity) {
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  if (granularity === 'year') return `${d.getFullYear()}`;
  if (granularity === 'month') return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  const jan1 = new Date(d.getFullYear(), 0, 1);
  const week = Math.ceil(((d - jan1) / 86400000 + jan1.getDay() + 1) / 7);
  return `${d.getFullYear()}-W${String(week).padStart(2, '0')}`;
}

function buildChartData(docs, granularity) {
  const counts = {};
  for (const doc of docs) {
    const key = getBucketKey(doc.date, granularity);
    if (key) counts[key] = (counts[key] || 0) + 1;
  }
  return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).map(([label, count]) => ({ label, count }));
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#2c3e50', color: '#fff', padding: '8px 14px', borderRadius: 6, fontSize: 13 }}>
      <p style={{ margin: '0 0 2px', fontWeight: 600 }}>{label}</p>
      <p style={{ margin: 0, opacity: 0.85 }}>{payload[0].value} article{payload[0].value !== 1 ? 's' : ''}</p>
    </div>
  );
}

function ArticleExtractor() {
  const [articles, setArticles] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [extractionMethod, setExtractionMethod] = useState('all');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [extractionSummary, setExtractionSummary] = useState(null);
  const [viewCollection, setViewCollection] = useState('articles2');
  const [newsDataCredits, setNewsDataCredits] = useState(null);

  // Chart state
  const [chartSource, setChartSource] = useState('All Sources');
  const [chartGranularity, setChartGranularity] = useState('month');
  const chartFiltered = useMemo(() =>
    chartSource === 'All Sources' ? mockData : mockData.filter(d => d.source === chartSource),
    [chartSource]
  );
  const chartData = useMemo(() => buildChartData(chartFiltered, chartGranularity), [chartFiltered, chartGranularity]);

  // Resizable panel
  const [chartWidth, setChartWidth] = useState(360);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const onMouseDown = useCallback((e) => {
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = chartWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [chartWidth]);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!isResizing.current) return;
      const delta = startX.current - e.clientX; // dragging left = wider chart
      const newWidth = Math.min(900, Math.max(260, startWidth.current + delta));
      setChartWidth(newWidth);
    };
    const onMouseUp = () => {
      if (!isResizing.current) return;
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  useEffect(() => {
    loadArticles();
    loadStats();
    loadNewsDataCredits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewCollection]);

  const loadNewsDataCredits = async () => {
    try {
      const data = await getNewsDataCredits();
      if (data.success) {
        setNewsDataCredits(data.credits);
      }
    } catch (err) {
      console.error('Failed to load NewsData credits:', err);
    }
  };

  const loadArticles = async () => {
    try {
      const data = viewCollection === 'articles2' 
        ? await getArticles2(20) 
        : await getArticles(20);
      setArticles(data.articles);
    } catch (err) {
      console.error('Failed to load articles:', err);
    }
  };

  const loadStats = async () => {
    try {
      const data = await getArticleStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setStats({ total: 0, breakdown: {} });
    }
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelExtraction();
      setSuccessMessage('Cancellation signal sent. Waiting for extraction to stop and save...');
    } catch (err) {
      setError('Failed to send cancel signal: ' + err.message);
    }
  };

  const handleExtract = async () => {
      setLoading(true);
      setError('');
      setSuccessMessage('');
      setExtractionSummary(null);

      try {
        let result;
        
        switch(extractionMethod) {
          case 'google':
            setSuccessMessage('Starting Google News extraction...');
            result = await extractGoogleNews();
            break;
          case 'toi':
            setSuccessMessage('Starting Times of India extraction...');
            result = await extractTimesOfIndia();
            break;
          case 'hindu':
            setSuccessMessage('Starting The Hindu extraction...');
            result = await extractHindu();
            break;
          case 'ndtv':
            setSuccessMessage('Starting NDTV extraction...');
            result = await extractNDTV();
            break;
          case 'ie':
            setSuccessMessage('Starting Indian Express extraction...');
            result = await extractIndianExpress();
            break;
          case 'newsdata':
            setSuccessMessage('Starting NewsData.io extraction (200 credits)...');
            result = await extractNewsData();
            break;
          case 'all':
          default:
            setSuccessMessage('Starting extraction using ALL methods... Auto-save every 50 articles.');
            result = await extractArticles(120);
            break;
        }

        if (result.success) {
          const s = result.stats;

          if (extractionMethod === 'all') {
            setSuccessMessage(
              `Extraction completed! Cycles: ${s.cycles}, Total URLs: ${s.total_urls}, ` +
              `Extracted: ${s.total_extracted}, Time: ${s.elapsed_minutes} min`
            );
          } else {
            setSuccessMessage(
              `${s.method} extraction completed! New articles: ${s.new_articles}, Total URLs: ${s.total_urls}` +
              (s.credits_used ? `, Credits used: ${s.credits_used}` : '') +
              (s.credits_remaining !== undefined ? `, Remaining: ${s.credits_remaining}` : '') +
              (s.hours_until_reset !== undefined ? `, Reset in: ${s.hours_until_reset}h ${s.minutes_until_reset}m` : '')
            );
          }

          // Store breakdown for summary table
          if (s.source_breakdown) {
            setExtractionSummary({
              breakdown: s.source_breakdown,
              elapsed_minutes: s.elapsed_minutes || null,
              total_extracted: s.total_extracted || s.new_articles || 0,
            });
          }

          await loadArticles();
          await loadStats();
          await loadNewsDataCredits();
        } else {
          setError(result.message || 'Failed to extract articles');
        }
      } catch (err) {
        setError(err.message || 'Failed to extract articles');
      } finally {
        setLoading(false);
        setCancelling(false);
      }
    };

  return (
    <div className="article-extractor-page">

      {/* ── Left column: existing extractor UI ── */}
      <div className="article-extractor">
        <div className="extractor-header">
        <h2>Crime Article Extractor</h2>
        <p>Extract crime news articles from multiple sources</p>
      </div>

      <div className="extractor-controls">
        <div className="method-selector">
          <label>Extraction Method:</label>
          <select 
            value={extractionMethod} 
            onChange={(e) => setExtractionMethod(e.target.value)}
            disabled={loading}
          >
            <option value="all">All Methods (6 sources)</option>
            <option value="google">Google News</option>
            <option value="toi">Times of India</option>
            <option value="hindu">The Hindu</option>
            <option value="ndtv">NDTV</option>
            <option value="ie">Indian Express</option>
            <option value="newsdata">
              NewsData.io
              {newsDataCredits && ` (${newsDataCredits.credits_remaining}/${newsDataCredits.max_credits} credits)`}
            </option>
          </select>
        </div>

        {extractionMethod === 'newsdata' && newsDataCredits && (
          <div className="credit-info">
            <div className="credit-status">
              <span className="credit-label">Daily Credits:</span>
              <span className="credit-value">{newsDataCredits.credits_remaining}/{newsDataCredits.max_credits}</span>
            </div>
            <div className="credit-status">
              <span className="credit-label">Daily Reset In:</span>
              <span className="credit-value">{newsDataCredits.hours_until_reset}h {newsDataCredits.minutes_until_reset}m</span>
            </div>
            <div className="credit-status">
              <span className="credit-label">Window (15 min):</span>
              <span className="credit-value">
                {newsDataCredits.window_remaining}/{newsDataCredits.window_max} remaining
                {newsDataCredits.window_wait_seconds > 0 && (
                  <span className="credit-warning-inline">
                    {' '}— full, resets in {Math.floor(newsDataCredits.window_wait_seconds / 60)}m {newsDataCredits.window_wait_seconds % 60}s
                  </span>
                )}
              </span>
            </div>
            {newsDataCredits.credits_remaining <= 0 && (
              <div className="credit-warning">
                No daily credits left. Please wait for reset.
              </div>
            )}
          </div>
        )}

        <button 
          onClick={handleExtract} 
          disabled={loading}
          className="extract-button"
        >
          {loading ? 'Extracting Articles...' : 'Extract Articles'}
        </button>

        {loading && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="cancel-button"
          >
            {cancelling ? 'Cancelling...' : 'Cancel Extraction'}
          </button>
        )}

        <div className="collection-toggle">
          <label>View Collection: </label>
          <select 
            value={viewCollection} 
            onChange={(e) => setViewCollection(e.target.value)}
            className="collection-select"
          >
            <option value="articles2">All Sources (articles2)</option>
            <option value="articles">Times of India (articles)</option>
          </select>
        </div>

        {stats && (
          <div className="stats-box">
            <div className="stat-item stat-total">
              <span className="stat-label">Total Articles</span>
              <span className="stat-value">{stats.total ?? 0}</span>
            </div>
            {stats.breakdown && Object.entries(stats.breakdown).map(([source, count]) => (
              <div key={source} className="stat-item">
                <span className="stat-label">{source}</span>
                <span className="stat-value">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      {error && (
        <div className="error-message">{error}</div>
      )}

      {extractionSummary && (
        <div className="extraction-summary">
          <h3>Extraction Summary</h3>
          <table className="summary-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Articles Saved</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(extractionSummary.breakdown).map(([source, count]) => (
                <tr key={source} className={count > 0 ? 'summary-row-active' : 'summary-row-zero'}>
                  <td>{source}</td>
                  <td>{count}</td>
                </tr>
              ))}
              <tr className="summary-row-total">
                <td>TOTAL</td>
                <td>{Object.values(extractionSummary.breakdown).reduce((a, b) => a + b, 0)}</td>
              </tr>
            </tbody>
          </table>
          {extractionSummary.elapsed_minutes && (
            <p className="summary-time">Time elapsed: {extractionSummary.elapsed_minutes} min</p>
          )}
        </div>
      )}

      <div className="articles-list">
        <h3>Recent Articles ({articles.length})</h3>
        {articles.length === 0 ? (
          <p className="no-articles">No articles yet. Click "Extract Articles" to get started.</p>
        ) : (
          <div className="articles-grid">
            {articles.map((article, index) => (
              <div key={index} className="article-card">
                <div className="article-source">{article.source}</div>
                <h4 className="article-title">{article.title}</h4>
                {article.description && (
                  <p className="article-description">{article.description}</p>
                )}
                <div className="article-footer">
                  <span className="article-date">
                    {new Date(article.extracted_at).toLocaleDateString()}
                  </span>
                  <a 
                    href={article.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="article-link"
                  >
                    Read More →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>

      {/* ── Drag handle ── */}
      <div className="panel-resizer" onMouseDown={onMouseDown} title="Drag to resize" />

      {/* ── Right column: date distribution chart ── */}
      <div className="chart-panel" style={{ width: chartWidth, minWidth: chartWidth }}>
        <h3 className="chart-panel-title">Article Date Distribution</h3>
        <p className="chart-panel-sub">Coverage per source in the database</p>

        {/* Source selector */}
        <div className="chart-control-group">
          <span className="chart-control-label">Source</span>
          <div className="chart-source-btns">
            {CHART_SOURCES.map(src => (
              <button
                key={src}
                className={`chart-src-btn ${chartSource === src ? 'active' : ''}`}
                style={chartSource === src ? { background: SOURCE_COLORS[src], borderColor: SOURCE_COLORS[src] } : {}}
                onClick={() => setChartSource(src)}
              >
                {src}
              </button>
            ))}
          </div>
        </div>

        {/* Granularity selector */}
        <div className="chart-control-group">
          <span className="chart-control-label">Group by</span>
          <div className="chart-gran-btns">
            {CHART_GRANULARITIES.map(g => (
              <button
                key={g.value}
                className={`chart-gran-btn ${chartGranularity === g.value ? 'active' : ''}`}
                onClick={() => setChartGranularity(g.value)}
              >
                {g.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="chart-area">
          {chartData.length === 0
            ? <p className="chart-no-data">No data for this source.</p>
            : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chartData} margin={{ top: 8, right: 10, left: -10, bottom: 55 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="label" angle={-45} textAnchor="end" tick={{ fontSize: 10, fill: '#666' }} interval={0} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#666' }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={SOURCE_COLORS[chartSource] || '#3498db'} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          }
        </div>

        {/*
          HOW TO CONNECT MONGODB:
          1. Add backend route GET /articles/date-stats returning [{ url, date: "YYYY-MM-DD", source }]
          2. Add getDateStats() to api.js
          3. Replace `import mockData` with a useEffect that calls getDateStats() into state
          4. Pass that state variable to buildChartData() instead of mockData
        */}
        <p className="chart-mock-note">
          Mock data shown — connect MongoDB to see real coverage
        </p>
      </div>

    </div>
  );
}

export default ArticleExtractor;
