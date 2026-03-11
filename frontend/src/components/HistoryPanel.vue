<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const emit = defineEmits(['close', 'select'])

const sessions = ref([])
const loading = ref(false)
const error = ref(null)

onMounted(async () => {
  await loadHistory()
})

async function loadHistory() {
  loading.value = true
  error.value = null
  
  try {
    const response = await api.getHistory({ limit: 50 })
    sessions.value = response.sessions || []
  } catch (e) {
    error.value = '加载历史记录失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function deleteSession(session, e) {
  e.stopPropagation()
  
  if (!confirm('确定要删除这条历史记录吗？')) return
  
  try {
    await api.deleteSession(session.id)
    sessions.value = sessions.value.filter(s => s.id !== session.id)
  } catch (e) {
    console.error('删除失败:', e)
  }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  })
}
</script>

<template>
  <div class="w-80 border-l border-gray-200 bg-white flex flex-col shadow-lg">
    <!-- 头部 -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
      <h3 class="font-medium" style="color: #8b6914;">📜 历史记录</h3>
      <button
        @click="emit('close')"
        class="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center
               text-gray-400 hover:text-gray-600 transition-colors"
      >
        ✕
      </button>
    </div>
    
    <!-- 内容 -->
    <div class="flex-1 overflow-y-auto">
      <!-- 加载中 -->
      <div v-if="loading" class="p-4 text-center text-gray-400">
        <div class="loading-dots justify-center">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
      
      <!-- 错误 -->
      <div v-else-if="error" class="p-4 text-center text-red-500">
        {{ error }}
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="sessions.length === 0" class="p-8 text-center text-gray-400">
        <div class="text-4xl mb-3">📭</div>
        <p>暂无历史记录</p>
      </div>
      
      <!-- 历史列表 -->
      <div v-else class="p-2">
        <div
          v-for="session in sessions"
          :key="session.id"
          @click="emit('select', session)"
          class="p-3 rounded-lg hover:bg-gray-50 cursor-pointer group
                 transition-colors duration-200 border border-transparent hover:border-gray-200"
        >
          <div class="flex items-start gap-2">
            <span class="text-gray-400 mt-0.5">💬</span>
            <div class="flex-1 min-w-0">
              <p class="text-gray-700 text-sm line-clamp-2">
                {{ session.first_question }}
              </p>
              <div class="flex items-center gap-2 mt-1 text-xs text-gray-400">
                <span>{{ formatDate(session.updated_at) }}</span>
                <span>·</span>
                <span>{{ session.message_count }} 条消息</span>
              </div>
            </div>
            <button
              @click="deleteSession(session, $event)"
              class="opacity-0 group-hover:opacity-100 p-1 rounded
                     hover:bg-gray-200 text-gray-400 hover:text-red-500
                     transition-all duration-200"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
