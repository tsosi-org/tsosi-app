import { afterEach, describe, expect, it } from "vitest"

import { mountComponent } from "@/__tests__/mount"
import SupportDates from "@/components/hub/SupportDates.vue"
import { emptyDraft } from "@/utils/hub-support-rows"

function emptyDates() {
  return emptyDraft(null).dates
}

let unmount: (() => void) | null = null

afterEach(() => {
  unmount?.()
  unmount = null
})

async function mountDates(
  dates = emptyDates(),
  errors: Record<string, string[]> = {},
) {
  const { wrapper } = await mountComponent(SupportDates, {
    props: {
      dates,
      errors,
      "onUpdate:dates": (value: typeof dates) =>
        wrapper.setProps({ dates: value }),
    },
  })
  unmount = () => wrapper.unmount()
  return wrapper
}

function input(wrapper: Awaited<ReturnType<typeof mountDates>>, label: string) {
  const labelElement = wrapper
    .findAll("label")
    .find((l) => l.text().includes(label))!
  return wrapper.find(`#${CSS.escape(labelElement.attributes("for")!)}`)
}

describe("SupportDates", () => {
  it("labels the five dates", async () => {
    const wrapper = await mountDates()
    expect(wrapper.findAll("label").map((l) => l.text())).toEqual([
      "Invoice date",
      "Date sent",
      "Date received",
      "Agreement start",
      "Agreement end",
    ])
    expect(wrapper.findAll("input")).toHaveLength(5)
  })

  it("flags the invalid dates as they're typed", async () => {
    const dates = emptyDates()
    const wrapper = await mountDates(dates)
    const invoice = input(wrapper, "Invoice date")
    await invoice.setValue("2023-02-29")
    expect(dates.date_invoice).toBe("2023-02-29")
    expect(invoice.classes()).toContain("p-invalid")
    await invoice.setValue("2024-02-29")
    expect(invoice.classes()).not.toContain("p-invalid")
    // Empty is valid
    await invoice.setValue("")
    expect(invoice.classes()).not.toContain("p-invalid")
  })

  it("flags the dates with an error, listed by the panel", async () => {
    const wrapper = await mountDates(emptyDates(), {
      date_end: ["Enter both the agreement start and end dates, or neither."],
    })
    expect(input(wrapper, "Agreement end").classes()).toContain("p-invalid")
    expect(input(wrapper, "Agreement start").classes()).not.toContain(
      "p-invalid",
    )
    expect(wrapper.text()).not.toContain("Enter both")
  })
})
