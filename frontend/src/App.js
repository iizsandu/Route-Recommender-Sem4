import React, { useState } from 'react';
import ArticleExtractor from './components/ArticleExtractor';
import YouTubeExtractor from './components/YouTubeExtractor';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('articles');

  return (
    <div className="app">
      <div className="header">
        <h1>Delhi Crime Data Collector</h1>
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'articles' ? 'active' : ''}`}
            onClick={() => setActiveTab('articles')}
          >
            Article Extractor
          </button>
          <button
            className={`tab ${activeTab === 'youtube' ? 'active' : ''}`}
            onClick={() => setActiveTab('youtube')}
          >
            YouTube Live
          </button>
        </div>
      </div>

      {activeTab === 'articles' && <ArticleExtractor />}
      {activeTab === 'youtube' && <YouTubeExtractor />}
    </div>
  );
}

export default App;
