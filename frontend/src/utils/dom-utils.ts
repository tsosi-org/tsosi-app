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
