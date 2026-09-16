<script setup>
import { ref } from 'vue'
import { apiFetch, setAuth } from './auth'

const emit = defineEmits(['success'])

const mode = ref('login') // login | register
const username = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  error.value = ''
  const name = username.value.trim()
  if (!name || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  if (mode.value === 'register') {
    if (password.value.length < 6) {
      error.value = '密码至少 6 位'
      return
    }
    if (password.value !== password2.value) {
      error.value = '两次密码不一致'
      return
    }
  }

  loading.value = true
  try {
    const url = mode.value === 'register' ? '/api/register' : '/api/login'
    const res = await apiFetch(url, {
      method: 'POST',
      body: JSON.stringify({
        username: name,
        password: password.value,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.error || (mode.value === 'register' ? '注册失败' : '登录失败'))
    setAuth(data.token, data.user)
    emit('success', data.user)
  } catch (err) {
    error.value = err.message || '操作失败'
  } finally {
    loading.value = false
  }
}

function switchMode(next) {
  mode.value = next
  error.value = ''
  password.value = ''
  password2.value = ''
}
</script>

<template>
  <div class="login-page">
    <form class="login-card" @submit.prevent="onSubmit">
      <h1>常州美食排行榜</h1>
      <p class="login-sub">请先注册或登录后再查看榜单</p>

      <div class="mode-tabs">
        <button
          type="button"
          class="mode-tab"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="mode-tab"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <label>
        <span>用户名</span>
        <input v-model="username" type="text" autocomplete="username" required maxlength="20" placeholder="2–20 位">
      </label>
      <label>
        <span>密码</span>
        <input v-model="password" type="password" autocomplete="current-password" required placeholder="至少 6 位">
      </label>
      <label v-if="mode === 'register'">
        <span>确认密码</span>
        <input v-model="password2" type="password" autocomplete="new-password" required>
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="login-actions">
        <button type="submit" :disabled="loading">
          {{ loading ? '处理中…' : (mode === 'register' ? '注册并进入' : '登录') }}
        </button>
      </div>
    </form>
  </div>
</template>
