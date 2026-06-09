import { createRouter, createWebHistory } from "vue-router"

import AboutView from "@/views/AboutView.vue"
import BlogView from "@/views/BlogView.vue"
// import DevModeView from "@/views/DevModeView.vue"
import EntityListView from "@/views/EntityListView.vue"
import EntityView from "@/views/EntityView.vue"
import FaqView from "@/views/FaqView.vue"
import HomeView from "@/views/HomeView.vue"
import LegalNotices from "@/views/LegalNotices.vue"
import NewsView from "@/views/NewsView.vue"
import NotFoundView from "@/views/NotFoundView.vue"
import PrivacyPolicyView from "@/views/PrivacyPolicyView.vue"
import TransferView from "@/views/TransferView.vue"
import WhoView from "@/views/WhoView.vue"


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/explore",
      name: "explore",
      component: EntityListView,
    },
    {
      path: "/entities",
      redirect: "/explore",
    },
    {
      path: "/entities/:id",
      name: "entity",
      component: EntityView,
    },
    {
      path: "/transfers/:id",
      name: "transfer",
      component: TransferView,
    },
    {
      path: "/pages/faq",
      name: "faq",
      component: FaqView,
    },
    {
      path: "/pages/about",
      name: "about",
      component: AboutView,
    },
    {
      path: "/pages/legal-notice",
      name: "legal-notice",
      component: LegalNotices,
    },
    {
      path: "/pages/newsletter",
      name: "newsletter-list",
      component: NewsView,
    },
    {
      path: "/pages/newsletter/:id",
      name: "newsletter",
      component: NewsView,
    },
    {
      path: "/pages/blog",
      name: "blog-list",
      component: BlogView,
    },
    {
      path: "/pages/blog/:id",
      name: "blog",
      component: BlogView,
    },
    {
      path: "/pages/privacy-policy",
      name: "privacy-policy",
      component: PrivacyPolicyView,
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: NotFoundView,
    },
    {
      path: "/pages/who-we-are",
      name: "who-we-are",
      component: WhoView,
    },
    // {
    //   path: "/preview-mode",
    //   name: "preview-mode",
    //   component: DevModeView,
    // }
  ],
  scrollBehavior(to, from, savedPosition) {
    if (to.hash === "#contact") {
      return false
    }
    const defaultScroll = { el: "#main", top: 500 }
    if (to.hash) {
      const scrollData: { [id: string]: any } = { el: to.hash, top: undefined }
      const el = document.querySelector(to.hash)
      if (!el) {
        return defaultScroll
      }
      const styles = window.getComputedStyle(el)
      // Retrieve the scroll-margin-top property
      const scrollMarginTop = styles.getPropertyValue("scroll-margin-top")
      if (scrollMarginTop) {
        scrollData.top = parseInt(scrollMarginTop)
      }
      return scrollData
    } else if (savedPosition) {
      return savedPosition
    }
    // The top value must be higher than the maximum header-height
    // which is contained in --big-header-height
    return defaultScroll
  },
})

export default router
