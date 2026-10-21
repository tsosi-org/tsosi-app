/**
 * Short descriptions of the supports of the Data Contribution Hub, in its
 * reconciliation panels, notes and submission summary.
 */
import type { DeepReadonly, Entity } from "@/singletons/ref-data"
import {
  formatDateWithPrecisionObj,
  type DateWithPrecision,
} from "@/utils/data-utils"

export function formatAmount(
  amount: number | null,
  currency: string | null,
): string {
  if (amount == null) {
    return "no amount"
  }
  return `${amount.toLocaleString("fr-FR")} ${currency ?? ""}`.trim()
}

function entityLabel(entity: DeepReadonly<Entity> | undefined): string {
  return entity?.short_name || entity?.name || "?"
}

interface SupportValues {
  date_clc: DateWithPrecision | null
  agents?: readonly (DeepReadonly<Entity> | undefined)[] | null
  recipient?: DeepReadonly<Entity> | null
  amount: number | null
  currency: string | null
}

/**
 * The date, intermediaries and amount of a support, and its beneficiary
 * with `withRecipient`.
 */
export function supportLabel(
  values: SupportValues,
  withRecipient: boolean = false,
): string {
  const parts = [
    (values.date_clc && formatDateWithPrecisionObj(values.date_clc)) ||
      "no date",
  ]
  const agents = (values.agents ?? []).filter(Boolean)
  if (agents.length) {
    parts.push(`via ${agents.map(entityLabel).join(", ")}`)
  }
  if (withRecipient) {
    parts.push(entityLabel(values.recipient ?? undefined))
  }
  parts.push(formatAmount(values.amount, values.currency))
  return parts.join(" · ")
}
