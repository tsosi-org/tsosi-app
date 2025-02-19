import { createRouter, createWebHistory } from "vue-router"
import HomeView from "@/views/HomeView.vue"
import EntityView from "@/views/EntityView.vue"
import NotFoundView from "@/views/NotFoundView.vue"
import TransfertView from "@/views/TransfertView.vue"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/entities/:id",
      name: "entity",
      component: EntityView,
    },
    {
      path: "/transferts/:id",
      name: "transfert",
      component: TransfertView,
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: NotFoundView,
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  },
})

export default router
