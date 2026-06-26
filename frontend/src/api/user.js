/**
 * 用户相关接口
 */
import request from './request'

// 用户注册
export function register(data) {
  return request.post('/user/register', data)
}

// 用户登录
export function login(data) {
  return request.post('/user/login', data)
}

// 获取当前用户信息
export function getUserInfo() {
  return request.get('/user/info')
}

// 修改密码
export function changePassword(data) {
  return request.put('/user/password', data)
}
