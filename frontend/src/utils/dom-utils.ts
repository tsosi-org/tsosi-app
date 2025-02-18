import { appContext } from "@/main"
import { createApp, type Component } from "vue"

export function changeTitle(title: string) {
  document.title = "TSOSI - " + title
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
