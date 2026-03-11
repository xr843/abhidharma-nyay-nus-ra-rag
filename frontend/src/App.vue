<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import ChatInput from './components/ChatInput.vue'
import ChatMessage from './components/ChatMessage.vue'
import HistoryPanel from './components/HistoryPanel.vue'
import DharmaWheelIcon from './components/DharmaWheelIcon.vue'
import api from './api'

// 状态
const messages = ref([])
const isLoading = ref(false)
const sessionId = ref(null)
const showHistory = ref(false)
const chatContainer = ref(null)

// 示例问题
const exampleQuestions = [
  '什么是"有漏"和"无漏"？',
  '顺正理论如何反驳经部的种子说？',
  '俱舍论的五蕴是什么？',
  '有部与经部的主要分歧是什么？'
]

// 发送消息
async function sendMessage(question) {
  if (!question.trim() || isLoading.value) return
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: question
  })
  
  isLoading.value = true
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  try {
    // 准备历史记录
    const history = messages.value.slice(-10).map(m => ({
      role: m.role,
      content: m.content
    }))
    
    // 调用API
    const response = await api.chat({
      question,
      session_id: sessionId.value,
      history: history.slice(0, -1) // 不包含刚添加的用户消息
    })
    
    // 更新session ID
    sessionId.value = response.session_id
    
    // 添加AI回复
    messages.value.push({
      role: 'assistant',
      content: response.answer,
      citations: response.citations,
      relatedQuestions: response.related_questions
    })
    
  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，处理您的问题时出现了错误。请稍后重试。',
      isError: true
    })
  } finally {
    isLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

// 处理相关问题点击
function handleRelatedQuestion(question) {
  sendMessage(question)
}

// 滚动到底部
function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// 新对话
function startNewChat() {
  messages.value = []
  sessionId.value = null
}

// 加载历史会话
async function loadSession(session) {
  try {
    sessionId.value = session.id
    // 可以从API加载完整的会话消息
    // 这里简化处理，只显示第一个问题
    messages.value = [{
      role: 'user',
      content: session.first_question
    }]
    showHistory.value = false
  } catch (error) {
    console.error('加载会话失败:', error)
  }
}
</script>

<template>
  <div class="min-h-screen bg-pattern flex flex-col">
    <!-- 头部 -->
    <header class="flex-shrink-0 header-bar">
      <div class="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-3xl">📚</span>
          <h1 class="text-xl font-serif font-bold" style="color: #6b5a3d;">
            《顺正理论》资料库
          </h1>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="startNewChat"
            class="btn-secondary flex items-center gap-2"
          >
            <span>✨</span>
            <span>新对话</span>
          </button>
          <button
            @click="showHistory = !showHistory"
            class="btn-secondary flex items-center gap-2"
          >
            <span>📜</span>
            <span>历史</span>
          </button>
        </div>
      </div>
    </header>
    
    <!-- 主内容区 -->
    <main class="flex-1 flex overflow-hidden">
      <!-- 对话区域 -->
      <div class="flex-1 flex flex-col">
        <!-- 消息列表 -->
        <div
          ref="chatContainer"
          class="flex-1 overflow-y-auto px-4 py-6"
        >
          <div class="max-w-4xl mx-auto">
            <!-- 欢迎界面 -->
            <div
              v-if="messages.length === 0"
              class="text-center py-20 animate-fade-in"
            >
              <div class="flex justify-center mb-6 dharma-wheel-icon">
                <DharmaWheelIcon :size="80" color="#6b5a3d" />
              </div>
              <h2 class="text-2xl font-serif mb-4" style="color: #6b5a3d;">
                《顺正理论》智能问答
              </h2>
              <p class="text-gray-600 mb-8 max-w-lg mx-auto">
                收录《俱舍论》、《顺正理论》、《俱舍论记》、《俱舍论疏》四部论典原文，
                辅助研习俱舍要义
              </p>
              
              <!-- 示例问题 -->
              <div class="flex flex-wrap justify-center gap-3 max-w-2xl mx-auto">
                <button
                  v-for="q in exampleQuestions"
                  :key="q"
                  @click="sendMessage(q)"
                  class="example-btn px-4 py-2 rounded-full text-sm"
                >
                  {{ q }}
                </button>
              </div>
            </div>
            
            <!-- 消息列表 -->
            <div v-else class="space-y-6">
              <ChatMessage
                v-for="(msg, idx) in messages"
                :key="idx"
                :message="msg"
                @ask="handleRelatedQuestion"
              />
              
              <!-- 加载中 -->
              <div
                v-if="isLoading"
                class="flex items-start gap-4 animate-fade-in"
              >
                <div class="w-10 h-10 rounded-full flex items-center justify-center text-xl" style="background: linear-gradient(135deg, #6b5a3d 0%, #5a4a32 100%);">
                  🤖
                </div>
                <div class="card flex-1">
                  <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span class="ml-3 text-gray-500">正在思考...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 输入区域 -->
        <div class="flex-shrink-0 input-area">
          <div class="max-w-4xl mx-auto px-4 py-4">
            <ChatInput
              @send="sendMessage"
              :disabled="isLoading"
            />
          </div>
        </div>
      </div>
      
      <!-- 历史面板 -->
      <HistoryPanel
        v-if="showHistory"
        @close="showHistory = false"
        @select="loadSession"
      />
    </main>
  </div>
</template>
