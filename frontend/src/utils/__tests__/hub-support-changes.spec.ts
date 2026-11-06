import { describe, expect, it } from "vitest"

import { mockApi } from "@/__tests__/api-mock"
import {
  ARXIV,
  COUPERIN,
  DOAJ,
  ENTITIES,
  ORG,
  apiDate,
  declaration,
  newSupport,
  transfer,
} from "@/__tests__/hub-fixtures"
import type { Declaration } from "@/singletons/hub-declarations"
import type { HubTransfer } from "@/singletons/ref-data"
import {
  AMOUNT_FORMAT_ERROR,
  asChangeOf,
  draftErrors,
  draftPayloadValues,
  errorMessage,
  errorMessages,
  newSupportOperations,
  newSupportPayload,
  payloadValues,
  reconcileOperations,
  runOperations,
  saveErrors,
  supportChange,
  supportOperations,
  type PayloadValues,
} from "@/utils/hub-support-changes"
import {
  buildSupportTable,
  emptyDraft,
  valuesFromTransfer,
  type SupportTable,
} from "@/utils/hub-support-rows"

function loaded(values: HubTransfer): HubTransfer {
  return {
    ...values,
    emitter: ENTITIES[values.emitter_id],
    recipient: ENTITIES[values.recipient_id],
    agents: values.agent_ids.map((id) => ENTITIES[id]),
  }
}

function makeTable(
  transfers: HubTransfer[],
  declarations: Declaration[] = [],
): SupportTable {
  return buildSupportTable({
    organization: ORG,
    transfers: transfers.map(loaded),
    declarations,
    duplicatePairs: [],
    getEntity: (id) => ENTITIES[id],
  })
}

// The values of the transfer, as the member would type them unchanged
function valuesOf(table: SupportTable, id: string): PayloadValues {
  return payloadValues(valuesFromTransfer(table.transferById.get(id)!))
}

describe("payload values", () => {
  it("are the values sent, dates as typed and intermediaries sorted", () => {
    const table = makeTable([
      transfer({
        agent_ids: [DOAJ.id, COUPERIN.id],
        date_end: apiDate("2025-06"),
      }),
    ])
    expect(valuesOf(table, "t1")).toEqual({
      recipient_id: DOAJ.id,
      agent_ids: [COUPERIN.id, DOAJ.id],
      amount: 1000,
      currency: "EUR",
      date_invoice: null,
      date_payment_emitter: null,
      date_payment_recipient: "2024",
      date_start: null,
      date_end: "2025-06",
    })
  })

  it("send the invalid dates as typed, to get their errors", () => {
    const draft = emptyDraft("EUR")
    draft.dates.date_invoice = " 2023-02-29 "
    draft.dates.date_start = "2024"
    const values: Record<string, unknown> = draftPayloadValues(draft)
    expect(values.date_invoice).toBe("2023-02-29")
    expect(values.date_start).toBe("2024")
    expect(values.date_end).toBeNull()
    expect(values.recipient_id).toBeNull()
  })
})

describe("supportChange", () => {
  const table = makeTable([
    transfer(),
    transfer({ id: "t2", status: "confirmed" }),
  ])

  it("confirms the values declared by others only", () => {
    expect(
      supportChange(table.transferById.get("t1")!, valuesOf(table, "t1")),
    ).toEqual({ kind: "confirmation", transfer_id: "t1" })
  })

  it("is nothing when the organization already declared them", () => {
    expect(
      supportChange(table.transferById.get("t2")!, valuesOf(table, "t2")),
    ).toBeNull()
  })

  it("edits changed values", () => {
    const values = { ...valuesOf(table, "t2"), amount: 1200 }
    expect(supportChange(table.transferById.get("t2")!, values)).toEqual({
      kind: "edit",
      transfer_id: "t2",
      ...values,
    })
  })
})

describe("newSupportPayload", () => {
  it("lists the rows it isn't, of those still in the table", () => {
    const table = makeTable([transfer()], [newSupport({ id: 7 })])
    const values = valuesOf(table, "t1")
    expect(
      newSupportPayload(table, values, ["t1", "gone", "new-7", "new-99"]),
    ).toEqual({
      kind: "new",
      transfer_id: null,
      ...values,
      other_transfer_ids: ["t1"],
      other_declaration_ids: [7],
    })
  })
})

