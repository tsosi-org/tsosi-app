/**
 * Subscription to the newsletter: the API applies the (un)subscription to the
 * mailing list right away.
 */
import { apiRequest } from "@/services/api"

export type NewsletterAction = "subscribe" | "unsubscribe"

/** (Un)subscribe the e-mail to the newsletter: the error message, if any. */
export async function requestNewsletter(
  action: NewsletterAction,
  email: string,
): Promise<string | null> {
  const result = await apiRequest(`newsletter/${action}`, "POST", { email })
  if (!result.error) {
    return null
  }
  if (result.status === 429) {
    return "Too many attempts, please try again later."
  }
  return result.data?.error ?? "The request failed, please try again later."
}
