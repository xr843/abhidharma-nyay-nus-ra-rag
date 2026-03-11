<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    xmlns="http://www.w3.org/2000/svg"
    :style="{ color: color }"
  >
    <!-- 外圈 -->
    <circle
      cx="50"
      cy="50"
      r="45"
      fill="none"
      :stroke="color"
      stroke-width="2"
    />

    <!-- 中圈 -->
    <circle
      cx="50"
      cy="50"
      r="35"
      fill="none"
      :stroke="color"
      stroke-width="1.5"
    />

    <!-- 八根辐条 -->
    <g v-for="i in 8" :key="i">
      <line
        :x1="50 + Math.cos((i - 1) * Math.PI / 4) * 15"
        :y1="50 + Math.sin((i - 1) * Math.PI / 4) * 15"
        :x2="50 + Math.cos((i - 1) * Math.PI / 4) * 45"
        :y2="50 + Math.sin((i - 1) * Math.PI / 4) * 45"
        :stroke="color"
        stroke-width="2"
        stroke-linecap="round"
      />
    </g>

    <!-- 中心圆 -->
    <circle
      cx="50"
      cy="50"
      r="8"
      :fill="color"
    />

    <!-- 中心小圆 -->
    <circle
      cx="50"
      cy="50"
      r="4"
      fill="white"
    />
  </svg>
</template>

<script setup>
defineProps({
  size: {
    type: [Number, String],
    default: 64
  },
  color: {
    type: String,
    default: '#8b6914'
  }
})
</script>
