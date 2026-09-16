<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import LoginView from './LoginView.vue'
import { apiFetch, clearAuth, getToken, getUser } from './auth'

const title = ref('常州美食排行榜')
const query = ref('')
const activeTag = ref('')
const items = ref([])
const tagStats = ref([])
const loading = ref(true)
const error = ref('')

const tonightItems = ref([])
const tonightLoading = ref(false)
const tonightError = ref('')
const tonightHint = ref('')

const showLogin = ref(!getToken())
const user = ref(getUser())
const isLoggedIn = computed(() => !!user.value && !!getToken())
const isAdmin = computed(() => isLoggedIn.value && user.value?.role === 'admin')

const editorOpen = ref(false)
const editorMode = ref('create')
const saving = ref(false)
const formError = ref('')
const form = ref({
  original_name: '',
  name: '',
  score: '',
  tags: '',
})

/** @type {import('vue').Ref<Record<string, boolean>>} */
const rateSaving = ref({})
/** @type {import('vue').Ref<string>} */
const rateError = ref('')
const rateOpen = ref(false)
const rateTarget = ref(null)
const ratePick = ref(null)

const scoreChoices = Array.from({ length: 21 }, (_, i) => Math.round(i * 0.5 * 10) / 10)

const rankedItems = computed(() =>
  items.value.map((item, index) => ({
    ...item,
    medal: { 1: '🥇', 2: '🥈', 3: '🥉' }[index + 1] || String(index + 1),
  })),
)

const editorTitle = computed(() => (editorMode.value === 'edit' ? '编辑饭店' : '新增饭店'))
const tableCols = computed(() => (isAdmin.value ? 6 : 5))
const rateModalTitle = computed(() =>
  rateTarget.value?.my_score == null ? '给这家店打分' : '修改我的评分',
)

function scoreText(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toFixed(1)
}

function openRate(row) {
  rateTarget.value = row
  ratePick.value = row.my_score == null ? 8 : row.my_score
  rateError.value = ''
  rateOpen.value = true
}

function closeRate() {
  if (rateSaving.value[rateTarget.value?.name]) return
  rateOpen.value = false
  rateTarget.value = null
}

async function restoreSession() {
  const token = getToken()
  if (!token) {
    user.value = null
    showLogin.value = true
    return
  }
  try {
    const res = await apiFetch('/api/me')
    const data = await res.json()
    if (data.authenticated && data.user) {
      user.value = data.user
      showLogin.value = false
    } else {
      clearAuth()
      user.value = null
      showLogin.value = true
    }
  } catch {
    clearAuth()
    user.value = null
    showLogin.value = true
  }
}

