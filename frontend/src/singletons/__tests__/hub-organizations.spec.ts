import { describe, expect, it } from "vitest"

import {
  parseOrganizationId,
  SCOPE_INFOS,
  scopeHighlight,
} from "@/singletons/hub-organizations"

describe("parseOrganizationId", () => {
  it.each([
    ["02feahw73", { registry: "ror", value: "02feahw73" }],
    [" 02FEAHW73 ", { registry: "ror", value: "02feahw73" }],
    ["https://ror.org/02feahw73", { registry: "ror", value: "02feahw73" }],
    ["ror.org/02feahw73/", { registry: "ror", value: "02feahw73" }],
    ["http://www.ror.org/02feahw73", { registry: "ror", value: "02feahw73" }],
    ["Q42", { registry: "wikidata", value: "Q42" }],
    ["q42", { registry: "wikidata", value: "Q42" }],
    [
      "https://www.wikidata.org/wiki/Q42/",
      { registry: "wikidata", value: "Q42" },
    ],
    ["http://wikidata.org/entity/q42", { registry: "wikidata", value: "Q42" }],
    ["https://m.wikidata.org/wiki/Q42", { registry: "wikidata", value: "Q42" }],
  ])("parses %j", (text, expected) => {
    expect(parseOrganizationId(text)).toEqual(expected)
  })

  it.each([
    "",
    "CNRS",
    "New lab 2024",
    "Q",
    "Q42a",
    "12feahw73",
    "02feahw7",
    "https://example.org/02feahw73",
  ])("returns null for %j", (text) => {
    expect(parseOrganizationId(text)).toBeNull()
  })
})

describe("scopeHighlight", () => {
  it("highlights the beneficiaries whose supports aren't public", () => {
    expect(scopeHighlight("in_scope")).toBeNull()
    expect(scopeHighlight("to_check")).toEqual({
      class: "scope-highlight scope-to-check",
      tooltip: SCOPE_INFOS.to_check,
    })
    expect(scopeHighlight("out_of_scope")).toEqual({
      class: "scope-highlight scope-out-of-scope",
      tooltip: SCOPE_INFOS.out_of_scope,
    })
    expect(SCOPE_INFOS.to_check).toContain("TSOSI team")
  })
})