describe("asChangeOf", () => {
  const draft = newSupport({ id: 7 })

  it("turns a draft new support into the change of its match", () => {
    const table = makeTable([transfer()], [draft])
    const values = { ...valuesOf(table, "t1"), amount: 1500 }
    expect(asChangeOf(table, draft, "t1", values)).toEqual({
      saves: [
        { payload: { kind: "edit", transfer_id: "t1", ...values }, id: 7 },
      ],
      deletions: [],
    })
    // The support being added: a new declaration
    expect(asChangeOf(table, null, "t1", valuesOf(table, "t1"))).toEqual({
      saves: [{ payload: { kind: "confirmation", transfer_id: "t1" } }],
      deletions: [],
    })
  })

  it("replaces the support's pending change", () => {
    const existing = declaration({ id: 3, kind: "removal" })
    const table = makeTable([transfer()], [draft, existing])
    expect(asChangeOf(table, draft, "t1", valuesOf(table, "t1"))).toEqual({
      saves: [{ payload: { kind: "confirmation", transfer_id: "t1" }, id: 3 }],
      deletions: [draft],
    })
  })

  it("deletes both when the organization already declared the values", () => {
    const existing = declaration({ id: 3, kind: "edit", amount: 1 })
    const table = makeTable(
      [transfer({ status: "confirmed" })],
      [draft, existing],
    )
    expect(asChangeOf(table, draft, "t1", valuesOf(table, "t1"))).toEqual({
      saves: [],
      deletions: [existing, draft],
    })
  })
})

describe("supportOperations", () => {
  const table = makeTable([transfer({ status: "confirmed" })])
  const t1 = table.transferById.get("t1")!
  const draft = declaration({ kind: "edit" })

  it("saves the edit in the draft, if any", () => {
    const values = { ...valuesOf(table, "t1"), amount: 10 }
    expect(supportOperations(t1, draft, values)).toEqual({
      saves: [
        { payload: { kind: "edit", transfer_id: "t1", ...values }, id: 1 },
      ],
      deletions: [],
    })
  })

  it("undoes the draft when the values are back to the declared ones", () => {
    expect(supportOperations(t1, draft, valuesOf(table, "t1"))).toEqual({
      saves: [],
      deletions: [draft],
    })
    expect(supportOperations(t1, null, valuesOf(table, "t1"))).toEqual({
      saves: [],
      deletions: [],
    })
  })
})

describe("newSupportOperations", () => {
  const draft = newSupport({ id: 7 })
  const other = newSupport({ id: 8, other_transfer_ids: ["t1"] })
  const table = makeTable([transfer(), transfer({ id: "t2" })], [draft, other])
  const values = payloadValues({
    ...valuesFromTransfer(table.transferById.get("t1")!),
    recipient: ARXIV,
    amount: 500,
  })

  it("saves the values, a new support or the draft", () => {
    expect(newSupportOperations(table, null, values)).toEqual({
      saves: [{ payload: newSupportPayload(table, values, []) }],
      deletions: [],
    })
    expect(newSupportOperations(table, draft, values)).toEqual({
      saves: [{ payload: newSupportPayload(table, values, []), id: 7 }],
      deletions: [],
    })
  })

  it("keeps what the draft was declared not to be", () => {
    expect(newSupportOperations(table, other, values)).toEqual({
      saves: [{ payload: newSupportPayload(table, values, ["t1"]), id: 8 }],
      deletions: [],
    })
  })
})

describe("reconcileOperations", () => {
  const first = newSupport({ id: 7 })
  const second = newSupport({ id: 8, other_transfer_ids: ["t2"] })
  const table = makeTable([transfer(), transfer({ id: "t2" })], [first, second])
  const row = (id: string) => table.rowById.get(id)!

  it("merges two published supports, or tells they're different", () => {
    expect(reconcileOperations(table, row("t1"), row("t2"), true)).toEqual({
      saves: [
        {
          payload: {
            kind: "merge",
            transfer_id: "t1",
            other_transfer_ids: ["t2"],
          },
        },
      ],
      deletions: [],
    })
    expect(
      reconcileOperations(table, row("t1"), row("t2"), false).saves[0].payload
        .kind,
    ).toBe("not_duplicate")
  })

  it("makes a new support the change of the same published one", () => {
    const values = payloadValues({
      recipient: ARXIV,
      agents: [],
      amount: 500,
      currency: "EUR",
      dates: {
        date_invoice: { value: "2025-01-01", precision: "year" },
        date_payment_emitter: null,
        date_payment_recipient: null,
        date_start: null,
        date_end: null,
      },
    })
    expect(reconcileOperations(table, row("t1"), row("new-7"), true)).toEqual(
      asChangeOf(table, first, "t1", values),
    )
  })

  it("lists the published support a new one isn't", () => {
    const operations = reconcileOperations(
      table,
      row("new-8"),
      row("t1"),
      false,
    )
    expect(operations.deletions).toEqual([])
    expect(operations.saves).toHaveLength(1)
    expect(operations.saves[0].id).toBe(8)
    // With those it was already declared not to be
    expect(operations.saves[0].payload).toMatchObject({
      kind: "new",
      recipient_id: ARXIV.id,
      other_transfer_ids: ["t2", "t1"],
    })
  })

  it("removes one of two new supports that are the same", () => {
    // The right one, when both are drafts
    expect(
      reconcileOperations(table, row("new-7"), row("new-8"), true),
    ).toEqual({ saves: [], deletions: [second] })
    const operations = reconcileOperations(
      table,
      row("new-7"),
      row("new-8"),
      false,
    )
    expect(operations.saves[0]).toMatchObject({
      id: 8,
      payload: { other_transfer_ids: ["t2"], other_declaration_ids: [7] },
    })
  })

  it("changes the draft when the other new support is submitted", () => {
    const submitted = newSupport({ id: 9, status: "submitted" })
    const locked = makeTable([transfer()], [first, submitted])
    expect(
      reconcileOperations(
        locked,
        locked.rowById.get("new-7")!,
        locked.rowById.get("new-9")!,
        true,
      ),
    ).toEqual({ saves: [], deletions: [first] })
  })
})

