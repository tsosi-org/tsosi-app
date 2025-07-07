/**
 * Handles the big header style for the home page.
 * It performs style related operations and expose the `bigHeader`
 * boolean ref.
 */
import { ref, watch } from "vue"

export async function togglePageNoHeader(value: boolean) {
  const app = document.getElementById("app")
  if (value) {
    app!.classList.add("init-big-header")
  } else {
    app!.classList.remove("init-big-header")
  }
}

/**
 * Whether the header is in big header mode.
 */
export const bigHeader = ref(false)

export function setBigHeader(value: boolean) {
  if (bigHeader.value == value) {
    return
  }
  bigHeader.value = value
}

watch(bigHeader, () => {
  if (bigHeader.value) {
    document.documentElement.style.setProperty(
      "--header-height",
      "var(--big-header-height)",
    )
  } else {
    document.documentElement.style.setProperty(
      "--header-height",
      "var(--regular-header-height)",
    )
  }
})
