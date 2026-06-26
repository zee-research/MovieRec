/**
 * 知识图谱相关接口
 */
import request from './request'

// 电影关联的知识图谱
export function getMovieGraph(movieId, limit = 30) {
  return request.get(`/graph/movie/${movieId}`, { params: { limit } })
}

// 全局知识图谱概览
export function getGlobalGraph(limitMovies = 50, limitUsers = 30) {
  return request.get('/graph/global', { params: { limitMovies, limitUsers } })
}
