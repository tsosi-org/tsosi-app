import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"
import { defineComponent, h, ref, type Component } from "vue"

import { mountComponent } from "@/__tests__/mount"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { transferDetailsButton } from "@/utils/transfer-table"

let wrapper: VueWrapper | null = null

function root(): HTMLElement {
  return wrapper!.element as HTMLElement
}

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

const columns: TableColumnProps[] = [
  { id: "name", title: "Name", field: "name", type: "string", sortable: true },
  { id: "rank", title: "Rank", field: "rank", type: "number", sortable: true },
]

type Row = { id: string; name: string; rank: number; public?: boolean }

const ROWS: Row[] = [
  { id: "a", name: "Alpha", rank: 2, public: true },
  { id: "b", name: "Beta", rank: 1 },
  { id: "c", name: "Gamma", rank: 3, public: true },
]

// A host whose state the tests change, as the table's parents do
function host(props: () => Record<string, unknown>) {
  return defineComponent({
    setup() {
      return () =>
        h(
          Table as Component,
          { id: "test", columns, rowUniqueId: "id", ...props() },
          {
            actionsHeader: () => h("button", { class: "add" }, "Add"),
            actions: ({ data }: { data: Row }) =>
              h("button", { class: "act" }, `Act ${data.id}`),
            cell: ({ data }: { data: Row }) =>
              h("input", { class: "cell-input", value: data.name }),
            expansion: ({ data }: { data: Row }) =>
              h("div", { class: "panel" }, `Panel ${data.id}`),
          },
        )
    },
  })
}

async function mountTable(
  props: () => Record<string, unknown>,
  route?: string,
) {
  const mounted = await mountComponent(host(props), { route })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return mounted
}

function bodyRows(): HTMLTableRowElement[] {
  return [...root().querySelectorAll<HTMLTableRowElement>("tbody tr")]
}

function names(): string[] {
  return bodyRows()
    .filter((r) => !r.className.includes("expansion"))
    .map((r) => r.querySelector("td")!.textContent!.trim())
}

describe("TableComponent", () => {
  it("shows the frozen rows first, whatever the sort", async () => {
    await mountTable(() => ({
      data: ROWS,
      frozenData: [{ id: "new", name: "New", rank: 9 }],
      defaultSort: { sortField: "rank", sortOrder: 1 },
    }))
    expect(names()).toEqual(["New", "Beta", "Alpha", "Gamma"])
  })

  it("sorts the rows by their `sortRow` values", async () => {
    // Beta sorted as if it were Gamma's rank
    const sortRow = (row: Row) => (row.id == "b" ? { ...row, rank: 4 } : row)
    await mountTable(() => ({
      data: ROWS,
      sortRow,
      defaultSort: { sortField: "rank", sortOrder: 1 },
    }))
    expect(names()).toEqual(["Alpha", "Gamma", "Beta"])
  })

  it("shows the `cell` slot in the custom cells, with their class", async () => {
    await mountTable(() => ({
      data: ROWS,
      customCell: (row: Row, column: TableColumnProps) =>
        row.id == "a" && column.id == "name",
      cellClass: (row: Row, column: TableColumnProps) =>
        row.id == "a" && column.id == "name" ? "edited" : undefined,
    }))
    const inputs = root().querySelectorAll<HTMLInputElement>(".cell-input")
    expect(inputs).toHaveLength(1)
    expect(inputs[0].value).toBe("Alpha")
    expect(inputs[0].parentElement!.className).toBe("edited")
  })

  it("tags the organizations of the columns with a `tagGetter`", async () => {
    const organization = (row: Row) => ({
      id: row.id,
      name: `Org ${row.name}`,
      identifiers: [],
    })
    await mountTable(() => ({
      data: ROWS.map((row) => ({ ...row, org: organization(row) })),
      columns: [
        ...columns,
        {
          id: "org",
          title: "Organization",
          field: "org",
          type: "entityLink",
          tagGetter: (row: Row) =>
            row.rank > 2 ? { value: "Low", severity: "warn" } : null,
        },
      ],
    }))
    const tags = [...wrapper!.element.querySelectorAll(".cell-tag")]
    expect(tags.map((t) => t.textContent)).toEqual(["Low"])
    expect(tags[0].closest("tr")!.textContent).toContain("Gamma")
  })

  it("has the actions of each row, and of the header", async () => {
    await mountTable(() => ({
      data: ROWS,
      buttons: [transferDetailsButton],
      hideButtons: (row: Row) => !row.public,
    }))
    expect(wrapper!.find("thead .add").exists()).toBe(true)
    expect(
      [...wrapper!.element.querySelectorAll(".act")].map((b) => b.textContent),
    ).toEqual(["Act a", "Act b", "Act c"])
    // The buttons of the rows with them
    const withButtons = bodyRows().filter((r) => r.querySelector("a"))
    expect(withButtons.map((r) => r.textContent)).toEqual([
      expect.stringContaining("Alpha"),
      expect.stringContaining("Gamma"),
    ])
  })

  it("expands the row given, under it", async () => {
    const expanded = ref<string | null>(null)
    await mountTable(() => ({ data: ROWS, expandedRowId: expanded.value }))
    expect(wrapper!.find(".panel").exists()).toBe(false)
    expanded.value = "b"
    await flushPromises()
    const panel = wrapper!.element.querySelector(".panel")!
    expect(panel.textContent).toBe("Panel b")
    expect(panel.closest("tr")!.previousElementSibling!.textContent).toContain(
      "Beta",
    )
  })

  it("keeps the custom cells, and their focus, across renders", async () => {
    const data = ref<Row[]>(ROWS)
    const expanded = ref<string | null>(null)
    const buttons = [transferDetailsButton]
    await mountTable(() => ({
      data: data.value,
      expandedRowId: expanded.value,
      buttons,
      customCell: (row: Row, column: TableColumnProps) =>
        row.id == "a" && column.id == "name",
    }))
    const input = root().querySelector<HTMLInputElement>(".cell-input")!
    input.focus()
    // New rows, as typing in the input makes them
    data.value = ROWS.map((row) => ({ ...row }))
    await flushPromises()
    expanded.value = "a"
    await flushPromises()
    expect(input.isConnected).toBe(true)
    expect(document.activeElement).toBe(input)
  })
})

