/**
 * Mount a component for the component tests with the app's globals:
 * PrimeVue (its classes, without the theme), its tooltips, the icons (as
 * stubs), and a router in memory with the routes the Hub links to.
 */
import { mount } from "@vue/test-utils"
import PrimeVue from "primevue/config"
import Tooltip from "primevue/tooltip"
import { defineComponent, h, type Component } from "vue"
import { createMemoryHistory, createRouter, type Router } from "vue-router"

const Page = defineComponent({ render: () => h("div") })

function testRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "home", component: Page },
      { path: "/entities/:id", name: "entity", component: Page },
      { path: "/hub/:entityId", name: "hub-home", component: Page },
      { path: "/hub/:entityId/submit", name: "hub-submit", component: Page },
      { path: "/:path(.*)*", name: "other", component: Page },
    ],
  })
}

export async function mountComponent(
  component: Component,
  options: {
    props?: Record<string, unknown>
    route?: string
    stubs?: Record<string, Component | boolean>
  } = {},
) {
  const router = testRouter()
  await router.push(options.route ?? "/")
  const wrapper = mount(component as any, {
    props: options.props,
    attachTo: document.body,
    global: {
      plugins: [[PrimeVue, { theme: "none" }], router],
      directives: { tooltip: Tooltip },
      stubs: { "font-awesome-icon": true, ...options.stubs },
    },
  })
  return { wrapper, router }
}

// The button with this accessible name: its label, or its `aria-label`
export function findButton(
  root: Element,
  name: string | RegExp,
): HTMLButtonElement | undefined {
  return [...root.querySelectorAll("button")].find((button) => {
    const label =
      button.getAttribute("aria-label") ?? button.textContent?.trim() ?? ""
    return typeof name == "string" ? label == name : name.test(label)
  })
}

export function buttonNames(root: Element): string[] {
  return [...root.querySelectorAll("button")].map(
    (button) =>
      button.getAttribute("aria-label") ?? button.textContent?.trim() ?? "",
  )
}
