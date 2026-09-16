<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const title = ref('常州美食排行榜')
const query = ref('')
const activeTag = ref('')
const items = ref([])
const tagStats = ref([])
const loading = ref(true)
const error = ref('')

const rankedItems = computed(() =>
  items.value.map((item, index) => ({
    ...item,
    medal: { 1: '🥇', 2: '🥈', 3: '🥉' }[index + 1] || String(index + 1),
  })),
)

async function fetchTags() {
  try {
    const res = await fetch('/api/tags')
    if (!res.ok) return
    const data = await res.json()
    tagStats.value = data.tags || []
  } catch {
    tagStats.value = []
  }
}

async function fetchList() {
  loading.value = true
  error.value = ''
  const params = new URLSearchParams()
  const q = query.value.trim()
  if (q) params.set('q', q)
  if (activeTag.value) params.set('tag', activeTag.value)
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

function selectTag(tag) {
  activeTag.value = activeTag.value === tag ? '' : tag
}

watch(activeTag, () => {
  fetchList()
})

onMounted(async () => {
  await fetchTags()
  await fetchList()
})
</script>

<template>
  <div class="wrap">
    <h1>{{ title }}</h1>
    <p class="sub">按评分排序 · 店名自动打标 · 同分优先打卡次数多的店</p>
    <form class="search" @submit.prevent="onSearch">
      <input
        v-model="query"
        type="search"
        placeholder="搜索饭店名称…"
        autocomplete="off"
      >
      <button type="submit">搜索</button>
    </form>
    <div v-if="tagStats.length" class="tag-bar">
      <button
        type="button"
        class="tag-chip"
        :class="{ active: !activeTag }"
        @click="activeTag = ''"
      >
        全部
      </button>
      <button
        v-for="row in tagStats"
        :key="row.tag"
        type="button"
        class="tag-chip"
        :class="{ active: activeTag === row.tag }"
        @click="selectTag(row.tag)"
      >
        {{ row.tag }}
        <span class="tag-count">{{ row.count }}</span>
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th class="rank">排名</th>
            <th>饭店</th>
            <th class="tags-col">标签</th>
            <th class="score">评分</th>
            <th class="count">次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="empty">加载中…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="5" class="empty">没有匹配的饭店</td>
          </tr>
          <tr v-for="row in rankedItems" :key="row.name">
            <td class="rank">{{ row.medal }}</td>
            <td class="name">{{ row.name }}</td>
            <td class="tags-col">
              <div v-if="row.tags?.length" class="row-tags">
                <span v-for="t in row.tags" :key="t" class="mini-tag">{{ t }}</span>
              </div>
              <span v-else class="muted-dash">—</span>
            </td>
            <td class="score">{{ row.score.toFixed(1) }}</td>
            <td class="count">{{ row.count == null ? '—' : row.count + ' 次' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="meta">
      共 {{ items.length }} 家
      <template v-if="activeTag"> · 标签：{{ activeTag }}</template>
    </p>
  </div>
</template>