async function fetchTags() {
  try {
    const res = await apiFetch('/api/tags')
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
    const res = await apiFetch(url)
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

async function refreshAll() {
  await fetchTags()
  await fetchList()
}

async function pickTonight() {
  tonightLoading.value = true
  tonightError.value = ''
  const params = new URLSearchParams({ n: '3', min_score: '7.0' })
  if (activeTag.value) params.set('tag', activeTag.value)
  try {
    const res = await apiFetch(`/api/tonight?${params}`)
    if (!res.ok) throw new Error(`请求失败：${res.status}`)
    const data = await res.json()
    tonightItems.value = data.items || []
    tonightHint.value = data.hint || ''
    if (!tonightItems.value.length) {
      tonightError.value = '当前筛选下没有可推荐的店'
    }
  } catch (err) {
    tonightError.value = err.message || '抽选失败'
    tonightItems.value = []
  } finally {
    tonightLoading.value = false
  }
}

function onSearch() {
  fetchList()
}

function selectTag(tag) {
  activeTag.value = activeTag.value === tag ? '' : tag
}

function openCreate() {
  if (!isAdmin.value) return
  editorMode.value = 'create'
  formError.value = ''
  form.value = {
    original_name: '',
    name: '',
    score: '7.5',
    tags: '',
  }
  editorOpen.value = true
}

function openEdit(row) {
  if (!isAdmin.value) return
  editorMode.value = 'edit'
  formError.value = ''
  form.value = {
    original_name: row.name,
    name: row.name,
    score: '',
    tags: (row.tags || []).join('，'),
  }
  editorOpen.value = true
}

function closeEditor() {
  if (saving.value) return
  editorOpen.value = false
}

async function saveRecord() {
  if (!isAdmin.value) {
    formError.value = '需要管理员登录'
    return
  }
  formError.value = ''
  const name = form.value.name.trim()
  if (!name) {
    formError.value = '请填写店名'
    return
  }

  const payload = {
    name,
    tags: form.value.tags,
  }

  if (editorMode.value === 'create') {
    const scoreRaw = form.value.score.trim()
    if (scoreRaw !== '') {
      const score = Number(scoreRaw)
      if (Number.isNaN(score) || score < 0 || score > 10) {
        formError.value = '初始评分须为 0–10，可留空'
        return
      }
      payload.score = score
    }
  } else {
    payload.original_name = form.value.original_name
  }

  saving.value = true
  try {
    const res = await apiFetch('/api/restaurants', {
      method: editorMode.value === 'edit' ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => ({}))
    if (res.status === 401) {
      clearAuth()
      user.value = null
      throw new Error('登录已失效，请重新登录')
    }
    if (!res.ok) throw new Error(data.error || `保存失败：${res.status}`)
    editorOpen.value = false
    await refreshAll()
  } catch (err) {
    formError.value = err.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function deleteRecord(row) {
  if (!isAdmin.value) return
  if (!window.confirm(`确认删除「${row.name}」？`)) return
  try {
    const res = await apiFetch(`/api/restaurants/${encodeURIComponent(row.name)}`, {
      method: 'DELETE',
    })
    const data = await res.json().catch(() => ({}))
    if (res.status === 401) {
      clearAuth()
      user.value = null
      showLogin.value = true
      throw new Error('登录已失效，请重新登录')
    }
    if (!res.ok) throw new Error(data.error || `删除失败：${res.status}`)
    await refreshAll()
  } catch (err) {
    error.value = err.message || '删除失败'
  }
}

async function submitRating() {
  const row = rateTarget.value
  if (!row) return
  const score = Number(ratePick.value)
  if (Number.isNaN(score) || score < 0 || score > 10) {
    rateError.value = '请选择 0–10 的分数'
    return
  }

  rateSaving.value = { ...rateSaving.value, [row.name]: true }
  rateError.value = ''
  try {
    const res = await apiFetch(`/api/restaurants/${encodeURIComponent(row.name)}/rating`, {
      method: 'PUT',
      body: JSON.stringify({ score }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.status === 401) {
      clearAuth()
      user.value = null
      showLogin.value = true
      throw new Error('登录已失效，请重新登录')
    }
    if (!res.ok) throw new Error(data.error || `打分失败：${res.status}`)

    items.value = items.value.map((item) => {
      if (item.name !== row.name) return item
      return {
        ...item,
        score: data.score,
        score_count: data.score_count,
        my_score: data.my_score,
      }
    })
    tonightItems.value = tonightItems.value.map((item) => {
      if (item.name !== row.name) return item
      return {
        ...item,
        score: data.score,
        score_count: data.score_count,
        my_score: data.my_score,
      }
    })
    items.value = [...items.value].sort((a, b) => {
      const sa = a.score == null ? -1 : a.score
      const sb = b.score == null ? -1 : b.score
      if (sb !== sa) return sb - sa
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh')
    })
    rateOpen.value = false
    rateTarget.value = null
  } catch (err) {
    rateError.value = err.message || '打分失败'
  } finally {
    rateSaving.value = { ...rateSaving.value, [row.name]: false }
  }
}

async function onLoginSuccess(nextUser) {
  user.value = nextUser
  showLogin.value = false
  await refreshAll()
}

function logout() {
  clearAuth()
  user.value = null
  editorOpen.value = false
  items.value = []
  tagStats.value = []
  tonightItems.value = []
  rateOpen.value = false
  rateTarget.value = null
  rateError.value = ''
  showLogin.value = true
}

watch(activeTag, () => {
  if (isLoggedIn.value) fetchList()
})

onMounted(async () => {
  await restoreSession()
  if (isLoggedIn.value) {
    await refreshAll()
  }
})
</script>

<template>
  <LoginView v-if="showLogin || !isLoggedIn" @success="onLoginSuccess" />

  <div v-else class="wrap">
    <header class="topbar">
      <div>
        <h1>{{ title }}</h1>
        <p class="sub">公共分为所有人评分的平均；每人每店可打一次分，可随时修改</p>
      </div>
      <div class="auth-box">
        <span class="auth-user">
          {{ isAdmin ? '管理员' : '用户' }} · {{ user.username }}
        </span>
        <button type="button" class="ghost-btn" @click="logout">退出</button>
      </div>
    </header>

    <section class="tonight">
      <div class="tonight-head">
        <div>
          <h2>今晚吃什么</h2>
          <p>从高分店里随机抽 3 家，分数越高越容易中</p>
        </div>
        <button type="button" class="tonight-btn" :disabled="tonightLoading" @click="pickTonight">
          {{ tonightLoading ? '抽取中…' : tonightItems.length ? '再抽一次' : '帮我选' }}
        </button>
      </div>
      <p v-if="activeTag" class="tonight-filter">当前标签：{{ activeTag }}（会按此筛选）</p>
      <p v-if="tonightError" class="error">{{ tonightError }}</p>
      <div v-if="tonightItems.length" class="tonight-cards">
        <article v-for="(row, idx) in tonightItems" :key="row.name" class="tonight-card">
          <div class="tonight-rank">推荐 {{ idx + 1 }}</div>
          <div class="tonight-name">{{ row.name }}</div>
          <div class="tonight-meta">
            <span class="score">{{ scoreText(row.score) }} 分</span>
            <span v-if="row.score_count">{{ row.score_count }} 人评</span>
          </div>
          <div v-if="row.tags?.length" class="row-tags">
            <span v-for="t in row.tags" :key="t" class="mini-tag">{{ t }}</span>
          </div>
        </article>
      </div>
      <p v-if="tonightHint && tonightItems.length" class="tonight-hint">{{ tonightHint }}</p>
    </section>

    <form class="search" @submit.prevent="onSearch">
      <input
        v-model="query"
        type="search"
        placeholder="搜索饭店名称…"
        autocomplete="off"
      >
      <button type="submit">搜索</button>
      <button v-if="isAdmin" type="button" class="ghost-btn" @click="openCreate">新增</button>
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
            <th class="score">公共分</th>
            <th class="my-score-col">我的分</th>
            <th v-if="isAdmin" class="action-col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="tableCols" class="empty">加载中…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td :colspan="tableCols" class="empty">没有匹配的饭店</td>
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
            <td class="score">
              <div>{{ scoreText(row.score) }}</div>
              <div class="score-sub">{{ row.score_count ? `${row.score_count} 人` : '暂无' }}</div>
            </td>
            <td class="my-score-col">
              <div class="my-score-cell">
                <span class="my-score-val">{{ scoreText(row.my_score) }}</span>
                <button type="button" class="link-btn" @click="openRate(row)">
                  {{ row.my_score == null ? '打分' : '修改' }}
                </button>
              </div>
            </td>
            <td v-if="isAdmin" class="action-col">
              <button type="button" class="link-btn" @click="openEdit(row)">编辑</button>
              <button type="button" class="link-btn danger" @click="deleteRecord(row)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="meta">
      共 {{ items.length }} 家
      <template v-if="activeTag"> · 标签：{{ activeTag }}</template>
    </p>

    <div v-if="rateOpen && rateTarget" class="modal-mask" @click.self="closeRate">
      <div class="modal rate-modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <h3>{{ rateModalTitle }}</h3>
          <button type="button" class="link-btn" @click="closeRate">关闭</button>
        </div>
        <p class="rate-target-name">{{ rateTarget.name }}</p>
        <div class="score-grid">
          <button
            v-for="n in scoreChoices"
            :key="n"
            type="button"
            class="score-chip"
            :class="{ active: ratePick === n }"
            @click="ratePick = n"
          >
            {{ n.toFixed(1) }}
          </button>
        </div>
        <p v-if="rateError" class="error">{{ rateError }}</p>
        <div class="modal-actions">
          <button type="button" class="ghost-btn" :disabled="!!rateSaving[rateTarget.name]" @click="closeRate">
            取消
          </button>
          <button type="button" :disabled="!!rateSaving[rateTarget.name]" @click="submitRating">
            {{ rateSaving[rateTarget.name] ? '提交中…' : '确认' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="editorOpen" class="modal-mask" @click.self="closeEditor">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <h3>{{ editorTitle }}</h3>
          <button type="button" class="link-btn" @click="closeEditor">关闭</button>
        </div>
        <form class="modal-form" @submit.prevent="saveRecord">
          <label>
            <span>店名</span>
            <input v-model="form.name" type="text" required maxlength="40" placeholder="例如：某某小馆">
          </label>
          <label v-if="editorMode === 'create'">
            <span>初始评分（可选，写入公共均分种子）</span>
            <input v-model="form.score" type="number" min="0" max="10" step="0.1" placeholder="可留空">
          </label>
          <label>
            <span>标签（逗号分隔，可空则自动打标）</span>
            <input v-model="form.tags" type="text" placeholder="例如：火锅，商圈">
          </label>
          <p v-if="formError" class="error">{{ formError }}</p>
          <div class="modal-actions">
            <button type="button" class="ghost-btn" :disabled="saving" @click="closeEditor">取消</button>
            <button type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
