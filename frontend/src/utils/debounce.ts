import { type Ref } from "vue"

export type DebounceStatus = "idle" | "waiting" | "running"

/**
 * Debounce the given function, ie. wait for a given interval of time without
 * trigger before actually calling the function.
 * Mainly useful for computations triggered by user input.
 *
 * @param callback The function to debounce.
 * @param interval The consolidation interval in ms.
 * @param status  Optional, a ref tracking the status of the debounce lifecycle.
 *                Useful when we want to display or not stuff depending on it.
 * @returns The debounced version of the function.
 */
export default function debounce<T extends unknown[]>(
  callback: (...args: T) => void,
  interval: number,
  status?: Ref<DebounceStatus>,
) {
  let timeoutTimer: ReturnType<typeof setTimeout> | null = null

  return (...args: T) => {
    if (timeoutTimer !== null) {
      clearTimeout(timeoutTimer)
    }

    if (status) {
      status.value = "waiting"
    }

    timeoutTimer = setTimeout(() => {
      timeoutTimer = null
      if (status) {
        status.value = "running"
      }
      callback(...args)

      if (status) {
        status.value = "idle"
      }
    }, interval)
  }
}
