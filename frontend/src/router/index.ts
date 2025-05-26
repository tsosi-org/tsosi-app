import { createRouter, createWebHistory } from "vue-router"
import HomeView from "@/views/HomeView.vue"
import EntityView from "@/views/EntityView.vue"
import NotFoundView from "@/views/NotFoundView.vue"
import TransferView from "@/views/TransferView.vue"
import FaqView from "@/views/FaqView.vue"
import AboutView from "@/views/AboutView.vue"
import LegalNotices from "@/views/LegalNotices.vue"
import PrivacyPolicyView from "@/views/PrivacyPolicyView.vue"
import { targetElement } from "@/utils/dom-utils"

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
      path: "/pages/privacy-policy",
      name: "privacy-policy",
      component: PrivacyPolicyView,
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: NotFoundView,
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (to.hash) {
      const scrollData: { [id: string]: any } = { el: to.hash, top: undefined }
      const el = document.querySelector(to.hash)
      if (!el) {
        return scrollData
      }
      const styles = window.getComputedStyle(el)
      // Retrieve the scroll-margin-top property
      const scrollMarginTop = styles.getPropertyValue("scroll-margin-top")
      if (scrollMarginTop) {
        scrollData.top = parseInt(scrollMarginTop)
      }
      targetElement(el)
      return scrollData
    } else if (savedPosition) {
      return savedPosition
    }
    // The top value must be higher than the maximum header-height
    // which is contained in --big-header-height
    return { el: "#main", top: 500 }
  },
})

export default router
