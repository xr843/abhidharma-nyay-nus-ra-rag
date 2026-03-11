/**
 * API服务模块
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000, // AI响应可能需要较长时间（3分钟，优化后通常 20-50秒，但复杂问题可能需要更长）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    throw error
  }
)

export default {
  /**
   * 发送对话请求
   */
  async chat({ question, session_id, history }) {
    return api.post('/chat', {
      question,
      session_id,
      history
    })
  },
  
  /**
   * 获取历史记录
   */
  async getHistory({ session_id, limit = 20, offset = 0 } = {}) {
    const params = { limit, offset }
    if (session_id) params.session_id = session_id
    return api.get('/history', { params })
  },
  
  /**
   * 删除会话
   */
  async deleteSession(sessionId) {
    return api.delete(`/history/${sessionId}`)
  },
  
  /**
   * 获取文献列表
   */
  async getTexts() {
    return api.get('/texts')
  },
  
  /**
   * 获取统计信息
   */
  async getStats() {
    return api.get('/stats')
  },
  
  /**
   * 健康检查
   */
  async health() {
    return api.get('/health')
  }
}

