/**
 * The state of a page kept in its URL's query, e.g. the sort, filters and
 * page of a table, so that it can be shared and is found again when coming
 * back in the history. See the "Table state in the URL" section of the
 * README.
 */
import type {
  LocationQuery,
  RouteLocationNormalizedLoaded,
  Router,
} from "vue-router"

// The params to set; null removes one
export type QueryValues = Record<string, string | null>

// The string value of a param, if it has one
export function queryString(
  query: LocationQuery,
  key: string,
): string | undefined {
  const value = query[key]
  return typeof value == "string" ? value : undefined
}

/**
 * Set these params of the current URL, keeping the others, and drop those
 * of `drop` not set. Replaced, not pushed: Back leaves the page instead of
 * undoing a sort, and coming back restores it. Nothing if they're the same.
 */
export function replaceQuery(
  router: Router,
  route: RouteLocationNormalizedLoaded,
  values: QueryValues,
  drop: (key: string) => boolean = () => false,
) {
  const query: LocationQuery = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (!(key in values) && !drop(key)) {
      query[key] = value
    }
  }
  for (const [key, value] of Object.entries(values)) {
    if (value != null) {
      query[key] = value
    }
  }
  if (sameQuery(query, route.query)) {
    return
  }
  router.replace({ query, hash: route.hash })
}

function sameQuery(left: LocationQuery, right: LocationQuery): boolean {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)])
  return [...keys].every(
    (key) => JSON.stringify(left[key]) == JSON.stringify(right[key]),
  )
}