describe("TableComponent state in the URL", () => {
  // Enough rows for the filters (10) and two pages (20 per page)
  const many: Row[] = Array.from({ length: 25 }, (_, i) => ({
    id: `r${i}`,
    name: `${i % 2 ? "Odd" : "Even"} ${String(i).padStart(2, "0")}`,
    rank: i,
  }))
  const filtered = columns.map((c) =>
    c.id == "name" ? { ...c, filter: { enable: true } } : c,
  )
  const props = () => ({
    data: many,
    columns: filtered,
    defaultSort: { sortField: "rank", sortOrder: 1 },
    urlState: true,
  })

  function wait(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  it("keeps the sort, filters and page in the URL, defaults left out", async () => {
    const { router } = await mountTable(props, "/page?tab=x")
    expect(router.currentRoute.value.query).toEqual({ tab: "x" })
    // Sorted by name: descending on the second click
    const header = [...root().querySelectorAll("th")].find((th) =>
      th.textContent!.includes("Name"),
    )!
    header.click()
    await flushPromises()
    header.click()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({
      tab: "x",
      sort: "-name",
    })
    expect(names()[0]).toBe("Odd 23")
    ;(root().querySelector(".p-paginator-next") as HTMLElement).click()
    await flushPromises()
    expect(router.currentRoute.value.query.page).toBe("2")
    // A filter: back to the first page
    const input = root().querySelector<HTMLInputElement>(".table-filter")!
    input.value = "Even"
    input.dispatchEvent(new Event("input"))
    await wait(500)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({
      tab: "x",
      sort: "-name",
      f_name: "even",
    })
    expect(names()).toHaveLength(13)
  })

  it("starts from the URL, ignoring what isn't valid", async () => {
    const { router } = await mountTable(
      props,
      "/page?sort=-rank,unknown,-rank&page=2&f_name=odd&f_rank=1&tab=x",
    )
    expect(names()[0]).toBe("Odd 23")
    // 12 odd rows: a single page
    expect(names()).toHaveLength(12)
    expect(root().querySelector<HTMLInputElement>(".table-filter")!.value).toBe(
      "odd",
    )
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({
      sort: "-rank",
      f_name: "odd",
      tab: "x",
    })
  })

  it("follows a link to the same page with other params", async () => {
    const { router } = await mountTable(props, "/page")
    await router.push("/page?sort=-rank&page=2")
    await flushPromises()
    expect(names()[0]).toBe("Even 04")
    await router.push("/page")
    await flushPromises()
    expect(names()[0]).toBe("Even 00")
  })

  it("leaves the URL alone without `urlState`", async () => {
    const { router } = await mountTable(
      () => ({ ...props(), urlState: undefined }),
      "/page?sort=-rank",
    )
    expect(names()[0]).toBe("Even 00")
    expect(router.currentRoute.value.query).toEqual({ sort: "-rank" })
  })
})
