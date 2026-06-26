<!--
  电影彩色占位封面：根据电影标题+类型生成独特渐变色
-->
<template>
  <div class="movie-poster" :style="posterStyle">
    <span class="poster-letter">{{ initial }}</span>
    <span v-if="year" class="poster-year">{{ year }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title:  { type: String, default: '' },
  genres: { type: String, default: '' },
  year:   { type: [String, Number], default: '' },
})

/* ---------- 生成稳定哈希 ---------- */
function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

/* ---------- 类型 → 色相映射 ---------- */
const genreHueMap = {
  Action: 0, Adventure: 25, Animation: 50, Children: 60,
  Comedy: 45, Crime: 210, Documentary: 170, Drama: 240,
  Fantasy: 280, 'Film-Noir': 260, Horror: 340, Musical: 320,
  Mystery: 230, Romance: 350, 'Sci-Fi': 190, Thriller: 200,
  War: 15, Western: 30, IMAX: 180,
}

function primaryHue(genresStr) {
  if (!genresStr) return 220
  const first = genresStr.split('|')[0] || genresStr.split(',')[0] || ''
  const key = first.trim()
  return genreHueMap[key] ?? hashStr(key) % 360
}

/* ---------- 首字母 ---------- */
const initial = computed(() => {
  const t = props.title.replace(/^(The|A|An)\s+/i, '').trim()
  return t.charAt(0).toUpperCase() || '?'
})

/* ---------- 渐变样式 ---------- */
const posterStyle = computed(() => {
  const h = primaryHue(props.genres)
  const seed = hashStr(props.title || 'x')
  const h2 = (h + 35 + (seed % 30)) % 360
  const sat = 55 + (seed % 20)        // 55-75
  const light1 = 42 + (seed % 12)     // 42-54
  const light2 = 52 + (seed % 14)     // 52-66
  const angle = 135 + (seed % 60)     // 135-195

  return {
    background: `linear-gradient(${angle}deg, hsl(${h},${sat}%,${light1}%) 0%, hsl(${h2},${sat}%,${light2}%) 100%)`,
  }
})
</script>

<style scoped>
.movie-poster {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  user-select: none;
}
.poster-letter {
  font-size: 52px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.85);
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  line-height: 1;
}
.poster-year {
  position: absolute;
  bottom: 8px;
  right: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}
</style>
