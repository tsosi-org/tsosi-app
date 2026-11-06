import { computed, reactive, ref, type Ref } from "vue"

import { apiRequest } from "@/services/api"
import type { EntityDetails } from "@/singletons/ref-data"
import { csrfHeaders } from "@/singletons/hub-session"

export interface EntityEditData {
  name?: string
  short_name?: string | null
  country?: string | null
  date_inception?: string | null
  description?: string | null
  is_barcelona?: boolean
  website?: string | null
  wikipedia_url?: string | null
  open_science_policy_url?: string | null
  identifiers?: {
    ror?: string | null
    wikidata?: string | null
  }
  infrastructure?: {
    support_url?: string | null
    posi_url?: string | null
    infra_finder_url?: string | null
    date_scoss_start?: string | null
    date_scoss_end?: string | null
  }
}

/**
 * Submit the entity edits, with the Hub session.
 * Return the updated entity details, or the validation errors.
 */
async function submitEntityEdit(
  entityId: string,
  data: EntityEditData,
  logo?: File | null,
  icon?: File | null,
): Promise<{ ok: boolean; data: any; status?: number }> {
  let body: FormData | EntityEditData = data
  if (logo || icon) {
    body = new FormData()
    body.append("data", JSON.stringify(data))
    if (logo) {
      body.append("logo", logo)
    }
    if (icon) {
      body.append("icon", icon)
    }
  }
  const result = await apiRequest(
    `entities/${entityId}/edit/`,
    "PATCH",
    body,
    csrfHeaders(),
  )
  return { ok: !result.error, data: result.data, status: result.status }
}

function toYear(date?: Date | null): number | null {
  return date ? date.getUTCFullYear() : null
}

/**
 * Return the date to send for the given year. Dates are only edited with
 * a year precision: the original date is kept when the year is unchanged,
 * otherwise the 1st of January is used.
 */
function yearToDateString(
  year: number | null,
  original?: Date | null,
): string | null {
  if (!year) {
    return null
  }
  if (original && original.getUTCFullYear() == year) {
    return original.toISOString().slice(0, 10)
  }
  return `${String(year).padStart(4, "0")}-01-01`
}

/**
 * State and actions of the in-place edition of an entity.
 */
export function useEntityEdit(entity: () => EntityDetails) {
  const form = reactive({
    name: "",
    short_name: "",
    country: "",
    date_inception: null as number | null,
    description: "",
    is_barcelona: false,
    website: "",
    wikipedia_url: "",
    open_science_policy_url: "",
    ror: "",
    wikidata: "",
    support_url: "",
    posi_url: "",
    infra_finder_url: "",
    date_scoss_start: null as number | null,
    date_scoss_end: null as number | null,
  })
  const logoFile: Ref<File | null> = ref(null)
  const logoPreview: Ref<string | undefined> = ref()
  const iconFile: Ref<File | null> = ref(null)
  const iconPreview: Ref<string | undefined> = ref()
  const saving = ref(false)
  const errors: Ref<Record<string, any>> = ref({})
  const globalError: Ref<string | null> = ref(null)

  const showInfrastructure = computed(
    () => entity().infrastructure != null || entity().is_recipient,
  )

  function getIdentifier(registry: string): string {
    return entity().identifiers.find((i) => i.registry == registry)?.value ?? ""
  }

  /** Reset the form with the current entity values. */
  function reset() {
    const e = entity()
    Object.assign(form, {
      name: e.name,
      short_name: e.short_name ?? "",
      country: e.country ?? "",
      date_inception: toYear(e.date_inception),
      description: e.description ?? "",
      is_barcelona: e.is_barcelona,
      website: e.website ?? "",
      wikipedia_url: e.wikipedia_url ?? "",
      open_science_policy_url: e.open_science_policy_url ?? "",
      ror: getIdentifier("ror"),
      wikidata: getIdentifier("wikidata"),
      support_url: e.infrastructure?.support_url ?? "",
      posi_url: e.infrastructure?.posi_url ?? "",
      infra_finder_url: e.infrastructure?.infra_finder_url ?? "",
      date_scoss_start: toYear(e.infrastructure?.date_scoss_start),
      date_scoss_end: toYear(e.infrastructure?.date_scoss_end),
    })
    setLogo(null)
    setIcon(null)
    errors.value = {}
    globalError.value = null
  }

  function setImage(
    file: File | null,
    fileRef: Ref<File | null>,
    previewRef: Ref<string | undefined>,
    current?: string,
  ) {
    if (previewRef.value?.startsWith("blob:")) {
      URL.revokeObjectURL(previewRef.value)
    }
    fileRef.value = file
    previewRef.value = file ? URL.createObjectURL(file) : current
  }

  function setLogo(file: File | null) {
    setImage(file, logoFile, logoPreview, entity().logo)
  }

  function setIcon(file: File | null) {
    setImage(file, iconFile, iconPreview, entity().icon)
  }

  /**
   * Format the error(s) of the given field from the API response.
   * Nested fields are given with a dot, ex: `identifiers.ror`.
   */
  function fieldError(path: string): string | null {
    let value: any = errors.value
    for (const key of path.split(".")) {
      value = value?.[key]
    }
    if (!value) {
      return null
    }
    return Array.isArray(value) ? value.join(" ") : String(value)
  }

  /** Submit the edits. Return whether they were saved. */
  async function save(): Promise<boolean> {
    saving.value = true
    errors.value = {}
    globalError.value = null
    const data: EntityEditData = {
      name: form.name,
      short_name: form.short_name || null,
      country: form.country || null,
      date_inception: yearToDateString(
        form.date_inception,
        entity().date_inception,
      ),
      description: form.description || null,
      is_barcelona: form.is_barcelona,
      website: form.website || null,
      wikipedia_url: form.wikipedia_url || null,
      identifiers: {
        ...(!getIdentifier("ror") && form.ror ? { ror: form.ror } : {}),
        ...(!getIdentifier("wikidata") && form.wikidata
          ? { wikidata: form.wikidata }
          : {}),
      },
    }
    if (!showInfrastructure.value) {
      // Institutions only: their open science policy
      data.open_science_policy_url = form.open_science_policy_url || null
    }
    if (showInfrastructure.value) {
      data.infrastructure = {
        support_url: form.support_url || null,
        posi_url: form.posi_url || null,
        infra_finder_url: form.infra_finder_url || null,
        date_scoss_start: yearToDateString(
          form.date_scoss_start,
          entity().infrastructure?.date_scoss_start,
        ),
        date_scoss_end: yearToDateString(
          form.date_scoss_end,
          entity().infrastructure?.date_scoss_end,
        ),
      }
    }
    const result = await submitEntityEdit(
      entity().id,
      data,
      logoFile.value,
      iconFile.value,
    )
    saving.value = false
    if (result.ok) {
      return true
    }
    if (result.status == 400 && result.data) {
      errors.value = result.data
      globalError.value = "Some fields are invalid, please check them below."
    } else if (result.status == 403) {
      globalError.value =
        "You can't edit this organization anymore. Please log in again."
    } else {
      globalError.value =
        "An error occurred while saving, please try again later."
    }
    return false
  }

  return {
    form,
    logoPreview,
    iconPreview,
    saving,
    globalError,
    showInfrastructure,
    reset,
    setLogo,
    setIcon,
    fieldError,
    save,
  }
}
