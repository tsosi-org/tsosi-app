import { getCountry, type Transfer } from "@/singletons/ref-data"
import { getStaticDataUrl } from "@/utils/url-utils"
import type { DeepReadonly } from "vue"

export const nullValues = [null, undefined]

export type DataType =
  | "date"
  | "dateWithPrecision"
  | "string"
  | "number"
  | "pageLink"
  | "entityLink"
  | "externalLink"
  | "country"
  | "constant"
  | "json"
  | "boolean"

export interface LinkConfig {
  base: string
  suffix: string
  suffixType: "field" | "string"
}

export interface DataFieldProps {
  id: string
  title: string
  field: string
  type: DataType
  fieldLabel?: string
  fieldLink?: LinkConfig
  labelGetter?: (data: Record<string, any>) => any
  info?: string
}

/**
 * Get the given object's value at the given path.
 * Return undefined if any property in the path is undefined.
 * @param item
 * @param path  The path to resolve, as properties name separated by a dot `.`
 *              Ex: `emitter.country`
 * @returns
 */
export function resolveValueFromPath(
  item: Record<string, any>,
  path: string,
): any {
  const paths = path.split(".")
  let current = item
  for (path of paths) {
    if (!nullValues.includes(current[path])) {
      current = current[path]
    } else {
      return undefined
    }
  }
  return current
}

/**
 * Returns an the item label of the corresponding field.
 * @param item
 * @param fieldProps
 * @returns
 */
export function getItemLabel(
  item: Record<string, any>,
  fieldProps: DataFieldProps,
): any {
  if (fieldProps.labelGetter) {
    return fieldProps.labelGetter(item)
  }
  if (fieldProps.fieldLabel) {
    return resolveValueFromPath(item, fieldProps.fieldLabel)
  } else if (fieldProps.type == "constant") {
    return fieldProps.field
  }
  return resolveValueFromPath(item, fieldProps.field)
}

export function getItemValue(
  item: Record<string, any>,
  fieldProps: DataFieldProps,
): any {
  return resolveValueFromPath(item, fieldProps.field)
}

export function getCountryIcon(countryCode: string): string {
  const iconPath = getCountry(countryCode).flag_4x3
  return getStaticDataUrl(iconPath)
}

export function getCountryLabel(countryCode: string): string {
  return getCountry(countryCode).name
}

export function getCountryRegion(countryCode: string): string {
  return getCountry(countryCode).continent
}

export function getCountryCoordinates(
  countryCode: string,
): DeepReadonly<[number, number]> | null {
  return getCountry(countryCode).coordinates
}

type FormatTarget = "html" | "csv" | "json"

/**
 * Format the given value according to the given `DataType`.
 * The formatting depends on the given format.
 * @param value   The value to be formatted
 * @param type    The `DataType` the value should be interpreted as
 * @param target  The formatting target: `html`, `csv` or `json`.
 * @returns
 */
export function formatValue(
  value: any,
  type: DataType,
  target: FormatTarget = "html",
): string | number | null {
  if (nullValues.includes(value)) {
    return target == "json" ? null : ""
  }
  switch (type) {
    case "dateWithPrecision":
      return formatDateWithPrecisionObj(value as DateWithPrecision) || ""
    case "date":
      return formatDateWithPrecision(value as string | Date, "day") || ""
    case "number":
      if (target == "json") {
        return value
      }
      if (target == "csv") {
        return value.toString()
      }
      return (value as number).toLocaleString("fr-FR")
    case "country":
      return getCountryLabel(value)
    default:
      return value
  }
}

/**
 * Return an item field value's link based on the
 * @param item
 * @param columnProps
 * @returns
 */
export function getItemLink(
  item?: Record<string, any>,
  linkConfig?: LinkConfig,
): string {
  if (linkConfig == null || item == null) {
    return ""
  }
  const url = linkConfig.base
  if (linkConfig.suffixType == "string") {
    return url + linkConfig.suffix
  }
  const value = resolveValueFromPath(item, linkConfig.suffix)
  if (value == null) {
    return ""
  }
  return url + value
}

export type DatePrecision = "day" | "month" | "year"

export interface DateWithPrecision {
  value: string
  precision: DatePrecision
  dateObj?: Date
  dateFormatted?: string
}

export function initDateWithPrecision(date?: DateWithPrecision | null) {
  if (!date || date.dateObj) {
    return
  }
  date.dateObj = new Date(date.value)
}

export function initDateProperty(obj: Record<string, any>, property: string) {
  const value = obj[property]
  if (value && typeof value == "string") {
    obj[property] = new Date(value)
  }
}

/**
 * Format a `DateWithPrecision` object for display.
 * @param date  The `DateWithPrecision` object.
 * @returns
 */
export function formatDateWithPrecisionObj(
  date?: DateWithPrecision,
): string | null {
  if (!date) {
    return null
  } else if (date.dateFormatted) {
    return date.dateFormatted
  }
  const dateFormatted = formatDateWithPrecision(date.dateObj!, date.precision)
  if (dateFormatted != null) {
    date.dateFormatted = dateFormatted
  }
  return dateFormatted
}

/**
 * Format a date with the given precision.
 * @param date        The date, as a string or a `Date`
 * @param precision   The desired `DatePrecision`
 * @returns
 */
