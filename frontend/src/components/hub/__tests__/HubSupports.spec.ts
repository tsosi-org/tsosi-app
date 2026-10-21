import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import {
  changes,
  DECLARATIONS_ROUTE,
  hubBackend,
  type HubBackend,
} from "@/__tests__/hub-backend"
import {
  ARXIV,
  COUPERIN,
  ORG,
  apiDate,
  declaration,
  newSupport,
  submission,
  transfer,
} from "@/__tests__/hub-fixtures"
import { buttonNames, findButton, mountComponent } from "@/__tests__/mount"
import HubSupports from "@/components/hub/HubSupports.vue"
import { defaultCurrency, selectedCurrency } from "@/singletons/currencyStore"

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
  selectedCurrency.value = defaultCurrency
})

async function mountSupports(readOnly = false, route?: string) {
  const mounted = await mountComponent(HubSupports, {
    props: { organization: ORG, readOnly },
    route,
  })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return mounted
}

function root(): HTMLElement {
  return wrapper!.element as HTMLElement
}

// The actions of a row: its buttons, by their accessible name
function actions(rowId: string): HTMLElement | null {
  return root().querySelector(`[data-row-id="${rowId}"]`)
}

function rowOf(rowId: string): HTMLTableRowElement {
  const row = actions(rowId)?.closest("tr")
  expect(row, rowId).toBeTruthy()
  return row as HTMLTableRowElement
}

function actionNames(rowId: string): string[] {
  const element = actions(rowId)
  return element ? buttonNames(element) : []
}

async function act(rowId: string, name: string | RegExp) {
  const button = findButton(actions(rowId)!, name)
  expect(button, `${rowId}: ${name}`).toBeDefined()
  expect(button!.disabled, `${rowId}: ${name} disabled`).toBe(false)
  button!.click()
  await flushPromises()
}

async function click(name: string | RegExp, within: Element = root()) {
  const button = findButton(within, name)
  expect(button, String(name)).toBeDefined()
  button!.click()
  await flushPromises()
}

function rowsShown(): HTMLTableRowElement[] {
  return [...root().querySelectorAll<HTMLTableRowElement>("tr.support-row")]
}

function messages(): string[] {
  return [...root().querySelectorAll(".p-message")].map((m) =>
    m.textContent!.replace(/\s+/g, " ").trim(),
  )
}

// The row being edited
function edited(): HTMLTableRowElement {
  const button = root().querySelector(".date-cell")
  expect(button, "row being edited").toBeTruthy()
  return button!.closest("tr")!
}

async function typeIn(input: Element, value: string) {
  const element = input as HTMLInputElement
  element.value = value
  element.dispatchEvent(new Event("input"))
  await flushPromises()
}

function amountInput(): Element {
  return edited().querySelector('input[aria-label^="Amount"]')!
}

// The cell of a column in the row being edited
function cell(title: string): HTMLElement {
  const headers = [...root().querySelectorAll("thead th")]
  const index = headers.findIndex((th) => th.textContent!.includes(title))
  expect(index, title).toBeGreaterThanOrEqual(0)
  return edited().children[index] as HTMLElement
}

// The panel under the row being edited
function panel(): HTMLElement | null {
  return root().querySelector(".support-row-panel")
}

async function typeDate(label: string, value: string) {
  const field = [...panel()!.querySelectorAll(".field")].find((f) =>
    f.querySelector("label")!.textContent!.includes(label),
  )!
  await typeIn(field.querySelector("input")!, value)
}

async function pickOrganization(cell: Element, query: string, name: string) {
  await typeIn(cell.querySelector("input")!, query)
  await wait(260)
  await flushPromises()
  const option = [
    ...document.querySelectorAll<HTMLElement>(".search-result"),
  ].find((o) => o.textContent!.includes(name))
  expect(option, name).toBeDefined()
  option!.click()
  await flushPromises()
}

