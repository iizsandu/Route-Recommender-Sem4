import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const extractArticles = async (timeoutMinutes = 120) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/articles/extract-all`, null, {
      params: { timeout_minutes: timeoutMinutes }
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract articles');
  }
};

export const extractGoogleNews = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/articles/extract-google-news`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract from Google News');
  }
};

export const extractTimesOfIndia = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/articles/extract-times-of-india`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract from Times of India');
  }
};

export const extractNewsData = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/articles/extract-newsdata`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract from NewsData.io');
  }
};

export const getNewsDataCredits = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/articles/newsdata-credits`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to get credit status');
  }
};

export const getArticles = async (limit = 50, skip = 0) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/articles`, {
      params: { limit, skip }
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch articles');
  }
};

export const getArticles2 = async (limit = 50, skip = 0) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/articles2`, {
      params: { limit, skip }
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch articles from articles2');
  }
};

export const getArticleStats = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/articles/stats`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch stats');
  }
};

export const getYouTubeChannels = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/youtube/channels`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch channels');
  }
};

export const extractYouTubeLive = async (channel, duration = 60, language = null) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/youtube/extract`, {
      channel,
      duration,
      language
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract YouTube live');
  }
};

export const extractYouTubeURL = async (url, language = null) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/youtube/extract-url`, {
      url,
      language
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to extract YouTube video');
  }
};
