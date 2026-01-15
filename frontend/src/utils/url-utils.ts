import type { Entity } from "@/singletons/ref-data"


export function getEntityBaseUrl(): string {
  return `/entities/`
}

export function getTransferBaseUrl(): string {
  return "/transfers/"
}

export function getEntityUrl(entity: Entity): string {
  const ror = entity.identifiers.find((id) => id.registry == "ror")
  if (ror) {
    return getEntityBaseUrl() + ror.value
  }
  const wikidata = entity.identifiers.find((id) => id.registry == "wikidata")
  if (wikidata) {
    return getEntityBaseUrl() + wikidata.value
  }
  const custom = entity.identifiers.find((id) => id.registry == "_custom")
  if (custom) {
    return getEntityBaseUrl() + custom.value
  }
  return getEntityBaseUrl() + entity.id
}

export function getRorUrl(ror_id: string): string {
  return `https://ror.org/${ror_id}`
}

export function getWikidataUrl(wikidata_id: string): string {
  return `https://wikidata.org/wiki/${wikidata_id}`
}

export function getStaticDataUrl(path: string): string {
  return `/static_data/${path}`
}
