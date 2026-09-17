import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/components/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppShell.vue'),
      children: [
        { path: '', redirect: '/chat' },
        { path: 'chat', name: 'chat', component: () => import('@/components/chat/_ChatViewPlaceholder.vue') },
        { path: 'admin', name: 'admin', component: () => import('@/components/admin/_AdminViewPlaceholder.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.accessToken) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

export default router