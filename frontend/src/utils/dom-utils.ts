import { appContext } from "@/main"
import { createApp, type Component } from "vue"

const updateMetaTags = false
export function changeMetaDescripion(desc: string) {
  const metaDesc: HTMLMetaElement | null = document.querySelector(
    "meta[name='description']",
  )
  if (metaDesc && updateMetaTags) {
    metaDesc.content = desc
  }
  const ogDesc: HTMLMetaElement | null = document.querySelector(
    "meta[property='og:description']",
  )
  if (ogDesc && updateMetaTags) {
    ogDesc.content = desc
  }
}

export function changeMetaTitle(title: string) {
  const newTitle = "TSOSI - " + title
  document.title = newTitle
  const ogTitle: HTMLMetaElement | null = document.querySelector(
    "meta[property='og:title']",
  )
  if (ogTitle && updateMetaTags) {
    ogTitle.content = newTitle
  }
}

export function changeMetaUrl(current: boolean, url?: string) {
  const ogUrl: HTMLMetaElement | null = document.querySelector(
    "meta[property='og:url']",
  )
  if (ogUrl && updateMetaTags) {
    ogUrl.content = current ? window.location.href : url || ""
  }
}

export function createComponent(
  component: Component,
  mountElement: HTMLElement,
  props?: Record<string, unknown>,
) {
  const instance = createApp(component, props)
  Object.assign(instance._context, appContext)
  instance.mount(mountElement)
  return instance
}

const clickLikeKeys = [" ", "Spacebar", "Enter"]

/**
 * Return whether the given UIEvent should be consider a "click-like" action.
 * For example: space and enter keydown are considered click-like actions.
 */
function isClickLikeAction(event: Event): boolean {
  if (event.type === "click") {
    return true
  }
  if (event.type === "keydown") {
    // @ts-expect-error It has to be a KeyboardEvent
    return clickLikeKeys.includes(event.key)
  }
  return false
}

/**
 * Adds the necessary event listeners to execute the provided callback
 * when a click-like action is performed on the element.
 */
export function addClickEventListener(
  element: HTMLElement,
  callback: (e: Event) => any,
) {
  if (!element) {
    return
  }
  element.addEventListener("click", callback)
  element.addEventListener("keydown", (event) => {
    if (!isClickLikeAction(event)) {
      return
    }
    callback(event)
  })
}
