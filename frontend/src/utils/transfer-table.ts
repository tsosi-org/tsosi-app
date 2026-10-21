/**
 * The columns of the transfers table of an organization's page, shared by
 * the public page and the Hub's supports table.
 */
import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import type { TableColumnProps } from "@/components/TableComponent.vue"
import { selectedCurrency } from "@/singletons/currencyStore"
import type {
  DeepReadonly,
  EntityDetails,
  Transfer,
} from "@/singletons/ref-data"
import { getTransferAmountCurrency } from "@/utils/data-utils"
import { getTransferBaseUrl } from "@/utils/url-utils"

/**
 * The columns of the transfers table. Each call returns new objects, so that
 * they can be changed.
 */
export function transferColumns(): TableColumnProps[] {
  return [
    {
      id: "date_clc",
      title: "Date",
      field: "date_clc",
      type: "dateWithPrecision",
      sortable: true,
      info: "The date field is relative. <a href='/pages/faq#what-does-the-date-column-refer-to'>See our FAQ</a>",
      filter: {
        enable: true,
      },
    },
    {
      id: "emitter",
      title: "Supporter",
      field: "emitter",
      type: "entityLink",
      fieldLabel: "emitter.name",
      sortable: true,
      filter: {
        enable: true,
      },
    },
    {
      id: "emitterCountry",
      title: "Country",
      field: "emitter.country",
      type: "country",
      sortable: true,
      filter: {
        enable: true,
      },
    },
    {
      id: "agents",
      title: "Intermediary",
      field: "agents",
      type: "entityLink",
      labelGetter: (item: any) =>
        item.agents
          ?.map(
            (agent: any) =>
              `${agent?.name}` +
              (agent?.short_name ? ` (${agent.short_name})` : ""),
          )
          .join(", ") || "",
      fieldLabel: "agent.name",
      sortable: true,
      info: "When a transfer is done through another entity like a library consortia, it appears in this column.",
      filter: {
        enable: true,
      },
    },
    {
      id: "recipient",
      title: "Beneficiary",
      field: "recipient",
      type: "entityLink",
      labelGetter: (item: any) =>
        `${item.recipient?.name}` +
        (item.recipient?.short_name ? ` (${item.recipient.short_name})` : ""),
      sortable: true,
      filter: {
        enable: true,
      },
    },
    {
      id: "amount",
      title: "Amount",
      labelGetter: (row) =>
        getTransferAmountCurrency(row as Transfer, selectedCurrency.value.id)
          .amount,
      // Amounts without a rate to the selected currency stay in their own
      // currency: show it next to them.
      labelSuffix: (row) => {
        const { amount, currency } = getTransferAmountCurrency(
          row as Transfer,
          selectedCurrency.value.id,
        )
        return amount != null && currency != selectedCurrency.value.id
          ? currency
          : null
      },
      field: "__amount",
      type: "number",
      sortable: true,
      nullValueTemplate: '<span class="data-label hidden-amount">hidden</span>',
      info: "The amount of the support may be hidden. See <a href='/pages/faq#amounts-hidden'>the FAQ</a>",
      currencySelector: true,
    },
    {
      id: "currency",
      title: "Currency",
      labelGetter: (row) =>
        getTransferAmountCurrency(row as Transfer, selectedCurrency.value.id)
          .currency,
      field: "__currency",
      type: "string",
      exportOnly: true,
    },
  ]
}

interface TransferRow {
  emitter_id: string
  recipient_id: string
  agent_ids: readonly string[]
  amount: number | null
}

/**
 * The IDs of the columns that would be empty or redundant for this
 * organization's transfers.
 */
export function hiddenTransferColumns(
  entity: DeepReadonly<EntityDetails>,
  transfers: TransferRow[],
): string[] {
  const toRemoveCols: string[] = []
  if (transfers.every((t) => t.amount == null)) {
    toRemoveCols.push("currency")
    if (entity.is_recipient) {
      toRemoveCols.push("amount")
    }
  }
  if (transfers.every((t) => t.agent_ids.length == 0)) {
    toRemoveCols.push("agents")
  }
  if (transfers.every((t) => t.emitter_id == entity.id)) {
    toRemoveCols.push("emitter")
  }
  if (!entity.is_recipient) {
    toRemoveCols.push("emitterCountry")
  }
  if (transfers.every((t) => t.recipient_id == entity.id)) {
    toRemoveCols.push("recipient")
  }
  return toRemoveCols
}

// The "…" button linking to the transfer's page
export const transferDetailsButton: ButtonProps = {
  id: "transferDetails",
  icon: ["fas", "ellipsis"],
  type: "pageLink",
  linkConfig: {
    base: getTransferBaseUrl(),
    suffix: "id",
    suffixType: "field",
  },
}
