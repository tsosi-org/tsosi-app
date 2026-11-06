import { describe, expect, it } from "vitest"

import { mockApi } from "@/__tests__/api-mock"
import {
  computeDateClc,
  deleteDeclaration,
  formatAmountInput,
  formatDateInput,
  getDeclarations,
  newRowId,
  parseAmountInput,
  parseDateInput,
  saveDeclaration,
  submitDeclarations,
} from "@/singletons/hub-declarations"
import type { DateWithPrecision } from "@/utils/data-utils"

function date(value: string, precision: DateWithPrecision["precision"]) {
  return { value, precision }
}

describe("parseDateInput", () => {
  it.each([
    ["2024", date("2024-01-01", "year")],
    ["2024-03", date("2024-03-01", "month")],
    ["2024-03-13", date("2024-03-13", "day")],
    [" 2024-03 ", date("2024-03-01", "month")],
    ["2024-02-29", date("2024-02-29", "day")],
  ])("parses %j", (text, expected) => {
    const parsed = parseDateInput(text)
    expect(parsed).toMatchObject(expected)
    expect(parsed?.dateObj?.toISOString().slice(0, 10)).toBe(expected.value)
  })

  it.each([
    "",
    "24",
    "2024-3",
    "2024-13",
    "2024-00",
    "2023-02-29",
    "2024-04-31",
    "2024/03/13",
    "13/03/2024",
    "2024-03-13T10:00",
  ])("rejects %j", (text) => {
    expect(parseDateInput(text)).toBeNull()
  })
})

describe("formatDateInput", () => {
  it.each([
    [date("2024-01-01", "year"), "2024"],
    [date("2024-03-01", "month"), "2024-03"],
    [date("2024-03-13", "day"), "2024-03-13"],
    [null, ""],
  ])("formats %j as typed", (value, expected) => {
    expect(formatDateInput(value)).toBe(expected)
  })

  it("is the inverse of parseDateInput", () => {
    for (const text of ["2024", "2024-03", "2024-03-13"]) {
      expect(formatDateInput(parseDateInput(text))).toBe(text)
    }
  })
})

describe("computeDateClc", () => {
  const invoice = date("2024-01-15", "day")
  const sent = date("2024-02-01", "month")
  const received = date("2024-03-10", "day")
  const start = date("2024-06-01", "month")

  it("takes received, else sent, else invoice", () => {
    const all = {
      date_invoice: invoice,
      date_payment_emitter: sent,
      date_payment_recipient: received,
    }
    expect(computeDateClc(all)).toEqual({
      date: received,
      field: "date_payment_recipient",
    })
    expect(
      computeDateClc({ ...all, date_payment_recipient: null })?.field,
    ).toBe("date_payment_emitter")
    expect(computeDateClc({ date_invoice: invoice })?.field).toBe(
      "date_invoice",
    )
  })

  it("takes the year of the agreement start last", () => {
    expect(computeDateClc({ date_start: start })).toEqual({
      date: { value: "2024-06-01", precision: "year", dateObj: undefined },
      field: "date_start",
    })
    expect(
      computeDateClc({ date_start: start, date_invoice: invoice })?.field,
    ).toBe("date_invoice")
  })

  it("is null without dates", () => {
    expect(computeDateClc({})).toBeNull()
    expect(computeDateClc({ date_end: start })).toBeNull()
  })

  it("returns a copy", () => {
    const result = computeDateClc({ date_invoice: invoice })
    expect(result?.date).not.toBe(invoice)
  })
})

describe("newRowId", () => {
  it("is the row of a new support", () => {
    expect(newRowId(12)).toBe("new-12")
  })
})

