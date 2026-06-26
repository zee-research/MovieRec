/**
 * 用户状态管理（Pinia）
 * 存储登录用户信息、token，持久化到 localStorage
 */
import { defineStore } from 'pinia'
import { getUserInfo } from '@/api/user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
  }),

  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,
    // 是否为管理员
    isAdmin: (state) => state.userInfo?.role === 'admin',
    // 用户名
    username: (state) => state.userInfo?.username || '',
  },

  actions: {
    // 设置登录信息
    setLogin(data) {
      this.token = data.token
      this.userInfo = { userId: data.userId, username: data.username, role: data.role }
      localStorage.setItem('token', data.token)
      localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
    },

    // 退出登录
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },

    // 刷新用户信息
    async refreshInfo() {
      try {
        const res = await getUserInfo()
        if (res.code === 200) {
          this.userInfo = res.data
          localStorage.setItem('userInfo', JSON.stringify(res.data))
        }
      } catch (e) {
        // 忽略
      }
    },
  },
})