export function formatDateWithPrecision(
  date: string | Date,
  precision: DatePrecision,
): string | null {
  if (!date) {
    return null
  }
  let dateObj = date
  if (!(date instanceof Date)) {
    dateObj = new Date(date)
  }
  let dateFormatted = ""
  switch (precision) {
    case "day":
      dateFormatted = dateObj!.toLocaleString("default", { day: "2-digit" })
    case "month":
      const month = dateObj!.toLocaleString("default", { month: "2-digit" })
      dateFormatted = dateFormatted ? `${month}-${dateFormatted}` : month
    default:
      const year = dateObj!.toLocaleString("default", { year: "numeric" })
      dateFormatted = dateFormatted ? `${year}-${dateFormatted}` : year
  }
  return dateFormatted
}

/**
 * Fill the given transfer's amount & currency properties with the
 * desired currency.
 * It fallbacks to the original currency if the given currency is unavailable
 * for this transfer.
 * @param transfer
 * @param currencyCode
 * @param amountPropName
 * @param currencyPropName
 * @returns
 */
export function fillTransferAmountCurrency(
  transfer: Transfer,
  currencyCode: string,
  amountPropName: string,
  currencyPropName: string,
) {
  if (transfer.amounts_clc?.hasOwnProperty(currencyCode)) {
    transfer[currencyPropName] = currencyCode
    transfer[amountPropName] = transfer.amounts_clc[currencyCode]
    return
  }
  transfer[currencyPropName] = transfer.currency
  transfer[amountPropName] = transfer.amount
}

export function formatItemLabel(
  item: Record<string, any>,
  columnProps: DataFieldProps,
  target: FormatTarget = "html",
): string | number | null {
  const itemValue = getItemLabel(item, columnProps)
  return formatValue(itemValue, columnProps.type, target)
}

/**
 * Download the given data as a file.
 *
 * @param data      The encoded data as a string
 * @param type      The file MIME type
 * @param fileName  The full file name
 */
function downloadFile(data: BlobPart, type: string, fileName: string) {
  const blob = new Blob([data], { type: type })

  const link = document.createElement("a")
  const url = URL.createObjectURL(blob)
  link.href = url
  link.download = fileName

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Escape double quotes and escape the whole output value.
 * @param value
 * @returns
 */
function cleanCSVValue(value: string | number): string {
  let baseValue: string = ""
  if (typeof value === "number") {
    baseValue = value.toString()
  } else {
    baseValue = value
  }
  return `"${baseValue.replace(/"/g, '""')}"`
}

/**
 * Export and download the given data as a CSV file.
 * @param fields    The data fields to include
 * @param data      The data items
 * @param fileName  The exported file name, without extension.
 */
export async function exportCSV(
  fields: DataFieldProps[],
  data: Record<string, any>[],
  fileName: string,
) {
  const processRow = (row: Record<string, any>) => {
    const values = fields.map((field) => {
      const value = formatItemLabel(row, field, "csv") as string
      return cleanCSVValue(value)
    })
    return values.join(",")
  }

  let csvRows = fields.map((field) => cleanCSVValue(field.title)).join(",")

  data.forEach((item) => {
    csvRows += "\n"
    csvRows += processRow(item)
  })
  downloadFile(csvRows, "text/csv;charset=utf-8;", `${fileName}.csv`)
}

/**
 * Export and download the given data as a JSON file.
 * @param fields    The data fields to include
 * @param data      The data items
 * @param fileName  The exported file name, without extension
 */
export async function exportJSON(
  fields: DataFieldProps[],
  data: Record<string, any>[],
  fileName: string,
) {
  const fieldsMapping: Map<string, string> = new Map()
  fields.forEach((field) =>
    fieldsMapping.set(field.id, field.title.toLowerCase().replace(/\s+/g, "_")),
  )
  const processRow = (row: Record<string, any>) => {
    const values: { [key: string]: string | number | null } = {}
    fields.forEach((field) => {
      const value = formatItemLabel(row, field, "json")
      values[fieldsMapping.get(field.id) as string] = value
    })
    return values
  }

  const processedData = JSON.stringify(data.map(processRow), null, 2)
  downloadFile(processedData, "application/json", `${fileName}.json`)
}

export function exportPNG(base64Data: string, fileName: string) {
  const link = document.createElement("a")
  link.href = base64Data
  link.download = `${fileName}.png`
  link.click()
}

export interface PointCoordinates {
  lat: number
  lon: number
}

/**
 * Parse the given WKT coordinates.
 * @param wktCoordinates the WKT coordinates string, as POINT(latitude longitude)
 * @returns
 */
export function parsePointCoordinates(
  wktCoordinates: string | null | undefined,
): PointCoordinates | null {
  if (!wktCoordinates) {
    return null
  }
  const parsedCoordinates = /[a-zA-Z]+\(([-\d\.]+)\s+([-\d\.]+)\)/g.exec(
    wktCoordinates,
  )
  if (parsedCoordinates?.length != 3) {
    return null
  }
  return {
    lat: parseFloat(parsedCoordinates[2]),
    lon: parseFloat(parsedCoordinates[1]),
  }
}

export function shuffleArray(data: any[]) {
  let currentIndex = data.length

  // While there remain elements to shuffle...
  while (currentIndex != 0) {
    // Pick a remaining element...
    const randomIndex = Math.floor(Math.random() * currentIndex)
    currentIndex--

    // And swap it with the current element.
    ;[data[currentIndex], data[randomIndex]] = [
      data[randomIndex],
      data[currentIndex],
    ]
  }
}
