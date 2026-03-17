import React, { useState, useEffect } from 'react';
import { extractYouTubeLive, extractYouTubeURL, getYouTubeChannels } from '../services/api';
import './YouTubeExtractor.css';

function YouTubeExtractor() {
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [result, setResult] = useState(null);
  
  // URL extraction state
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);

  useEffect(() => {
    loadChannels();
  }, []);

  const loadChannels = async () => {
    try {
      const data = await getYouTubeChannels();
      setChannels(data.channels);
      if (data.channels.length > 0) {
        setSelectedChannel(data.channels[0]);
      }
    } catch (err) {
      console.error('Failed to load channels:', err);
    }
  };

  const handleExtract = async () => {
    if (!selectedChannel) {
      setError('Please select a channel');
      return;
    }

    setLoading(true);
    setError('');
    setSuccessMessage('');
    setResult(null);

    try {
      const data = await extractYouTubeLive(
        selectedChannel,
        duration,
        language === 'auto' ? null : language
      );

      if (data.success) {
        setSuccessMessage(data.message);
        setResult(data.data);
      } else {
        setError(data.message || 'Failed to extract YouTube live stream');
      }
    } catch (err) {
      setError(err.message || 'Failed to extract YouTube live stream');
    } finally {
      setLoading(false);
    }
  };

  const handleUrlExtract = async () => {
    if (!youtubeUrl.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }

    setUrlLoading(true);
    setError('');
    setSuccessMessage('');
    setResult(null);

    try {
      const data = await extractYouTubeURL(
        youtubeUrl,
        language === 'auto' ? null : language
      );

      if (data.success) {
        setSuccessMessage(data.message);
        setResult(data.data);
      } else {
        setError(data.message || 'Failed to extract YouTube video');
      }
    } catch (err) {
      setError(err.message || 'Failed to extract YouTube video');
    } finally {
      setUrlLoading(false);
    }
  };

  return (
    <div className="youtube-extractor">
      <div className="extractor-header">
        <h2>YouTube Live News Extractor</h2>
        <p>Extract and transcribe live news from YouTube channels</p>
      </div>

      <div className="extractor-form">
        <h3>Option 1: Live Channel Extraction</h3>
        <div className="form-group">
          <label>News Channel:</label>
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            disabled={loading || urlLoading}
          >
            {channels.map((channel) => (
              <option key={channel} value={channel}>
                {channel.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Duration (seconds):</label>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(parseInt(e.target.value))}
            min="30"
            max="300"
            disabled={loading || urlLoading}
          />
        </div>

        <div className="form-group">
          <label>Language:</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading || urlLoading}
          >
            <option value="auto">Auto-detect</option>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>
        </div>

        <button
          onClick={handleExtract}
          disabled={loading || urlLoading}
          className="extract-button-youtube"
        >
          {loading ? 'Processing... (This may take a few minutes)' : 'Extract Live Stream'}
        </button>
      </div>

      <div className="extractor-form" style={{ marginTop: '30px', borderTop: '2px solid #ddd', paddingTop: '20px' }}>
        <h3>Option 2: Extract from YouTube URL</h3>
        <div className="form-group">
          <label>YouTube Video URL:</label>
          <input
            type="text"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            disabled={loading || urlLoading}
            style={{ width: '100%', padding: '8px', fontSize: '14px' }}
          />
        </div>

        <button
          onClick={handleUrlExtract}
          disabled={loading || urlLoading}
          className="extract-button-youtube"
        >
          {urlLoading ? 'Processing... (This may take several minutes)' : 'Download & Transcribe Video'}
        </button>
      </div>

      {(loading || urlLoading) && (
        <div className="loading-info">
          <div className="spinner"></div>
          <p>Processing pipeline:</p>
          <ul>
            <li>📹 Downloading video from YouTube...</li>
            <li>🎵 Extracting audio...</li>
            <li>📝 Transcribing speech to text...</li>
            <li>💾 Saving to database...</li>
          </ul>
          <p className="note">This process may take 2-10 minutes depending on video length</p>
        </div>
      )}

      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      {error && (
        <div className="error-message">{error}</div>
      )}

      {result && (
        <div className="result-box">
          <h3>Extraction Results</h3>
          {result.channel && (
            <div className="result-item">
              <span className="result-label">Channel:</span>
              <span className="result-value">{result.channel.toUpperCase()}</span>
            </div>
          )}
          {result.url && (
            <div className="result-item">
              <span className="result-label">URL:</span>
              <span className="result-value">{result.url}</span>
            </div>
          )}
          <div className="result-item">
            <span className="result-label">Video Path:</span>
            <span className="result-value">{result.video_path}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Audio Path:</span>
            <span className="result-value">{result.audio_path}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Transcription Length:</span>
            <span className="result-value">{result.transcription_length} characters</span>
          </div>
          <div className="result-item">
            <span className="result-label">Saved to Database:</span>
            <span className="result-value">{result.saved_to_db ? '✓ Yes' : '✗ No'}</span>
          </div>
        </div>
      )}

      <div className="info-box">
        <h4>ℹ️ Requirements</h4>
        <ul>
          <li><strong>yt-dlp:</strong> pip install yt-dlp</li>
          <li><strong>ffmpeg:</strong> Install and add to PATH</li>
          <li><strong>whisper:</strong> pip install openai-whisper</li>
        </ul>
        <p className="note">
          This feature extracts video from YouTube (live streams or regular videos), converts to audio,
          and transcribes the speech to text using OpenAI Whisper. All transcriptions are saved to the 'youtube' collection in MongoDB.
        </p>
      </div>
    </div>
  );
}

export default YouTubeExtractor;
