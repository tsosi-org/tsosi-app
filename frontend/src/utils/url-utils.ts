export function getEntityBaseUrl(): string {
  return `/entities/`
}

export function getTransferBaseUrl(): string {
  return "/transfers/"
}

export function getEntityUrl(entity_id: string): string {
  return getEntityBaseUrl() + entity_id
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