describe("runOperations", () => {
  const route = "hub/entities/org/declarations"

  it("saves, then deletes, the drafts by their ID", async () => {
    const requests = mockApi({
      [route]: { status: 201, body: {} },
      [`${route}/3`]: { body: {} },
      [`${route}/7`]: { status: 204 },
    })
    const result = await runOperations(ORG.id, {
      saves: [
        { payload: { kind: "confirmation", transfer_id: "t2" } },
        { payload: { kind: "confirmation", transfer_id: "t1" }, id: 3 },
      ],
      deletions: [newSupport({ id: 7 })],
    })
    expect(result).toBeNull()
    expect(requests.map((r) => `${r.method} ${r.route}`)).toEqual([
      `POST ${route}`,
      `PUT ${route}/3`,
      `DELETE ${route}/7`,
    ])
  })

  it("stops at the first error, a deletion's too (F5)", async () => {
    const requests = mockApi({
      [`${route}/3`]: { body: {} },
      [`${route}/7`]: {
        status: 403,
        body: { detail: "This change is submitted." },
      },
    })
    const result = await runOperations(ORG.id, {
      saves: [{ payload: { kind: "removal", transfer_id: "t1" }, id: 3 }],
      deletions: [newSupport({ id: 7 }), newSupport({ id: 8 })],
    })
    expect(result).toMatchObject({
      status: 403,
      data: { detail: "This change is submitted." },
    })
    expect(requests).toHaveLength(2)
  })
})

describe("errors", () => {
  it("are the validation errors by field, as lists", () => {
    expect(
      saveErrors({
        status: 400,
        data: { amount: ["Enter the amount."], detail: "Not allowed." },
      }),
    ).toEqual({ amount: ["Enter the amount."], detail: ["Not allowed."] })
  })

  it("are a general message on other failures", () => {
    const message = "The change couldn't be saved. Please try again."
    expect(saveErrors({ status: 500, data: "<html>" })).toEqual({
      detail: [message],
    })
    expect(errorMessage(undefined)).toBe(message)
    expect(
      errorMessage({ transfer_id: ["Pick the support."], detail: "Gone." }),
    ).toBe("Pick the support. Gone.")
  })
})

describe("draftErrors", () => {
  it("stops an empty or invalid amount", () => {
    const draft = { ...emptyDraft("EUR"), amountText: "  " }
    expect(draftErrors(draft)).toEqual({ amount: ["Enter the amount."] })
    draft.amountText = "12abc"
    expect(draftErrors(draft)).toEqual({ amount: [AMOUNT_FORMAT_ERROR] })
    // The others are checked by the server
    draft.amountText = "1 500,50"
    expect(draftErrors(draft)).toEqual({})
  })
})

describe("errorMessages", () => {
  it("lists the cells' errors in their order, then the others", () => {
    expect(
      errorMessages({
        detail: ["Not allowed."],
        amount: ["Enter the amount."],
        date_end: ["The agreement ends before it starts."],
        dates: ["Enter at least one date."],
        recipient_id: ["Pick the beneficiary."],
      }),
    ).toEqual([
      // A date's message names it
      "Agreement end: The agreement ends before it starts.",
      "Enter at least one date.",
      "Pick the beneficiary.",
      "Enter the amount.",
      "Not allowed.",
    ])
    expect(errorMessages({})).toEqual([])
  })
})
