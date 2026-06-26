/**
 * 管理员相关接口
 */
import request from './request'

// ==================== 统计 ====================
// 首页统计数据
export function getStatistics() {
  return request.get('/admin/statistics')
}

// 评分分布
export function getRatingDistribution() {
  return request.get('/admin/rating-distribution')
}

// 各类型电影数量
export function getGenreStats() {
  return request.get('/admin/genre-stats')
}

// ==================== 用户管理 ====================
// 用户列表
export function getUsers(params) {
  return request.get('/admin/users', { params })
}

// 删除用户
export function deleteUser(userId) {
  return request.delete(`/admin/users/${userId}`)
}

// 重置用户密码
export function resetUserPassword(userId) {
  return request.put(`/admin/users/${userId}/reset-password`)
}

// ==================== 评分管理 ====================
// 评分列表
export function getRatings(params) {
  return request.get('/admin/ratings', { params })
}

// 删除评分
export function deleteRating(userId, movieId) {
  return request.delete('/admin/ratings/delete', { params: { userId, movieId } })
}

// ==================== 模型评估 ====================
// 启动后台评估任务
export function startEvaluate() {
  return request.post('/admin/model/evaluate-start')
}

// 轮询评估进度
export function getEvaluateProgress() {
  return request.get('/admin/model/evaluate-progress')
}
