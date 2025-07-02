import { type Ref } from "vue"

/**
 * Throttle the given function so that max. one function call is performed
 * during the given interval.
 *
 * @param callback The function to throttle.
 * @param interval The throttling interval.
 * @param waiting Optional, a boolean ref tracking whether the throttling
 *                is currently in effect, ie. the function cannot be called
 *                before the interval is elapsed.
 * @returns The throttled version of the function.
 */
export function throttle<T extends unknown[]>(
  callback: (...args: T) => void,
  interval: number,
  waitingRef?: Ref<boolean>,
) {
  let isWaiting = false // Variable to keep track of the timer
  if (waitingRef) {
    waitingRef.value = false
  }

  return (...args: T) => {
    if (isWaiting) {
      return
    }

    callback(...args)
    isWaiting = true

    if (waitingRef) {
      waitingRef.value = true
    }
    setTimeout(() => {
      isWaiting = false
      if (waitingRef) {
        waitingRef.value = false
      }
    }, interval)
  }
}
