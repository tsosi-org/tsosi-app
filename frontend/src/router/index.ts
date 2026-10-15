import { createRouter, createWebHistory } from "vue-router"

import { extractEditKey } from "@/singletons/edit-access"
import { applyRouteMeta, removeTrailingSlash } from "@/utils/seo"


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
    {
      path: "/explore",
      name: "explore",
      component: () => import("@/views/EntityListView.vue"),
      meta: {
        title: "Explore the funding network",
        description:
          "Browse the open science infrastructures in TSOSI and the institutions, consortia and funders that support them.",
      },
    },
    {
      path: "/entities",
      redirect: "/explore",
    },
    {
      path: "/entities/:id",
      name: "entity",
      component: () => import("@/views/EntityView.vue"),
    },
    {
      path: "/transfers/:id",
      name: "transfer",
      component: () => import("@/views/TransferView.vue"),
      meta: {
        title: "Transfer details",
        description:
          "Details and data source of a financial support to an open science infrastructure.",
      },
    },
    {
      path: "/pages/faq",
      name: "faq",
      component: () => import("@/views/FaqView.vue"),
      meta: {
        description:
          "Answers to common questions about TSOSI: where the data comes from, who runs the project and how to join as a data provider.",
      },
    },
    {
      path: "/pages/about",
      name: "about",
      component: () => import("@/views/AboutView.vue"),
      meta: {
        description:
          "How TSOSI started, its approach, the team behind it and the related initiatives that make support for open infrastructure visible.",
      },
    },
    {
      path: "/pages/legal-notice",
      name: "legal-notice",
      component: () => import("@/views/LegalNotices.vue"),
      meta: {
        description:
          "Legal notice of the TSOSI website: data and content policy, copyright, publication director and hosting.",
      },
    },
    {
      path: "/pages/newsletter",
      name: "newsletter-list",
      component: () => import("@/views/NewsView.vue"),
      meta: {
        description:
          "The TSOSI newsletters: news about the project, its data providers and the open science infrastructures it covers.",
      },
    },
    {
      path: "/pages/newsletter/:id",
      name: "newsletter",
      component: () => import("@/views/NewsView.vue"),
      meta: {
        description:
          "The TSOSI newsletters: news about the project, its data providers and the open science infrastructures it covers.",
      },
    },
    {
      path: "/pages/blog",
      name: "blog-list",
      component: () => import("@/views/BlogView.vue"),
      meta: {
        description:
          "Posts from the TSOSI team about the project, its data and the funding of open science infrastructure.",
      },
    },
    {
      path: "/pages/blog/:id",
      name: "blog_redirect",
      redirect: to => {
        return to.path.replace(/\/$/, "") + "/"
      },
    },
    {
      path: "/pages/blog/:id/",
      name: "blog",
      component: () => import("@/views/BlogView.vue"),
      strict: true,
    },
    {
      path: "/pages/privacy-policy",
      name: "privacy-policy",
      component: () => import("@/views/PrivacyPolicyView.vue"),
      meta: {
        description:
          "How the TSOSI website collects and handles personal data, and your rights over it.",
      },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: () => import("@/views/NotFoundView.vue"),
    },
    {
      path: "/new-provider",
      name: "new-provider",
      component: () => import("@/views/ProvideView.vue"),
      meta: {
        description:
          "Become a TSOSI data provider and make your financial support to open infrastructures visible.",
      },
    },
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

router.beforeEach(extractEditKey)
router.beforeEach(removeTrailingSlash)
router.afterEach(applyRouteMeta)

// After a deploy, the chunks of the previous build no longer exist: load the
// target page in full to get the new ones. The session flag prevents a reload
// loop if the chunk is missing from the new build too.
const chunkErrorRegex =
  /dynamically imported module|Importing a module script failed/
const chunkReloadKey = "chunk-reload"
router.onError((error, to) => {
  if (!(error instanceof TypeError) || !chunkErrorRegex.test(error.message)) {
    return
  }
  try {
    if (sessionStorage.getItem(chunkReloadKey) === to.fullPath) {
      return
    }
    sessionStorage.setItem(chunkReloadKey, to.fullPath)
  } catch {
    // Without storage, reload anyway
  }
  window.location.assign(to.fullPath)
})
router.afterEach(() => {
  try {
    sessionStorage.removeItem(chunkReloadKey)
  } catch {
    // Storage unavailable
  }
})

export default router
