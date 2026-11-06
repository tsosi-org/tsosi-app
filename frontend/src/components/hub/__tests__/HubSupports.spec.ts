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
import {
  defaultCurrency,
  originalCurrency,
  selectedCurrency,
} from "@/singletons/currencyStore"

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

// The status of a row, as shown in its Status column
function statusOf(rowId: string): string | null {
  const tag = rowOf(rowId).querySelector(".cell-tag")
  return tag?.textContent!.trim() ?? null
}

async function pressEscape(target: Element) {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  )
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
  describe("rows and statuses", () => {
    it("shows the status of each row, explained on hover", async () => {
      hubBackend({
        transfers: [
          transfer({ id: "t1" }),
          transfer({ id: "t2", status: "confirmed" }),
          transfer({ id: "t3", status: "confirmed" }),
        ],
        declarations: [
          newSupport({ id: 7 }),
          declaration({ id: 8, transfer_id: "t3", status: "submitted" }),
        ],
      })
      await mountSupports()
      expect(rowsShown()).toHaveLength(4)
      expect(["new-7", "t1", "t2", "t3"].map(statusOf)).toEqual([
        "Created",
        "Not confirmed",
        null,
        "Waiting for approval",
      ])
      expect(
        rowOf("new-7").querySelector(".cell-tag")!.getAttribute("aria-label"),
      ).toMatch(/^Created: .*preview and submit your changes/)
      // No legend, no colors, no details' button
      expect(root().querySelector(".legend")).toBeNull()
      expect(rowOf("t1").className).not.toMatch(/row-not_confirmed/)
      expect(rowOf("t1").querySelector("a.p-button")).toBeNull()
    })

    it("is filtered by status too, the sub-rows with their row", async () => {
      hubBackend({
        transfers: [
          transfer({ id: "t1" }),
          ...Array.from({ length: 10 }, (_, i) =>
            transfer({ id: `c${i}`, status: "confirmed" }),
          ),
        ],
        duplicates: [["t1", "c0"]],
      })
      await mountSupports(false, "/hub/org?f_status=not%20confirmed")
      // The columns' search filters, and the status' select
      expect(
        root().querySelectorAll("input.table-filter").length,
      ).toBeGreaterThan(0)
      expect(root().querySelectorAll(".p-select.table-filter")).toHaveLength(1)
      expect(rowsShown()).toHaveLength(1)
      await act("t1", "Show its possible duplicates")
      expect(actions("t1>c0")).toBeTruthy()
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
      expect(statusOf("t1")).toBe("Confirmed")
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
      expect(statusOf("t1")).toBe("Deleted")
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
      expect(actionNames("t1")).toEqual([])
      const status = rowOf("t1").querySelector(".cell-tag")!
      expect(status.textContent!.trim()).toBe("Waiting for approval")
      expect(status.getAttribute("aria-label")).toContain("read-only")
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

      // The dates' panel, opened from the Date cell, the focus on the
      // invoice date
      dates.click()
      await flushPromises()
      expect(dates.isConnected).toBe(true)
      expect(dates.getAttribute("aria-expanded")).toBe("true")
      expect(panel()!.querySelectorAll("input")).toHaveLength(5)
      expect(document.activeElement).toBe(panel()!.querySelector("input"))
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
      // In the selected currency: without it
      expect(rowOf("t1").textContent).toMatch(/1\s200,5/)
      expect(rowOf("t1").textContent).not.toContain("EUR")
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

    it("cancels the row being edited or added with Escape", async () => {
      const backend = hubBackend({ transfers: [transfer()] })
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "2000")
      await pressEscape(amountInput())
      expect(root().querySelector(".date-cell")).toBeNull()
      // Its saved values
      expect(rowOf("t1").textContent).not.toMatch(/2\D?000/)
      await click("Add a support")
      expect(root().querySelector(".date-cell")).toBeTruthy()
      await pressEscape(panel()!.querySelector("input")!)
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(changes(backend)).toEqual([])
    })

    it("shows an edited amount in its currency, until converted", async () => {
      hubBackend({ transfers: [transfer()] })
      selectedCurrency.value = { id: "USD", name: "US dollar" }
      await mountSupports()
      await act("t1", "Edit")
      await typeIn(amountInput(), "1200")
      await click("Save", edited())
      expect(rowOf("t1").textContent).toMatch(/1\s200\sEUR/)
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
        "Not found? Add an intermediary",
      )
      const form = panel()!.querySelector("form")!
      expect(form.querySelector("h4")!.textContent).toMatch(
        /^\s*Add an intermediary /,
      )
      expect((form.querySelector("input") as HTMLInputElement).value).toBe(
        "New lab",
      )
      await click("Add from its name", form)
      expect(panel()).toBeNull()
      expect(cell("Intermediary").textContent!.trim()).toBe("New lab")
      await click("Save", edited())
      expect(lastPayload(backend)).toMatchObject({
        kind: "edit",
        agent_ids: ["new-lab"],
      })
    })

    it("closes the organization being added once another is picked", async () => {
      hubBackend({ transfers: [transfer({ agent_ids: [COUPERIN.id] })] })
      await mountSupports()
      await act("t1", "Edit")
      await click("Replace", cell("Intermediary"))
      await pickOrganization(
        cell("Intermediary"),
        "New lab",
        "Not found? Add an intermediary",
      )
      expect(panel()!.querySelector("form")).toBeTruthy()
      await pickOrganization(cell("Intermediary"), "arx", "arXiv")
      expect(panel()).toBeNull()
      expect(cell("Intermediary").textContent).toContain("arXiv")
    })
  })

  describe("a failed reconciliation after saved changes (C4)", () => {
    // A draft new support, the same as the published support with a pending
    // confirmation: the confirmation becomes its edit, then the draft is
    // deleted
    async function reconcileAsSame(backend: HubBackend) {
      await mountSupports()
      await act("new-7", "Show its possible duplicates")
      await act("new-7>t1", "The same support")
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
        duplicates: [["new-7", "t1"]],
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
      await reconcileAsSame(backend)
      // The edit saved, the draft gone, the error above the table
      expect(reloadedAfterDelete(backend)).toBe(true)
      expect(actions("new-7")).toBeNull()
      expect(statusOf("t1")).toBe("Edited")
      expect(backend.declarations).toMatchObject([{ id: 1, kind: "edit" }])
      expect(messages()).toContain("Not found.")
    })

    it("reloads the table, the draft still there", async () => {
      const backend = backendWithDraft()
      backend.failures[`DELETE ${DECLARATIONS_ROUTE}/7`] = { status: 500 }
      await reconcileAsSame(backend)
      expect(reloadedAfterDelete(backend)).toBe(true)
      // The error above the table, the edit saved, the draft kept
      expect(messages()).toContain(
        "The change couldn't be saved. Please try again.",
      )
      expect(backend.declarations).toMatchObject([
        { id: 1, kind: "edit" },
        { id: 7, kind: "new" },
      ])
      expect(actions("new-7")).not.toBeNull()
    })
  })

  describe("adding a support", () => {
    async function startAdding() {
      await click("Add a support")
      const row = edited()
      // First, frozen above the others, with its dates' panel open, the
      // focus on the invoice date
      expect(row.closest("tbody")!.querySelector("tr")).toBe(row)
      expect(panel()!.querySelectorAll("input")).toHaveLength(5)
      expect(document.activeElement).toBe(panel()!.querySelector("input"))
      return row
    }

    async function fillSupport() {
      await pickOrganization(cell("Beneficiary"), "arx", "arXiv")
      await typeDate("Invoice date", "2025")
      await typeIn(amountInput(), "500")
    }

    it("saves a new support in the currency selected", async () => {
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
        currency: "EUR",
        date_invoice: "2025",
        date_payment_emitter: null,
        date_payment_recipient: null,
        date_start: null,
        date_end: null,
        other_transfer_ids: [],
        other_declaration_ids: [],
      })
      expect(actionNames("new-100")).toEqual(["Edit", "Undo the change"])
      expect(statusOf("new-100")).toBe("Created")
    })

    it("starts in the organization's last currency, without one selected", async () => {
      hubBackend({
        transfers: [transfer({ currency: "USD", status: "confirmed" })],
      })
      selectedCurrency.value = originalCurrency
      await mountSupports()
      await startAdding()
      expect(edited().querySelector(".p-select-label")!.textContent).toBe("USD")
    })

    it("has no Currency column, but the currency selector", async () => {
      hubBackend({ transfers: [transfer()] })
      await mountSupports()
      const headers = [...root().querySelectorAll("thead th")].map((th) =>
        th.textContent!.trim(),
      )
      expect(headers.some((h) => h.startsWith("Currency"))).toBe(false)
      const amount =
        root().querySelectorAll("thead th")[
          headers.findIndex((h) => h.startsWith("Amount"))
        ]
      expect(amount.querySelector(".header-currency-selector")).toBeTruthy()
    })

    it("saves it at once, its possible duplicates shown once saved", async () => {
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
        // Reported by the backend once the new support is saved
        duplicates: [["new-100", "t1"]],
      })
      await mountSupports()
      await startAdding()
      await fillSupport()
      await wait(450)
      await flushPromises()
      // No match is looked up while typing
      expect(backend.requests.some((r) => r.route.includes("matches"))).toBe(
        false,
      )
      expect(root().querySelector("tr.sub-row")).toBeNull()
      await click("Save", edited())
      expect(lastPayload(backend)).toMatchObject({
        kind: "new",
        other_transfer_ids: [],
      })
      expect(root().querySelector(".date-cell")).toBeNull()
      expect(statusOf("new-100")).toBe("Created")
      expect(actionNames("new-100")).toContain("Show its possible duplicates")
    })
  })

  describe("possible duplicates", () => {
    it("marks two published supports as the same, or not", async () => {
      const backend = hubBackend({
        transfers: [transfer(), transfer({ id: "t2", amount: 2000 })],
        duplicates: [["t1", "t2"]],
      })
      await mountSupports()
      // First, in red
      expect(actionNames("t1")[0]).toBe("Show its possible duplicates")
      expect(
        findButton(actions("t1")!, "Show its possible duplicates")!.className,
      ).toContain("p-button-danger")
      expect(rowOf("t2").className).not.toContain("duplicate-match")
      await act("t1", "Show its possible duplicates")
      expect(
        findButton(
          actions("t1")!,
          "Hide its possible duplicates",
        )!.getAttribute("aria-pressed"),
      ).toBe("true")
      // Colored, under the row and in the rest of the table
      expect(rowOf("t1>t2").className).toContain("duplicate-match")
      expect(rowOf("t2").className).toContain("duplicate-match")
      expect(rowOf("t1").className).not.toContain("duplicate-match")
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
      expect(statusOf("t1")).toBe("Merged")
      const info = rowOf("t1").querySelector(".cell-tag")!
      expect(info.getAttribute("aria-label")).toMatch(
        /^Merged: Marked as the same support as .*\. Not published yet/,
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
      expect(statusOf("t1")).toBe("Edited")
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
