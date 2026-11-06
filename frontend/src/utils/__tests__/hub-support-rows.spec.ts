import { describe, expect, it } from "vitest"

import {
  ARXIV,
  COUPERIN,
  DOAJ,
  ENTITIES,
  ORG,
  apiDate,
  date,
  declaration,
  newSupport,
  transfer,
} from "@/__tests__/hub-fixtures"
import { DATE_FIELDS, type Declaration } from "@/singletons/hub-declarations"
import type { HubTransfer } from "@/singletons/ref-data"
import type { DateWithPrecision } from "@/utils/data-utils"
import { formatAmount } from "@/utils/hub-supports"
import {
  addedRows,
  buildSupportTable,
  defaultCurrency,
  dismissedRows,
  draftFromValues,
  emptyDraft,
  isLocked,
  lockedReason,
  NEW_ROW_ID,
  orphans,
  pairDisabledReasons,
  rowStatus,
  sortRow,
  statusInfo,
  tableRows,
  valuesFromDraft,
  valuesFromTransfer,
  type RowsState,
  type SupportTable,
} from "@/utils/hub-support-rows"

function withDateObjs<T extends Record<string, any>>(values: T): T {
  const result: Record<string, any> = { ...values }
  for (const field of [...DATE_FIELDS, "date_clc"]) {
    const value = result[field] as DateWithPrecision | null | undefined
    if (value) {
      result[field] = { ...value, dateObj: new Date(value.value) }
    }
  }
  return result as T
}

// A transfer as `getHubTransfers` returns it: with its entities
function loaded(values: HubTransfer): HubTransfer {
  return withDateObjs({
    ...values,
    emitter: ENTITIES[values.emitter_id],
    recipient: ENTITIES[values.recipient_id],
    agents: values.agent_ids.map((id) => ENTITIES[id]),
  })
}

function makeTable(
  data: {
    transfers?: HubTransfer[]
    declarations?: Declaration[]
    duplicates?: [string, string][]
  } = {},
): SupportTable {
  return buildSupportTable({
    organization: ORG,
    transfers: (data.transfers ?? []).map(loaded),
    declarations: (data.declarations ?? []).map(withDateObjs),
    duplicatePairs: data.duplicates ?? [],
    getEntity: (id) => ENTITIES[id],
  })
}

const NO_STATE: RowsState = { editing: null, openDuplicates: null }

describe("rowStatus", () => {
  const unconfirmed = transfer()
  const confirmed = transfer({ status: "confirmed" })
  const draftEdit = declaration({ kind: "edit" })
  const submitted = declaration({ status: "submitted" })
  const draftMerge = declaration({ id: 2, kind: "merge" })

  it("shows the change not published yet first", () => {
    expect(rowStatus(draftEdit, [draftMerge], unconfirmed)).toBe("edit")
    expect(rowStatus(newSupport(), [], null)).toBe("new")
  })

  it("then the reconciliation not published yet", () => {
    expect(rowStatus(submitted, [draftMerge], confirmed)).toBe("merge")
  })

  it("then the changes waiting for approval", () => {
    expect(rowStatus(submitted, [], unconfirmed)).toBe("submitted")
    const merge = { ...draftMerge, status: "submitted" as const }
    expect(rowStatus(null, [merge], confirmed)).toBe("submitted")
  })

  it("then whether it's confirmed: none when it is", () => {
    expect(rowStatus(null, [], unconfirmed)).toBe("not_confirmed")
    expect(rowStatus(null, [], confirmed)).toBeNull()
  })
})

describe("buildSupportTable", () => {
  it("lists the new supports first, with their declared values", () => {
    const table = makeTable({
      transfers: [transfer()],
      declarations: [newSupport({ id: 7, agent_ids: [COUPERIN.id] })],
    })
    expect(table.rows.map((r) => r.id)).toEqual(["new-7", "t1"])
    const row = table.rowById.get("new-7")!
    expect(row).toMatchObject({
      transfer: null,
      status: "new",
      emitter: ORG,
      recipient: ARXIV,
      agents: [COUPERIN],
      amount: 500,
      // Not converted yet: in its own currency
      unconverted: true,
      amounts_clc: { EUR: 500 },
      amount_hidden: false,
    })
    // The public page's date: the invoice date here
    expect(row.date_clc?.value).toBe("2025-01-01")
  })

  it("shows the transfers with their status and published values", () => {
    const table = makeTable({
      transfers: [
        transfer({ amount_hidden: true }),
        transfer({ id: "t2", status: "confirmed" }),
      ],
    })
    expect(table.rowById.get("t1")).toMatchObject({
      status: "not_confirmed",
      recipient: DOAJ,
      amounts_clc: { EUR: 1000, USD: 1100 },
      amount_hidden: true,
      unconverted: false,
      removed: false,
    })
    expect(table.rowById.get("t2")!.status).toBeNull()
  })

  it("shows the values of an edit, and fades a removal", () => {
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" })],
      declarations: [
        declaration({
          kind: "edit",
          recipient_id: DOAJ.id,
          amount: 1200,
          currency: "USD",
          date_payment_recipient: apiDate("2024-06"),
        }),
        declaration({ id: 2, kind: "removal", transfer_id: "t2" }),
      ],
    })
    const edited = table.rowById.get("t1")!
    expect(edited).toMatchObject({
      status: "edit",
      amount: 1200,
      currency: "USD",
      amounts_clc: { USD: 1200 },
      unconverted: true,
    })
    expect(edited.date_clc?.value).toBe("2024-06-01")
    expect(edited.declaration?.kind).toBe("edit")
    expect(table.rowById.get("t2")).toMatchObject({
      status: "removal",
      removed: true,
      amount: 1000,
    })
  })

  it("links the reconciliations and possible duplicates to both rows", () => {
    const merge = declaration({
      kind: "merge",
      other_transfer_ids: ["t2"],
    })
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" }), transfer({ id: "t3" })],
      declarations: [merge],
      duplicates: [["t1", "t3"]],
    })
    expect(table.rowById.get("t1")!.reconciliations).toEqual([merge])
    expect(table.rowById.get("t2")!.reconciliations).toEqual([merge])
    expect(table.rowById.get("t2")!.declaration).toBeNull()
    expect(table.rowById.get("t1")!.duplicateIds).toEqual(["t3"])
    expect(table.rowById.get("t3")!.duplicateIds).toEqual(["t1"])
    expect(table.rowById.get("t1")!.status).toBe("merge")
    expect(table.rowById.get("t2")!.status).toBe("merge")
  })
})

