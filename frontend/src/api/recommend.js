/**
 * 推荐相关接口
 */
import request from './request'

// 协同过滤推荐
export function getCollaborativeRecommend(topN = 20) {
  return request.get('/recommend/collaborative', { params: { topN } })
}

// SVD矩阵分解推荐
export function getSvdRecommend(topN = 20) {
  return request.get('/recommend/svd', { params: { topN } })
}

// 知识图谱路径推荐
export function getKnowledgeRecommend(topN = 20) {
  return request.get('/recommend/knowledge', { params: { topN } })
}

// 混合推荐
export function getHybridRecommend(topN = 20) {
  return request.get('/recommend/hybrid', { params: { topN } })
}
