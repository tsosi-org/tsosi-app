interface JsonResult {
  data?: object | Array<any> | JSON
  error: boolean
  error_message?: string
}

/**
 * Fetches the TSOSI JSON resource at the given route.
 *
 * @param route         The URL route
 * @param api           Whether this is a request to TSOSI API
 * @param queryParams   Additional query parameters
 * @param forceFullUrl  Whether to force fetching the full URL
 *                      (with scheme and domain). This is required when fetching
 *                      static front data.
 * @returns The JSON resource.
 */
export async function get(
  route: string,
  api: boolean = false,
  queryParams?: URLSearchParams,
  forceFullUrl: boolean = false,
): Promise<JsonResult> {
  let baseUrl = import.meta.env.BASE_URL
  if (!queryParams) {
    queryParams = new URLSearchParams({})
  }
  if (api) {
    if (!import.meta.env.VITE_API_ROOT) {
      throw Error("MISSING env variable `VITE_API_ROOT`")
    }
    baseUrl = import.meta.env.VITE_API_ROOT
    queryParams.set("format", "json")
  }
  if (forceFullUrl && baseUrl.startsWith("/")) {
    baseUrl = window.location.protocol + "//" + window.location.host + baseUrl
  }
  baseUrl += baseUrl.endsWith("/") ? "" : "/"
  route = route[0] == "/" ? route.slice(1) : route
  const url = new URL(baseUrl + route)

  url.searchParams.forEach((value, key) => queryParams.append(key, value))
  url.search = "?" + queryParams.toString()

  console.log(`querying URL: "${url.toString()}"`)

  return fetchUrl(url.toString(), api)
}

/**
 * Fetch the JSON resource at the given URL.
 * It expects a full URL.
 *
 * @param url The full well-formed URL to fetch.
 * @param api Whether it's a TSOSI API call. If `true`, it adds a custom HTTP
 *            header. Default `false`.
 * @returns
 */
export async function fetchUrl(
  url: string,
  api: boolean = false,
): Promise<JsonResult> {
  const headers = new Headers()
  if (api) {
    const customHeader = import.meta.env.VITE_CUSTOM_HTTP_HEADER
    const customHeaderValue = import.meta.env.VITE_CUSTOM_HTTP_HEADER_VALUE
    if (!customHeader || !customHeaderValue) {
      console.log(
        "MISSING env variable `VITE_CUSTOM_HTTP_HEADER` or `VITE_CUSTOM_HTTP_HEADER_VALUE`",
      )
    } else {
      headers.append(customHeader, customHeaderValue)
    }
  }
  return fetch(url, {
    headers: headers,
  })
    .then((response) => response.json())
    .then((data) => {
      return {
        data: data,
        error: false,
      }
    })
    .catch(() => {
      // TODO: Print dialog with error message.
      const msg = `Error while querying API with url: ${url}`
      console.log(msg)
      return {
        error: true,
        error_message: msg,
      }
    })
}
