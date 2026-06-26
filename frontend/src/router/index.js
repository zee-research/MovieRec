/**
 * 路由配置
 * 管理员端：/admin/* —— 使用 AdminLayout（侧边栏）
 * 用户端：/* —— 使用 UserLayout（顶部导航）
 */
import { createRouter, createWebHistory } from 'vue-router'

/* ========== 布局 ========== */
const AdminLayout = () => import('@/layouts/AdminLayout.vue')
const UserLayout = () => import('@/layouts/UserLayout.vue')

/* ========== 管理员页面 ========== */
const AdminDashboard = () => import('@/views/admin/Dashboard.vue')
const AdminUsers = () => import('@/views/admin/UserManage.vue')
const AdminMovies = () => import('@/views/admin/MovieManage.vue')
const AdminRatings = () => import('@/views/admin/RatingManage.vue')
const AdminGraph = () => import('@/views/admin/GraphManage.vue')
const AdminEvaluate = () => import('@/views/admin/ModelEvaluate.vue')

/* ========== 用户页面 ========== */
const Home = () => import('@/views/user/Home.vue')
const MovieList = () => import('@/views/user/MovieList.vue')
const MovieDetail = () => import('@/views/user/MovieDetail.vue')
const Recommend = () => import('@/views/user/Recommend.vue')
const MyRatings = () => import('@/views/user/MyRatings.vue')
const KnowledgeGraph = () => import('@/views/user/KnowledgeGraph.vue')
const Profile = () => import('@/views/user/Profile.vue')

/* ========== 公共页面 ========== */
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')

const routes = [
  // 登录 & 注册
  { path: '/login', name: 'Login', component: Login, meta: { title: '登录' } },
  { path: '/register', name: 'Register', component: Register, meta: { title: '注册' } },

  // 管理员端
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, requiresAdmin: true },
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', name: 'AdminDashboard', component: AdminDashboard, meta: { title: '数据概览' } },
      { path: 'users', name: 'AdminUsers', component: AdminUsers, meta: { title: '用户管理' } },
      { path: 'movies', name: 'AdminMovies', component: AdminMovies, meta: { title: '电影管理' } },
      { path: 'ratings', name: 'AdminRatings', component: AdminRatings, meta: { title: '评分管理' } },
      { path: 'graph', name: 'AdminGraph', component: AdminGraph, meta: { title: '知识图谱' } },
      { path: 'evaluate', name: 'AdminEvaluate', component: AdminEvaluate, meta: { title: '模型评估' } },
    ],
  },

  // 用户端
  {
    path: '/',
    component: UserLayout,
    redirect: '/home',
    children: [
      { path: 'home', name: 'Home', component: Home, meta: { title: '首页' } },
      { path: 'movies', name: 'MovieList', component: MovieList, meta: { title: '电影列表' } },
      { path: 'movie/:id', name: 'MovieDetail', component: MovieDetail, meta: { title: '电影详情' } },
      { path: 'recommend', name: 'Recommend', component: Recommend, meta: { title: '个性化推荐', requiresAuth: true } },
      { path: 'my-ratings', name: 'MyRatings', component: MyRatings, meta: { title: '我的评分', requiresAuth: true } },
      { path: 'knowledge-graph', name: 'KnowledgeGraph', component: KnowledgeGraph, meta: { title: '知识图谱' } },
      { path: 'profile', name: 'Profile', component: Profile, meta: { title: '个人中心', requiresAuth: true } },
    ],
  },

  // 404 重定向
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/* ========== 路由守卫 ========== */
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 电影推荐系统` : '电影推荐系统'

  const token = localStorage.getItem('token')
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || 'null')

  // 需要登录
  if (to.meta.requiresAuth && !token) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  // 需要管理员权限
  if (to.meta.requiresAdmin && userInfo?.role !== 'admin') {
    return next({ name: 'Home' })
  }

  // 已登录时不再进入登录/注册页
  if ((to.name === 'Login' || to.name === 'Register') && token) {
    return next(userInfo?.role === 'admin' ? { name: 'AdminDashboard' } : { name: 'Home' })
  }

  next()
})

export default router
