/**
 * 电影相关接口
 */
import request from './request'

// 电影列表（分页、搜索、筛选）
export function getMovieList(params) {
  return request.get('/movie/list', { params })
}

// 电影详情
export function getMovieDetail(movieId) {
  return request.get(`/movie/detail/${movieId}`)
}

// 获取所有电影类型
export function getGenres() {
  return request.get('/movie/genres')
}

// 热门电影
export function getHotMovies(limit = 10) {
  return request.get('/movie/hot', { params: { limit } })
}

// 相似电影
export function getSimilarMovies(movieId, limit = 10) {
  return request.get(`/movie/similar/${movieId}`, { params: { limit } })
}