describe("tableRows", () => {
  const table = makeTable({
    transfers: [transfer(), transfer({ id: "t2" }), transfer({ id: "t3" })],
    declarations: [newSupport({ id: 7 })],
    duplicates: [["t1", "t3"]],
  })
  const typed = {
    ...valuesFromTransfer(table.transferById.get("t2")!),
    amount: 2000,
  }

  it("lists the saved rows", () => {
    expect(tableRows(table, NO_STATE)).toEqual(table.rows)
  })

  it("shows the values typed in the row being edited", () => {
    const rows = tableRows(table, {
      editing: { rowId: "t2", values: typed },
      openDuplicates: null,
    })
    const edited = rows.find((r) => r.id == "t2")!
    expect(edited.amount).toBe(2000)
    // Sorted by its saved values, so that it doesn't move while typing
    expect(edited.saved).toBe(table.rowById.get("t2"))
    expect(sortRow(table, edited)).toBe(table.rowById.get("t2"))
  })

  it("shows the possible duplicates of a row when open", () => {
    const rows = tableRows(table, { editing: null, openDuplicates: "t1" })
    expect(rows.map((r) => r.id)).toEqual(["new-7", "t1", "t1>t3", "t2", "t3"])
    expect(rows[2].sub?.kind).toBe("duplicate")
  })

  it("adds the row of the support being added", () => {
    expect(addedRows(table, NO_STATE)).toEqual([])
    const values = valuesFromDraft({
      ...emptyDraft("EUR"),
      recipient: DOAJ,
      amount: 300,
      dates: { ...emptyDraft("EUR").dates, date_invoice: "2023-02" },
    })
    const rows = addedRows(table, {
      editing: { rowId: NEW_ROW_ID, values },
      openDuplicates: null,
    })
    expect(rows.map((r) => r.id)).toEqual([NEW_ROW_ID])
    expect(rows[0]).toMatchObject({ amount: 300, recipient: DOAJ })
    expect(rows[0].date_clc?.value).toBe("2023-02-01")
  })
})

describe("orphans", () => {
  it("are the changes of supports missing from the table", () => {
    const missing = declaration({ id: 1, transfer_id: "gone" })
    const mergedAway = declaration({
      id: 2,
      kind: "merge",
      other_transfer_ids: ["gone"],
    })
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" })],
      declarations: [
        missing,
        mergedAway,
        declaration({ id: 3, transfer_id: "t2" }),
        declaration({
          id: 4,
          kind: "merge",
          other_transfer_ids: ["t2", "gone"],
        }),
        newSupport({ id: 5 }),
      ],
    })
    expect(orphans(table)).toEqual([missing, mergedAway])
  })
})

