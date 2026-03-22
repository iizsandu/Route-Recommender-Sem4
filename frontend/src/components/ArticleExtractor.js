import React, { useState, useEffect } from 'react';
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
import './ArticleExtractor.css';

function ArticleExtractor() {
  const [articles, setArticles] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [extractionMethod, setExtractionMethod] = useState('all');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [viewCollection, setViewCollection] = useState('articles2');
  const [newsDataCredits, setNewsDataCredits] = useState(null);

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
      console.log('Stats loaded:', data); // Debug log
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
      // Set default stats structure on error
      setStats({
        total: 0,
        articles: { total: 0, collection: 'articles', source: 'Times of India' },
        articles2: { total: 0, collection: 'articles2', source: 'Google News' }
      });
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
          if (extractionMethod === 'all') {
            setSuccessMessage(
              `Extraction completed! ` +
              `Cycles: ${result.stats.cycles}, ` +
              `Total URLs: ${result.stats.total_urls}, ` +
              `Extracted: ${result.stats.total_extracted}, ` +
              `Time: ${result.stats.elapsed_minutes} minutes`
            );
          } else {
            setSuccessMessage(
              `${result.stats.method} extraction completed! ` +
              `New articles: ${result.stats.new_articles}, ` +
              `Total URLs: ${result.stats.total_urls}` +
              (result.stats.credits_used ? `, Credits used: ${result.stats.credits_used}` : '') +
              (result.stats.credits_remaining !== undefined ? `, Remaining: ${result.stats.credits_remaining}` : '') +
              (result.stats.hours_until_reset !== undefined ? `, Reset in: ${result.stats.hours_until_reset}h ${result.stats.minutes_until_reset}m` : '')
            );
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
              <span className="credit-label">📊 Credits Available:</span>
              <span className="credit-value">{newsDataCredits.credits_remaining}/{newsDataCredits.max_credits}</span>
            </div>
            <div className="credit-status">
              <span className="credit-label">⏰ Reset In:</span>
              <span className="credit-value">{newsDataCredits.hours_until_reset}h {newsDataCredits.minutes_until_reset}m</span>
            </div>
            {!newsDataCredits.can_use && (
              <div className="credit-warning">
                ⚠️ No credits available. Please wait for reset.
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
            <option value="articles2">
              All Sources (articles2){stats?.articles2?.total ? ` - ${stats.articles2.total} articles` : ''}
            </option>
            <option value="articles">
              Times of India (articles){stats?.articles?.total ? ` - ${stats.articles.total} articles` : ''}
            </option>
          </select>
        </div>

        {stats && (
          <div className="stats-box">
            <div className="stat-item">
              <span className="stat-label">Total Articles:</span>
              <span className="stat-value">{stats.total || 0}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">All Sources (articles2):</span>
              <span className="stat-value">{stats.articles2?.total || 0}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Times of India (articles):</span>
              <span className="stat-value">{stats.articles?.total || 0}</span>
            </div>
          </div>
        )}
      </div>

      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      {error && (
        <div className="error-message">{error}</div>
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
  );
}

export default ArticleExtractor;
