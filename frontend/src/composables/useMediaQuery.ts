import { ref, type Ref, unref, onMounted, onUnmounted, computed } from "vue"

/**
 * Returns the result of the given media query as a ref.
 * It will automatically update when the media query result changes.
 * @param query
 * @returns
 */
export function useMediaQuery(query: string | Ref<string>, global = false) {
  let mediaQuery: MediaQueryList | undefined
  const matches = ref(false)

  mediaQuery = window.matchMedia(unref(query))
  matches.value = mediaQuery.matches
  const cleanup = () => {
    if (!mediaQuery) return
    mediaQuery.removeEventListener("change", handler)
    mediaQuery = undefined
  }
  const handler = (event: MediaQueryListEvent) => {
    matches.value = event.matches
  }

  if (!global) {
    onMounted(() => mediaQuery!.addEventListener("change", handler))
    onUnmounted(() => cleanup())
  } else {
    mediaQuery.addEventListener("change", handler)
  }
  return matches
}

export const isDesktop = useMediaQuery("(min-width: 1000px)", true)

export const isTouchScreen = computed(
  () => !useMediaQuery("(pointer: fine)").value,
)
