/**
 * 从电影对象中提取类型列表
 * 兼容后端不同接口返回的 genreNames(数组) 和 genres(|分隔字符串) 两种格式
 */
export function getGenreList(movie) {
  if (!movie) return []
  if (Array.isArray(movie.genreNames) && movie.genreNames.length) return movie.genreNames
  if (Array.isArray(movie.genres)) return movie.genres
  if (typeof movie.genres === 'string' && movie.genres) return movie.genres.split('|')
  return []
}
