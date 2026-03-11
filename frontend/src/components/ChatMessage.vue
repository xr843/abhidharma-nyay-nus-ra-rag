<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['ask'])

// 解析Markdown
const htmlContent = computed(() => {
  if (props.message.role === 'user') {
    return props.message.content
  }
  return marked.parse(props.message.content || '')
})

// 获取来源样式类
function getSourceClass(textId) {
  const classes = {
    'T1558': 'source-t1558',
    'T1562': 'source-t1562',
    'T1821': 'source-t1821',
    'T1822': 'source-t1822'
  }
  return classes[textId] || ''
}
</script>

<template>
  <div
    class="flex items-start gap-4 animate-fade-in"
    :class="message.role === 'user' ? 'flex-row-reverse' : ''"
  >
    <!-- 头像 -->
    <div
      class="w-10 h-10 rounded-full flex items-center justify-center text-xl flex-shrink-0"
      :class="message.role === 'user'
        ? 'bg-gray-100 border border-gray-200'
        : ''"
      :style="message.role === 'assistant' ? 'background: linear-gradient(135deg, #6b5a3d 0%, #5a4a32 100%);' : ''"
    >
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    
    <!-- 内容 -->
    <div
      class="flex-1 max-w-[85%]"
      :class="message.role === 'user' ? 'text-right' : ''"
    >
      <!-- 用户消息 -->
      <div
        v-if="message.role === 'user'"
        class="inline-block px-5 py-3 rounded-2xl rounded-tr-sm user-message font-medium"
      >
        {{ message.content }}
      </div>
      
      <!-- AI消息 -->
      <div v-else class="card ai-message">
        <!-- 主要回答 -->
        <div
          class="markdown-content"
          :class="{ 'text-red-500': message.isError }"
          v-html="htmlContent"
        ></div>
        
        <!-- 引用 -->
        <div v-if="message.citations?.length" class="mt-6">
          <h4 class="font-medium mb-3 flex items-center gap-2" style="color: #6b5a3d;">
            <span>📖</span>
            <span>相关引文</span>
          </h4>
          <div class="space-y-3">
            <div
              v-for="(cite, idx) in message.citations"
              :key="idx"
              class="citation-card"
              :class="getSourceClass(cite.text_id)"
            >
              <div class="flex items-center gap-2 text-sm text-gray-500 mb-2">
                <span>{{ cite.icon }}</span>
                <span class="font-medium text-gray-700">《{{ cite.short_title || cite.text_title }}》</span>
                <span>卷{{ cite.volume }}</span>
                <span v-if="cite.chapter" class="text-gray-400">{{ cite.chapter }}</span>
                <span class="ml-auto text-xs text-gray-400">
                  相关度: {{ (cite.relevance_score * 100).toFixed(0) }}%
                </span>
              </div>
              <p class="text-gray-700 font-serif leading-relaxed text-sm">
                {{ cite.content.length > 300 ? cite.content.slice(0, 300) + '...' : cite.content }}
              </p>
            </div>
          </div>
        </div>
        
        <!-- 相关问题 -->
        <div v-if="message.relatedQuestions?.length" class="mt-6">
          <h4 class="font-medium mb-3 flex items-center gap-2" style="color: #6b5a3d;">
            <span>💡</span>
            <span>相关问题</span>
          </h4>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(q, idx) in message.relatedQuestions"
              :key="idx"
              @click="emit('ask', q)"
              class="related-btn px-3 py-1.5 rounded-full text-sm transition-all duration-200"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