function lastPayload(backend: HubBackend) {
  return backend.requests.filter((r) => r.method != "GET").at(-1)?.body
}

describe("HubSupports", () => {
  describe("rows and legend", () => {
    it("counts the rows by status, and filters them", async () => {
      hubBackend({
        transfers: [
          transfer({ id: "t1" }),
          transfer({ id: "t2", status: "confirmed" }),
          transfer({ id: "t3", status: "confirmed" }),
          transfer({ id: "t4", status: "confirmed" }),
          transfer({ id: "t5", status: "confirmed" }),
        ],
        declarations: [
          newSupport({ id: 7 }),
          declaration({ id: 8, transfer_id: "t5", status: "submitted" }),
        ],
        duplicates: [["t3", "t4"]],
      })
      await mountSupports()
      expect(rowsShown()).toHaveLength(6)
      const legend = [...root().querySelectorAll(".legend-item")]
      expect(
        legend.map((l) => l.textContent!.replace(/\s+/g, " ").trim()),
      ).toEqual([
        "Not confirmed 1",
        "Possible duplicate 2",
        "Not published 1",
        "Waiting for approval 1",
      ])
      // The rows of a status only, until it's clicked again
      ;(legend[1] as HTMLElement).click()
      await flushPromises()
      expect(legend[1].getAttribute("aria-pressed")).toBe("true")
      expect(rowsShown().map((r) => r.className)).toEqual([
        expect.stringContaining("row-duplicate"),
        expect.stringContaining("row-duplicate"),
      ])
      ;(legend[1] as HTMLElement).click()
      await flushPromises()
      expect(rowsShown()).toHaveLength(6)
    })

    it("keeps the status picked in the URL", async () => {
      hubBackend({
        transfers: [
          transfer({ id: "t1" }),
          transfer({ id: "t2", status: "confirmed" }),
        ],
      })
      const { router } = await mountSupports(
        false,
        "/hub/org?status=not_confirmed",
      )
      expect(rowsShown()).toHaveLength(1)
      expect(
        root().querySelector(".legend-item.active")!.textContent,
      ).toContain("Not confirmed")
      ;(root().querySelector(".legend-item.active") as HTMLElement).click()
      await flushPromises()
      expect(router.currentRoute.value.query).toEqual({})
      expect(rowsShown()).toHaveLength(2)
    })

    it("ignores a status of the URL without rows", async () => {
      hubBackend({ transfers: [transfer({ id: "t1", status: "confirmed" })] })
      const { router } = await mountSupports(false, "/hub/org?status=duplicate")
      expect(rowsShown()).toHaveLength(1)
      expect(router.currentRoute.value.query).toEqual({})
    })

    it("tells when there's no support yet", async () => {
      hubBackend()
      await mountSupports()
      expect(root().querySelector(".empty")!.textContent).toContain(
        "TSOSI doesn't know any support from this organization yet.",
      )
      await click("Add a support")
      expect(root().querySelector(".date-cell")).toBeTruthy()
    })

    it("tells when the supports couldn't be loaded", async () => {
      const backend = hubBackend()
      backend.failures[`GET ${DECLARATIONS_ROUTE}`] = { status: 500 }
      await mountSupports()
      expect(messages()).toEqual([
        "The supports couldn't be loaded. Please try again later.",
      ])
    })
  })

  describe("row actions", () => {
    it("confirms a support, then undoes it", async () => {
      const backend = hubBackend({ transfers: [transfer()] })
      await mountSupports()
      expect(actionNames("t1")).toEqual(["Edit", "Confirm"])
      expect(findButton(root(), /^Preview and submit/)!.disabled).toBe(true)

      await act("t1", "Confirm")
      expect(changes(backend)).toEqual(["POST declarations"])
      expect(lastPayload(backend)).toEqual({
        kind: "confirmation",
        transfer_id: "t1",
      })
      expect(rowOf("t1").className).toContain("row-unpublished")
      expect(actionNames("t1")).toEqual(["Edit", "Undo the change"])
      const submit = findButton(root(), /^Preview and submit/)!
      expect(submit.textContent).toContain("(1 change)")
      expect(submit.disabled).toBe(false)
      // The focus stays on the row
      expect(document.activeElement?.closest("[data-row-id]")).toBe(
        actions("t1"),
      )

      await act("t1", "Undo the change")
      expect(changes(backend).at(-1)).toBe("DELETE declarations/100")
      expect(actionNames("t1")).toEqual(["Edit", "Confirm"])
    })

    it("removes a support the organization declared, faded", async () => {
      const backend = hubBackend({
        transfers: [transfer({ status: "confirmed" })],
      })
      await mountSupports()
      expect(actionNames("t1")).toEqual(["Edit", "Remove this support"])
      await act("t1", "Remove this support")
      expect(lastPayload(backend)).toEqual({
        kind: "removal",
        transfer_id: "t1",
      })
      expect(rowOf("t1").className).toContain("row-removed")
    })

    it("tells why an undo failed (F5)", async () => {
      const backend = hubBackend({
        transfers: [transfer()],
        declarations: [declaration()],
      })
      backend.failures[`DELETE ${DECLARATIONS_ROUTE}/1`] = {
        status: 403,
        body: {
          detail: "This change is submitted, it can't be changed any more.",
        },
      }
      await mountSupports()
      await act("t1", "Undo the change")
      expect(messages()).toContain(
        "This change is submitted, it can't be changed any more.",
      )
    })

    it("locks the changes waiting for approval", async () => {
      hubBackend({
        transfers: [transfer()],
        declarations: [declaration({ status: "submitted" })],
        submissions: [submission({ changes_count: 1 })],
      })
      await mountSupports()
      expect(messages()[0]).toMatch(
        /^Submission waiting for approval by the TSOSI team\. Sent on .* by member@uni\.edu, with 1 change\./,
      )
      expect(rowOf("t1").className).toContain("row-submitted")
      expect(actionNames("t1")).toEqual([])
      const icons = [...rowOf("t1").querySelectorAll(".row-icon")]
      expect(icons.map((i) => i.getAttribute("aria-label"))).toEqual([
        "Confirmation (waiting for approval)",
        "Waiting for approval by the TSOSI team: read-only until then.",
      ])
    })

    it("lists the changes of supports gone, to undo", async () => {
      const backend = hubBackend({
        transfers: [transfer()],
        declarations: [declaration({ transfer_id: "gone" })],
      })
      await mountSupports()
      const warning = root().querySelector(".orphans")!
      expect(warning.textContent).toContain("Confirmation")
      await click("Undo", warning)
      expect(changes(backend)).toEqual(["DELETE declarations/1"])
      expect(root().querySelector(".orphans")).toBeNull()
    })

    it("is read-only for the TSOSI team", async () => {
      hubBackend({
        transfers: [transfer()],
        declarations: [newSupport({ id: 7 })],
      })
      await mountSupports(true)
      expect(rowsShown()).toHaveLength(2)
      expect(root().querySelectorAll("[data-row-id]")).toHaveLength(0)
      expect(findButton(root(), "Add a support")).toBeUndefined()
      expect(findButton(root(), /^Preview and submit/)).toBeUndefined()
    })
  })

  describe("editing a row", () => {
    it("edits the cells in place, the dates in a panel", async () => {
      const backend = hubBackend({
        transfers: [transfer({ agent_ids: [COUPERIN.id] })],
      })
      await mountSupports()
      await act("t1", "Edit")
      const row = edited()
      // The focus on the first cell: the dates
      const dates = row.querySelector<HTMLButtonElement>(".date-cell")!
      expect(document.activeElement).toBe(dates)
      expect(dates.getAttribute("aria-expanded")).toBe("false")
      expect(panel()).toBeNull()
      expect(buttonNames(row)).toEqual([
        "Dates: 2024",
        // The intermediary, then the beneficiary
        "Replace",
        "No intermediary",
        "Replace",
        "Cancel",
        "Save",
      ])
      expect((amountInput() as HTMLInputElement).value).toBe("1000")
      // Only the row being edited has actions
      expect(root().querySelectorAll("[data-row-id]")).toHaveLength(1)

      // The dates' panel, opened from the Date cell, the focus kept on it
      dates.click()
      await flushPromises()
      expect(dates.isConnected).toBe(true)
      expect(document.activeElement).toBe(dates)
      expect(dates.getAttribute("aria-expanded")).toBe("true")
      expect(panel()!.querySelectorAll("input")).toHaveLength(5)
      // Closed by the other cells
      const amount = amountInput() as HTMLInputElement
      amount.focus()
      await flushPromises()
      expect(panel()).toBeNull()
      // Typed in place, the focus kept in the input
      await typeIn(amount, "1 200,5")
      await typeIn(amount, "1 200,50")
      expect(amount.isConnected).toBe(true)
      expect(document.activeElement).toBe(amount)
      dates.click()
      await flushPromises()
      await typeDate("Agreement start", "2024-01")
      await typeDate("Agreement end", "2024-12")
      await click("Save", edited())
      expect(changes(backend)).toEqual(["POST declarations"])
      expect(lastPayload(backend)).toEqual({
        kind: "edit",
        transfer_id: "t1",
        recipient_id: "doaj",
        agent_ids: [COUPERIN.id],
        amount: 1200.5,
        currency: "EUR",
        date_invoice: null,
        date_payment_emitter: null,
        date_payment_recipient: "2024",
        date_start: "2024-01",
        date_end: "2024-12",
      })
      // Closed, the focus back on the row
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(document.activeElement?.closest("[data-row-id]")).toBe(
        actions("t1"),
      )
      // Shown in its own currency until converted
      expect(rowOf("t1").textContent).toMatch(/1\s200,5EUR/)
    })

    it("fades the rest of the table while a row is edited", async () => {
      hubBackend({ transfers: [transfer(), transfer({ id: "t2" })] })
      await mountSupports()
      expect(root().className).not.toContain("is-editing")
      await act("t1", "Edit")
      expect(root().className).toContain("is-editing")
      expect(
        rowsShown().map((r) => r.classList.contains("row-editing")),
      ).toEqual([true, false])
      expect(edited().className).toContain("row-editing")
      await click("Cancel", edited())
      expect(root().className).not.toContain("is-editing")
    })

    it("shows an edited amount in its currency, until converted", async () => {
      hubBackend({ transfers: [transfer()] })
      selectedCurrency.value = { id: "USD", name: "US dollar" }
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "1200")
      await click("Save", edited())
      expect(rowOf("t1").textContent).toMatch(/1\s200EUR/)
    })

    it("cancels the edit without saving", async () => {
      const backend = hubBackend({ transfers: [transfer()] })
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "5")
      await click("Cancel", edited())
      expect(changes(backend)).toEqual([])
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(document.activeElement).toBe(findButton(actions("t1")!, "Edit"))
    })

    it("confirms the values unchanged, or declares nothing", async () => {
      const backend = hubBackend({
        transfers: [transfer(), transfer({ id: "t2", status: "confirmed" })],
      })
      await mountSupports()
      await act("t1", "Edit")
      await click("Save", edited())
      expect(lastPayload(backend)).toEqual({
        kind: "confirmation",
        transfer_id: "t1",
      })
      // Already declared by the organization
      await act("t2", "Edit")
      await click("Save", edited())
      expect(changes(backend)).toEqual(["POST declarations"])
      expect(root().querySelector(".date-cell")).toBeNull()
    })

    it("lists the errors under the row, its cells flagged", async () => {
      const backend = hubBackend({ transfers: [transfer()] })
      backend.failures[`POST ${DECLARATIONS_ROUTE}`] = {
        status: 400,
        body: {
          amount: ["The amount must be positive."],
          date_end: ["The agreement ends before it starts."],
          detail: "This support already has a change not published yet.",
        },
      }
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "0")
      await click("Save", edited())
      const row = edited()
      expect(row.querySelector(".cell-editor .error")).toBeNull()
      expect(amountInput().className).toContain("p-invalid")
      // The dates' panel opens on their errors
      expect(row.querySelector(".date-cell")!.className).toContain("has-error")
      expect(panel()!.querySelectorAll("input")).toHaveLength(5)
      // In the cells' order, a date's named
      const items = [...panel()!.querySelectorAll(".errors li")]
      expect(items.map((li) => li.textContent!.trim())).toEqual([
        "Agreement end: The agreement ends before it starts.",
        "The amount must be positive.",
        "This support already has a change not published yet.",
      ])
      // Gone once its cell is changed
      await typeIn(amountInput(), "10")
      expect(amountInput().className).not.toContain("p-invalid")
      expect(panel()!.textContent).not.toContain("The amount must be positive.")
    })

    it("stops an empty or invalid amount before saving", async () => {
      const backend = hubBackend({ transfers: [transfer()] })
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "")
      await click("Save", edited())
      expect(changes(backend)).toEqual([])
      expect(amountInput().className).toContain("p-invalid")
      expect(panel()!.textContent!.trim()).toBe("Enter the amount.")
      await typeIn(amountInput(), "12abc")
      // Flagged at once, listed on save
      expect(amountInput().className).toContain("p-invalid")
      expect(panel()).toBeNull()
      await click("Save", edited())
      expect(changes(backend)).toEqual([])
      expect(panel()!.textContent!.trim()).toBe(
        "Enter an amount like 1500, 1500.50 or 1 500,50.",
      )
    })

    it("replaces the intermediary by one added from its name (F6)", async () => {
      const backend = hubBackend({
        transfers: [transfer({ agent_ids: [COUPERIN.id] })],
      })
      await mountSupports()
      await act("t1", "Edit")
      await click("Replace", cell("Intermediary"))
      await pickOrganization(
        cell("Intermediary"),
        "New lab",
        "Add a new organization",
      )
      const form = panel()!.querySelector("form")!
      expect((form.querySelector("input") as HTMLInputElement).value).toBe(
        "New lab",
      )
      await click("Add this organization", form)
      expect(panel()).toBeNull()
      expect(cell("Intermediary").textContent!.trim()).toBe("New lab")
      await click("Save", edited())
      expect(lastPayload(backend)).toMatchObject({
        kind: "edit",
        agent_ids: ["new-lab"],
      })
    })
  })

  describe("a failed save after saved changes (C4)", () => {
    // A draft new support, the change of the published support with a
    // pending confirmation: the confirmation becomes its edit, then the
    // draft is deleted
    async function saveAsChangeOf(backend: HubBackend) {
      await mountSupports()
      await act("new-7", "Edit")
      // The matches found first
      await click("Save", edited())
      await click(
        /^This is the support entered/,
        root().querySelector("tr.sub-row")!,
      )
      await click("Save", edited())
      expect(changes(backend)).toEqual([
        "PUT declarations/1",
        "DELETE declarations/7",
      ])
    }

    // The declarations requested after the deletion
    function reloadedAfterDelete(backend: HubBackend): boolean {
      const index = backend.requests.findLastIndex((r) => r.method == "DELETE")
      return backend.requests
        .slice(index)
        .some((r) => r.method == "GET" && r.route == DECLARATIONS_ROUTE)
    }

    function backendWithDraft() {
      return hubBackend({
        transfers: [transfer()],
        declarations: [
          declaration({ id: 1 }),
          newSupport({ id: 7, recipient_id: "doaj" }),
        ],
        matches: [{ row_id: "t1", amount_differs: true }],
      })
    }

    it("reloads the table when the draft was deleted elsewhere", async () => {
      const backend = backendWithDraft()
      // Undone by another member: a 404
      backend.beforeRequest = (request) => {
        if (request.method == "DELETE") {
          backend.declarations.splice(1, 1)
        }
      }
      await saveAsChangeOf(backend)
      // The edit saved, the draft gone, the error above the table
      expect(reloadedAfterDelete(backend)).toBe(true)
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(actions("new-7")).toBeNull()
      expect(rowOf("t1").className).toContain("row-unpublished")
      expect(backend.declarations).toMatchObject([{ id: 1, kind: "edit" }])
      expect(messages()).toContain("Not found.")
    })

    it("reloads the table, the row still edited", async () => {
      const backend = backendWithDraft()
      backend.failures[`DELETE ${DECLARATIONS_ROUTE}/7`] = { status: 500 }
      await saveAsChangeOf(backend)
      expect(reloadedAfterDelete(backend)).toBe(true)
      expect(edited()).toBe(rowOf("new-7"))
      expect(panel()!.textContent).toContain(
        "The change couldn't be saved. Please try again.",
      )
      // Tried again: the edit saved again, then the draft deleted
      delete backend.failures[`DELETE ${DECLARATIONS_ROUTE}/7`]
      await click("Save", edited())
      expect(changes(backend).slice(2)).toEqual([
        "PUT declarations/1",
        "DELETE declarations/7",
      ])
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(actions("new-7")).toBeNull()
    })
  })

  describe("adding a support", () => {
    async function startAdding() {
      await click("Add a support")
      const row = edited()
      // First, frozen above the others, with its dates' panel open
      expect(row.closest("tbody")!.querySelector("tr")).toBe(row)
      expect(document.activeElement).toBe(row.querySelector(".date-cell"))
      expect(panel()!.querySelectorAll("input")).toHaveLength(5)
      return row
    }

    async function fillSupport() {
      await pickOrganization(cell("Beneficiary"), "arx", "arXiv")
      await typeDate("Invoice date", "2025")
      await typeIn(amountInput(), "500")
    }

    it("saves a new support in the organization's last currency", async () => {
      const backend = hubBackend({
        transfers: [transfer({ currency: "USD", status: "confirmed" })],
      })
      await mountSupports()
      await startAdding()
      await fillSupport()
      await wait(450)
      await flushPromises()
      await click("Save", edited())
      expect(lastPayload(backend)).toEqual({
        kind: "new",
        transfer_id: null,
        recipient_id: ARXIV.id,
        agent_ids: [],
        amount: 500,
        currency: "USD",
        date_invoice: "2025",
        date_payment_emitter: null,
        date_payment_recipient: null,
        date_start: null,
        date_end: null,
        other_transfer_ids: [],
        other_declaration_ids: [],
      })
      expect(actionNames("new-100")).toEqual(["Edit", "Undo the change"])
      expect(rowOf("new-100").className).toContain("row-unpublished")
    })

    it("shows its matches under it, one to pick before saving", async () => {
      const backend = hubBackend({
        transfers: [
          transfer({
            recipient_id: ARXIV.id,
            amount: 500,
            date_invoice: apiDate("2025"),
            date_payment_recipient: null,
            date_clc: apiDate("2025"),
          }),
        ],
        matches: [{ row_id: "t1", amount_differs: false }],
      })
      await mountSupports()
      await startAdding()
      await fillSupport()
      // Saved at once: the matches are found first
      await click("Save", edited())
      expect(changes(backend)).toEqual([])
      const match = root().querySelector<HTMLElement>("tr.sub-row")!
      // Under the row being added, and its panel
      expect(match.previousElementSibling).toBe(edited().nextElementSibling)
      expect(buttonNames(edited())).toContain(
        "None of the supports below: it's a new support",
      )
      expect(panel()!.textContent).toContain(
        "pick the support below that it is (This is it), or None of these",
      )

      // This is it: the confirmation of the support it is
      await click("This is the support entered", match)
      expect(match.className).toContain("picked")
      await click("Save", edited())
      expect(lastPayload(backend)).toEqual({
        kind: "confirmation",
        transfer_id: "t1",
      })
    })

    it("lists the matches it isn't, with None of these", async () => {
      const backend = hubBackend({
        transfers: [transfer({ recipient_id: ARXIV.id })],
        matches: [{ row_id: "t1", amount_differs: true }],
      })
      await mountSupports()
      await startAdding()
      await fillSupport()
      await wait(450)
      await flushPromises()
      expect(panel()!.textContent).toContain(
        "This may already be on TSOSI: is it one of the supports below?",
      )
      const match = root().querySelector<HTMLElement>("tr.sub-row")!
      expect(buttonNames(match)).toEqual([
        "This is the support entered: your amount is published",
      ])
      await click("None of the supports below: it's a new support", edited())
      await click("Save", edited())
      expect(lastPayload(backend)).toMatchObject({
        kind: "new",
        other_transfer_ids: ["t1"],
      })
    })
  })

  describe("possible duplicates", () => {
    it("marks two published supports as the same, or not", async () => {
      const backend = hubBackend({
        transfers: [transfer(), transfer({ id: "t2", amount: 2000 })],
        duplicates: [["t1", "t2"]],
      })
      await mountSupports()
      await act("t1", "Show its possible duplicates")
      expect(
        findButton(
          actions("t1")!,
          "Hide its possible duplicates",
        )!.getAttribute("aria-pressed"),
      ).toBe("true")
      const sub = actions("t1>t2")!
      expect(buttonNames(sub)).toEqual([
        "The same support",
        "Not the same support",
      ])
      await act("t1>t2", "The same support")
      expect(lastPayload(backend)).toEqual({
        kind: "merge",
        transfer_id: "t1",
        other_transfer_ids: ["t2"],
      })
      // Reconciled: closed, and undone from the row
      expect(actions("t1>t2")).toBeNull()
      expect(actionNames("t1")).toEqual([
        "Edit",
        "Confirm",
        "Undo: marked as the same support",
      ])
      const info = rowOf("t1").querySelector(".row-icon")!
      expect(info.getAttribute("aria-label")).toMatch(
        /^The same support as .* \(not published\)$/,
      )

      await act("t1", "Undo: marked as the same support")
      await act("t1", "Show its possible duplicates")
      await act("t1>t2", "Not the same support")
      expect(lastPayload(backend)).toMatchObject({ kind: "not_duplicate" })
    })

    it("makes a new support the change of the same published one", async () => {
      const backend = hubBackend({
        transfers: [transfer()],
        declarations: [newSupport({ id: 7, recipient_id: "doaj" })],
        duplicates: [["new-7", "t1"]],
      })
      await mountSupports()
      await act("new-7", "Show its possible duplicates")
      await act("new-7>t1", "The same support")
      expect(changes(backend)).toEqual(["PUT declarations/7"])
      expect(lastPayload(backend)).toMatchObject({
        kind: "edit",
        transfer_id: "t1",
        amount: 500,
      })
      expect(actions("new-7")).toBeNull()
      expect(rowOf("t1").className).toContain("row-unpublished")
    })

    it("can't make it the change of a support waiting for approval", async () => {
      hubBackend({
        transfers: [transfer()],
        declarations: [
          newSupport({ id: 7 }),
          declaration({ id: 8, status: "submitted" }),
        ],
        duplicates: [["new-7", "t1"]],
      })
      await mountSupports()
      await act("new-7", "Show its possible duplicates")
      const same = findButton(actions("new-7>t1")!, "The same support")!
      expect(same.disabled).toBe(true)
      expect(
        findButton(actions("new-7>t1")!, "Not the same support")!.disabled,
      ).toBe(false)
    })
  })
})
