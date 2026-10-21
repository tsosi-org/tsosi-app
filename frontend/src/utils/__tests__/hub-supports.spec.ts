import { describe, expect, it } from "vitest"

import { recipientScope } from "@/singletons/hub-organizations"
import type { Entity } from "@/singletons/ref-data"
import { formatAmount, supportLabel } from "@/utils/hub-supports"
import { getEntityUrl, getHubEntityRef } from "@/utils/url-utils"

function entity(values: Partial<Entity> = {}): Entity {
  return {
    id: "uuid-1",
    name: "Directory of Open Access Journals",
    identifiers: [],
    is_partner: false,
    is_emitter: false,
    is_agent: false,
    is_recipient: false,
    is_scoss: false,
    is_posi: false,
    is_barcelona: false,
    ...values,
  } as Entity
}

describe("formatAmount", () => {
  it.each([
    [1500, "EUR", "1 500 EUR"],
    [1234.5, "USD", "1 234,5 USD"],
    [0, "EUR", "0 EUR"],
    [100, null, "100"],
    [null, "EUR", "no amount"],
  ])("formats %j %j", (amount, currency, expected) => {
    expect(formatAmount(amount, currency)).toBe(expected)
  })
})

describe("supportLabel", () => {
  const values = {
    date_clc: {
      value: "2024-03-01",
      precision: "month" as const,
      dateObj: new Date("2024-03-01"),
    },
    agents: [entity({ name: "Couperin consortium", short_name: "Couperin" })],
    recipient: entity({ short_name: "DOAJ" }),
    amount: 1000,
    currency: "EUR",
  }

  it("describes the date, intermediaries and amount", () => {
    const label = supportLabel(values)
    expect(label).toMatch(/ · via Couperin · 1 000 EUR$/)
    expect(label).not.toContain("DOAJ")
  })

  it("adds the beneficiary on demand", () => {
    expect(supportLabel(values, true)).toMatch(/ · DOAJ · 1 000 EUR$/)
  })

  it("tells the missing values", () => {
    expect(
      supportLabel(
        { date_clc: null, agents: [undefined], amount: null, currency: null },
        true,
      ),
    ).toBe("no date · ? · no amount")
  })
})

describe("recipientScope", () => {
  it.each([
    // From the Hub, with their scope
    [{ scope: "out_of_scope" as const }, "out_of_scope"],
    [{ scope: "in_scope" as const }, "in_scope"],
    // Without scope yet, e.g. added in the Hub: to be checked once published
    [{ scope: null }, "to_check"],
    // From the reference data, without scope: the public beneficiaries
    [{ is_recipient: true }, "in_scope"],
    [{ is_recipient: false }, "to_check"],
  ])("of %j is %s", (values, expected) => {
    expect(recipientScope(entity(values))).toBe(expected)
  })
})

describe("URLs", () => {
  const identifiers: Entity["identifiers"] = [
    { registry: "ror", value: "02feahw73" },
    { registry: "tsosi", value: "T123456" },
  ]

  it("uses the TSOSI ID in the Hub, else the UUID", () => {
    expect(getHubEntityRef(entity({ identifiers }))).toBe("T123456")
    expect(getHubEntityRef(entity({ identifiers: [identifiers[0]] }))).toBe(
      "uuid-1",
    )
  })

  it("prefers the TSOSI ID, then ROR, on the public site", () => {
    expect(getEntityUrl(entity({ identifiers }))).toBe("/entities/T123456")
    expect(getEntityUrl(entity({ identifiers: [identifiers[0]] }))).toBe(
      "/entities/02feahw73",
    )
    expect(getEntityUrl(entity())).toBe("/entities/uuid-1")
  })
})
