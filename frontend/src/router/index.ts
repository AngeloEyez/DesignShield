import { createRouter, createWebHistory } from 'vue-router'
import TaskMonitorView from '@/views/TaskMonitorView.vue'
import SettingsView from '@/views/SettingsView.vue'

const routes = [
  {
    path: '/',
    name: 'TaskMonitor',
    component: TaskMonitorView,
    meta: { title: '線路 DRC 任務檢測 - DesignShield' },
  },
  {
    path: '/rules',
    name: 'RuleManagement',
    component: () => import('@/views/RuleManagementView.vue'),
    meta: { title: 'DRC 規則庫管理 - DesignShield' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
    meta: { title: '系統環境與參數設定 - DesignShield' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
  next()
})

export default router