describe("locks and reconciliation rules", () => {
  const submitted = declaration({ status: "submitted" })

  it("tells the rows with changes waiting for approval", () => {
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" })],
      declarations: [
        submitted,
        declaration({
          id: 2,
          kind: "not_duplicate",
          transfer_id: "t2",
          other_transfer_ids: ["t1"],
        }),
      ],
    })
    const [t1, t2] = [table.rowById.get("t1")!, table.rowById.get("t2")!]
    expect(isLocked(t1)).toBe(true)
    expect(isLocked(t2)).toBe(false)
    expect(lockedReason(t1)).toBe("It has a change waiting for approval.")
    expect(lockedReason(t2)).toBeUndefined()
    expect(lockedReason(undefined)).toBe("This support doesn't exist any more.")
  })

  it("can't merge a published support already merged", () => {
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" }), transfer({ id: "t3" })],
      declarations: [
        declaration({ kind: "merge", other_transfer_ids: ["t2"] }),
      ],
    })
    const row = (id: string) => table.rowById.get(id)!
    expect(pairDisabledReasons(table, row("t2"), row("t3"))).toEqual({
      same: "One of them is already marked as the same as another one.",
    })
    const free = makeTable({
      transfers: [transfer(), transfer({ id: "t2" })],
    })
    expect(
      pairDisabledReasons(
        free,
        free.rowById.get("t1")!,
        free.rowById.get("t2")!,
      ),
    ).toEqual({ same: undefined })
  })

  it("can't change a new support waiting for approval", () => {
    const table = makeTable({
      transfers: [transfer()],
      declarations: [newSupport({ id: 7, status: "submitted" })],
    })
    const reason = "Its change is waiting for approval."
    expect(
      pairDisabledReasons(
        table,
        table.rowById.get("new-7")!,
        table.rowById.get("t1")!,
      ),
    ).toEqual({ same: reason, different: reason })
  })

  it("makes a new support the change of a published one not locked", () => {
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2" })],
      declarations: [
        newSupport({ id: 7 }),
        newSupport({ id: 8 }),
        declaration({ id: 9, transfer_id: "t2", status: "submitted" }),
      ],
    })
    const row = (id: string) => table.rowById.get(id)!
    expect(pairDisabledReasons(table, row("new-7"), row("t1"))).toEqual({
      same: undefined,
    })
    expect(pairDisabledReasons(table, row("t2"), row("new-7"))).toEqual({
      same: "It has a change waiting for approval.",
    })
    expect(pairDisabledReasons(table, row("new-7"), row("new-8"))).toEqual({})
  })
})

describe("statusInfo", () => {
  it("names the supports of a reconciliation not published yet", () => {
    const table = makeTable({
      transfers: [
        transfer(),
        transfer({ id: "t2", agent_ids: [COUPERIN.id], amount: 2000 }),
      ],
      declarations: [
        declaration({
          kind: "not_duplicate",
          transfer_id: "t2",
          other_transfer_ids: ["t1"],
        }),
      ],
    })
    const info = statusInfo(table, table.rowById.get("t1")!)
    expect(info).toMatch(/^Marked as a different support from /)
    expect(info).toContain(`via Couperin · ${formatAmount(2000, "EUR")}.`)
    expect(info).toContain("preview and submit")
    // The other row: the support it isn't
    const other = statusInfo(table, table.rowById.get("t2")!)
    expect(other).toContain(formatAmount(1000, "EUR"))
  })

  it("explains the other statuses, and is empty without one", () => {
    const table = makeTable({
      transfers: [transfer(), transfer({ id: "t2", status: "confirmed" })],
      declarations: [newSupport({ id: 7 })],
    })
    expect(statusInfo(table, table.rowById.get("new-7")!)).toContain(
      "preview and submit",
    )
    expect(statusInfo(table, table.rowById.get("t1")!)).toMatch(
      /^Only other organizations declared this support/,
    )
    expect(statusInfo(table, table.rowById.get("t2")!)).toBe("")
  })
})

describe("drafts", () => {
  it("types the values of a support as in the inputs", () => {
    const values = valuesFromTransfer(
      loaded(
        transfer({ agent_ids: [COUPERIN.id], date_start: apiDate("2024-03") }),
      ),
    )
    const draft = draftFromValues(values)
    expect(draft).toMatchObject({
      recipient: DOAJ,
      agents: [COUPERIN],
      amount: 1000,
      currency: "EUR",
    })
    expect(draft.dates).toEqual({
      date_invoice: "",
      date_payment_emitter: "",
      date_payment_recipient: "2024",
      date_start: "2024-03",
      date_end: "",
    })
    // A copy: editing it doesn't change the row
    expect(draft.agents).not.toBe(values.agents)
  })

  it("leaves the invalid dates typed out of the values", () => {
    const draft = emptyDraft("USD")
    draft.dates.date_invoice = "2023-02-29"
    draft.dates.date_start = "2024-03"
    const values = valuesFromDraft(draft)
    expect(values.currency).toBe("USD")
    expect(values.dates.date_invoice).toBeNull()
    expect(values.dates.date_start).toMatchObject({
      value: "2024-03-01",
      precision: "month",
    })
  })

  it("starts a new support in the organization's last currency", () => {
    const transfers = [
      transfer({ currency: "USD", date_clc: date("2022") }),
      transfer({ id: "t2", currency: "GBP", date_clc: date("2024") }),
      // Not the organization's: through a consortium, to another one
      transfer({
        id: "t3",
        emitter_id: COUPERIN.id,
        currency: "CHF",
        date_clc: date("2025"),
      }),
    ]
    expect(defaultCurrency(transfers, ORG.id)).toBe("GBP")
    expect(defaultCurrency([], ORG.id)).toBe("EUR")
  })

  it("lists the rows that a new support was declared not to be", () => {
    expect(dismissedRows(null)).toEqual([])
    expect(
      dismissedRows(
        newSupport({ other_transfer_ids: ["t1"], other_declaration_ids: [8] }),
      ),
    ).toEqual(["t1", "new-8"])
  })
})
