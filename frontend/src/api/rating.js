/**
 * 评分相关接口
 */
import request from './request'

// 添加/更新评分
export function addRating(data) {
  return request.post('/rating/add', data)
}

// 获取当前用户对某电影的评分状态
export function getRatingStatus(movieId) {
  return request.get('/rating/status', { params: { movieId } })
}

// 我的评分记录
export function getMyRatings(params) {
  return request.get('/rating/my', { params })
}

// 删除我的评分
export function deleteRating(movieId) {
  return request.delete('/rating/delete', { params: { movieId } })
}
