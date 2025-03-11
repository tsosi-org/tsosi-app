import { createRouter, createWebHistory } from "vue-router"
import HomeView from "@/views/HomeView.vue"
import EntityView from "@/views/EntityView.vue"
import NotFoundView from "@/views/NotFoundView.vue"
import TransfertView from "@/views/TransfertView.vue"
import FaqView from "@/views/FaqView.vue"
import AboutView from "@/views/AboutView.vue"

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
      path: "/faq",
      name: "faq",
      component: FaqView,
    },
    {
      path: "/about",
      name: "about",
      component: AboutView,
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: NotFoundView,
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (to.hash) {
      return { el: to.hash }
    } else if (savedPosition) {
      return savedPosition
    }
    return { el: "#main", top: 200 }
  },
})

export default router
