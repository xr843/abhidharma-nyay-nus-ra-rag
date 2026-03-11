<script setup>
import { ref } from 'vue'

const props = defineProps({
  disabled: Boolean
})

const emit = defineEmits(['send'])

const inputText = ref('')

function handleSubmit() {
  if (inputText.value.trim() && !props.disabled) {
    emit('send', inputText.value.trim())
    inputText.value = ''
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="relative">
    <input
      v-model="inputText"
      @keydown="handleKeydown"
      :disabled="disabled"
      type="text"
      placeholder="请输入检索内容或所疑之处..."
      class="input-search pr-14"
    />
    <button
      @click="handleSubmit"
      :disabled="disabled || !inputText.trim()"
      class="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
             flex items-center justify-center
             disabled:opacity-50 disabled:cursor-not-allowed
             transition-all duration-200"
      style="background: linear-gradient(135deg, #6b5a3d 0%, #5a4a32 100%); color: #fdfbf7;"
    >
      <svg
        v-if="!disabled"
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
          clip-rule="evenodd"
        />
      </svg>
      <span v-else class="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </span>
    </button>
  </div>
</template>
