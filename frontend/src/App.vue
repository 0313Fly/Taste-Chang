<script setup>
import { computed, onMounted, ref } from 'vue'

const title = ref('常州美食排行榜')
const query = ref('')
const items = ref([])
const loading = ref(true)
const error = ref('')

const rankedItems = computed(() =>
  items.value.map((item, index) => ({
    ...item,
    medal: { 1: '🥇', 2: '🥈', 3: '🥉' }[index + 1] || String(index + 1),
  })),
)

async function fetchList() {
  loading.value = true
  error.value = ''
  const params = new URLSearchParams()
  const q = query.value.trim()
  if (q) params.set('q', q)
  const url = params.size ? `/api/restaurants?${params}` : '/api/restaurants'
  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`请求失败：${res.status}`)
    const data = await res.json()
    title.value = data.title || title.value
    items.value = data.items || []
  } catch (err) {
    error.value = err.message || '加载失败'
    items.value = []
  } finally {
    loading.value = false
  }
}

function onSearch() {
  fetchList()
}

onMounted(fetchList)
</script>

<template>
  <div class="wrap">
    <h1>{{ title }}</h1>
    <p class="sub">按评分排序 · 同分优先展示打卡次数更多的店</p>
    <form class="search" @submit.prevent="onSearch">
      <input
        v-model="query"
        type="search"
        placeholder="搜索饭店名称…"
        autocomplete="off"
      >
      <button type="submit">搜索</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th class="rank">排名</th>
            <th>饭店</th>
            <th class="score">评分</th>
            <th class="count">次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="4" class="empty">加载中…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="4" class="empty">没有匹配的饭店</td>
          </tr>
          <tr v-for="row in rankedItems" :key="row.name">
            <td class="rank">{{ row.medal }}</td>
            <td class="name">{{ row.name }}</td>
            <td class="score">{{ row.score.toFixed(1) }}</td>
            <td class="count">{{ row.count == null ? '—' : row.count + ' 次' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="meta">
      共 {{ items.length }} 家 · API:
      <a href="/api/restaurants">/api/restaurants</a>
    </p>
  </div>
</template>