describe("requests", () => {
  it("loads the declarations with their dates", async () => {
    mockApi({
      "hub/entities/T1/declarations": {
        body: {
          declarations: [
            { id: 1, kind: "new", date_invoice: date("2024-03-01", "month") },
          ],
          entities: { e1: { id: "e1", name: "Infra" } },
          possible_duplicates: [["t1", "new-1"]],
        },
      },
    })
    const result = await getDeclarations("T1")
    expect(result?.declarations[0].date_invoice?.dateObj).toBeInstanceOf(Date)
    expect(result?.entities.e1).toMatchObject({ name: "Infra" })
    expect(result?.duplicates).toEqual([["t1", "new-1"]])
  })

  it("returns null on errors", async () => {
    mockApi({ "hub/entities/T1/declarations": { status: 403 } })
    expect(await getDeclarations("T1")).toBeNull()
  })

  it("sends the CSRF token on save", async () => {
    document.cookie = "csrftoken=abc%3D"
    const requests = mockApi({
      "hub/entities/T1/declarations": { status: 201, body: { id: 3 } },
      "hub/entities/T1/declarations/3": { body: { id: 3 } },
    })
    await saveDeclaration("T1", { kind: "new", transfer_id: null })
    await saveDeclaration("T1", { kind: "new", transfer_id: null }, 3)
    expect(requests.map((r) => r.method)).toEqual(["POST", "PUT"])
    expect(requests[0].headers.get("X-CSRFToken")).toBe("abc=")
    expect(requests[0].body).toEqual({ kind: "new", transfer_id: null })
  })
})

describe("deleteDeclaration", () => {
  it("returns the error of a submitted change", async () => {
    mockApi({
      "hub/entities/T1/declarations/3": {
        status: 403,
        body: { detail: "This change is submitted." },
      },
    })
    const result = await deleteDeclaration("T1", 3)
    expect(result).toMatchObject({
      error: true,
      status: 403,
      data: { detail: "This change is submitted." },
    })
  })
})

describe("submitDeclarations", () => {
  it("sends the consent and the changes previewed", async () => {
    const requests = mockApi({
      "hub/entities/T1/submissions": { status: 201, body: { id: 1 } },
    })
    await submitDeclarations("T1", {
      declarationIds: [3, 5],
      declarationsHash: "abc",
    })
    expect(requests[0].method).toBe("POST")
    expect(requests[0].body).toEqual({
      consent: true,
      declaration_ids: [3, 5],
      declarations_hash: "abc",
    })
  })
})

describe("parseAmountInput", () => {
  it.each([
    ["1500", 1500],
    ["1500.50", 1500.5],
    ["1500,50", 1500.5],
    ["1500.5", 1500.5],
    ["1 500,50", 1500.5],
    ["1\u00a0500,50", 1500.5],
    ["1\u202f500.50", 1500.5],
    ["  1500  ", 1500],
    // A trailing separator while typing (C7)
    ["1500.", 1500],
    ["1500,", 1500],
    // A single separator is the decimal one, with any number of decimals,
    // as in the 3-decimal currencies (C7)
    ["1,500", 1.5],
    ["1.234", 1.234],
    ["0,500", 0.5],
    ["1500.505", 1500.505],
    [".50", 0.5],
    ["0", 0],
  ])("parses %j", (text, amount) => {
    expect(parseAmountInput(text)).toEqual({ amount })
  })

  it("is empty without amount", () => {
    expect(parseAmountInput("  ")).toEqual({ amount: null })
  })

  it.each([
    "abc",
    "-100",
    "+100",
    "1e3",
    ".",
    ",",
    // A single decimal separator
    "1,500.50",
    "1.500,50",
    "1.5.0",
    "1'500",
    "1 500,50 EUR",
    // Not a finite number
    "9".repeat(400),
  ])("rejects %j", (text) => {
    expect(parseAmountInput(text)).toBeNull()
  })

  it("formats the amounts to type them again", () => {
    for (const amount of [1500, 1500.5, 0.25]) {
      const text = formatAmountInput(amount)
      expect(parseAmountInput(text)).toEqual({ amount })
    }
    expect(formatAmountInput(null)).toBe("")
  })
})
