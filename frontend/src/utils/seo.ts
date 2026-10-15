import type { NavigationFailure, RouteLocationNormalized } from "vue-router"


declare module "vue-router" {
  interface RouteMeta {
    // Page title, prefixed with "TSOSI - ". Views can override it.
    title?: string
    // Meta description. Views can override it.
    description?: string
  }
}

const DEFAULT_TITLE = "Transparency to Sustain Open Science Infrastructure"
// Keep in sync with the description of `index.html`
const DEFAULT_DESCRIPTION =
  "A data-driven platform to broaden funding for open science " +
  "infrastructure: TSOSI shows which organizations support which " +
  "infrastructures, with open data."

function setMetaContent(selector: string, content: string) {
  const meta: HTMLMetaElement | null = document.querySelector(selector)
  if (meta) {
    meta.content = content
  }
}

export function changeMetaTitle(title: string) {
  const newTitle = "TSOSI - " + title
  document.title = newTitle
  setMetaContent("meta[property='og:title']", newTitle)
}

export function changeMetaDescription(desc: string) {
  setMetaContent("meta[name='description']", desc)
  setMetaContent("meta[property='og:description']", desc)
}

/**
 * Set the canonical URL of the page, and the matching `og:url`.
 * The canonical link is only created client-side: a canonical in the
 * static `index.html` would point every URL to the same page for crawlers
 * that don't run JS.
 */
export function changeCanonicalUrl(path: string) {
  const url = window.location.origin + path
  let link: HTMLLinkElement | null = document.querySelector(
    "link[rel='canonical']",
  )
  if (!link) {
    link = document.createElement("link")
    link.rel = "canonical"
    document.head.appendChild(link)
  }
  link.href = url
  setMetaContent("meta[property='og:url']", url)
}

/**
 * Ask search engines not to index the current page, e.g. a "Not found" page
 * served with a 200 status.
 */
export function setNoIndex(noIndex: boolean) {
  let meta: HTMLMetaElement | null = document.querySelector(
    "meta[name='robots']",
  )
  if (!noIndex) {
    meta?.remove()
    return
  }
  if (!meta) {
    meta = document.createElement("meta")
    meta.name = "robots"
    document.head.appendChild(meta)
  }
  meta.content = "noindex"
}

/**
 * Reset the page metadata from the route `meta`, so that nothing is kept
 * from the previous page. Views setting their own metadata run after it.
 */
export function applyRouteMeta(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  failure?: NavigationFailure | void,
) {
  // Views stay mounted on hash or query changes (the RouterView is keyed by
  // path), e.g. when opening the contact modal: keep the metadata they set.
  // On the first load, `from` is the start location, which matches nothing.
  if (failure || (from.matched.length && to.path === from.path)) {
    return
  }
  changeMetaTitle(to.meta.title ?? DEFAULT_TITLE)
  changeMetaDescription(to.meta.description ?? DEFAULT_DESCRIPTION)
  changeCanonicalUrl(to.path)
  setNoIndex(false)
}

/**
 * Redirect URLs with a trailing slash to the URL without it, so that each page
 * has a single URL. Blog posts are the exception: they need the trailing slash
 * for the relative links of their content.
 */
export function removeTrailingSlash(to: RouteLocationNormalized) {
  if (to.path === "/" || !to.path.endsWith("/") || to.name === "blog") {
    return true
  }
  return {
    path: to.path.replace(/\/+$/, ""),
    query: to.query,
    hash: to.hash,
    replace: true,
  }
}
