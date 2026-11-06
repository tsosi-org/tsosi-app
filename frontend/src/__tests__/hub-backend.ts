/**
 * A fake backend of an organization's Hub (`ORG`) for the component tests,
 * over `mockApi`: the member logged in, the organization's supports table,
 * its declarations, saved, changed and deleted in memory, its
 * submissions and the preview of their publication. Its URLs take its UUID
 * or its TSOSI ID. A failure can be set for a method and route (with the
 * UUID), and a change made before a request is answered, e.g. by another
 * member.
 */
import { mockApi, type MockRequest, type MockResponse } from "./api-mock"
import { ENTITIES, ORG, apiDate, declaration, entity } from "./hub-fixtures"

import {
  DATE_FIELDS,
  type Declaration,
  type DeclarationPayload,
  type Submission,
} from "@/singletons/hub-declarations"
import type { Member } from "@/singletons/hub-session"
import type { HubTransfer, PreviewTransfer } from "@/singletons/ref-data"

export interface HubBackend {
  // The user logged in, a member of the organization by default
  member: Member | null
  transfers: HubTransfer[]
  declarations: Declaration[]
  // The pairs of rows that may be the same support, before reconciliation
  duplicates: [string, string][]
  submissions: Submission[]
  preview: {
    transfers: PreviewTransfer[]
    changes: Record<string, string[]>
  }
  // By `<method> <route>`, e.g. `DELETE hub/entities/org/declarations/1`
  failures: Record<string, MockResponse>
  // Called before each request is answered
  beforeRequest: ((request: MockRequest) => void) | null
  requests: MockRequest[]
}

const BASE = `hub/entities/${ORG.id}`
export const DECLARATIONS_ROUTE = `${BASE}/declarations`
// The organization's routes, by its UUID or its TSOSI ID: the rest
const ORG_ROUTE = /^hub\/entities\/(?:org|T123456)(?:\/(.*))?$/

export const MEMBER: Member = {
  email: "member@uni.edu",
  is_staff: false,
  organization: { id: ORG.id, tsosi_id: "T123456", name: ORG.name },
  can_declare_supports: true,
}

// The declaration saved from a payload: its dates typed become dates
function saved(payload: DeclarationPayload, id: number): Declaration {
  const dates = Object.fromEntries(
    DATE_FIELDS.map((f) => [f, payload[f] ? apiDate(payload[f]!) : null]),
  )
  return declaration({
    ...payload,
    ...dates,
    id,
    recipient_id: payload.recipient_id ?? null,
    agent_ids: payload.agent_ids ?? [],
    other_transfer_ids: payload.other_transfer_ids ?? [],
    other_declaration_ids: payload.other_declaration_ids ?? [],
    amount: payload.amount ?? null,
    currency: payload.currency ?? null,
  } as Partial<Declaration>)
}

// The drafts, to submit: their IDs and a hash of their values, as the
// backend's (a deterministic string here)
function drafts(backend: HubBackend): Declaration[] {
  return backend.declarations
    .filter((d) => d.status == "draft")
    .sort((a, b) => a.id - b.id)
}

export function draftsHash(declarations: Declaration[]): string {
  return JSON.stringify(declarations)
}

// The possible duplicates still to reconcile: of the rows still in the
// table, and not reconciled by a pending declaration
function possibleDuplicates(backend: HubBackend): [string, string][] {
  const rows = new Set([
    ...backend.transfers.map((t) => t.id),
    ...backend.declarations
      .filter((d) => d.kind == "new")
      .map((d) => `new-${d.id}`),
  ])
  const reconciled = backend.declarations
    .filter((d) => ["merge", "not_duplicate", "new"].includes(d.kind))
    .map((d) => [
      d.transfer_id ?? `new-${d.id}`,
      ...d.other_transfer_ids,
      ...d.other_declaration_ids.map((id) => `new-${id}`),
    ])
  return backend.duplicates.filter(
    ([left, right]) =>
      rows.has(left) &&
      rows.has(right) &&
      !reconciled.some((ids) => ids.includes(left) && ids.includes(right)),
  )
}

export function hubBackend(data: Partial<HubBackend> = {}): HubBackend {
  const backend: HubBackend = {
    member: MEMBER,
    transfers: [],
    declarations: [],
    duplicates: [],
    submissions: [],
    preview: { transfers: [], changes: {} },
    failures: {},
    beforeRequest: null,
    requests: [],
    ...data,
  }
  let nextId = 100

  function declarations(request: MockRequest, id?: number): MockResponse {
    if (request.method == "GET") {
      return {
        body: {
          declarations: backend.declarations,
          entities: ENTITIES,
          possible_duplicates: possibleDuplicates(backend),
        },
      }
    }
    if (request.method == "POST") {
      const result = saved(request.body as DeclarationPayload, nextId++)
      backend.declarations.push(result)
      return { status: 201, body: result }
    }
    const index = backend.declarations.findIndex((d) => d.id == id)
    if (index < 0) {
      return { status: 404, body: { detail: "Not found." } }
    }
    if (request.method == "DELETE") {
      backend.declarations.splice(index, 1)
      return { status: 204 }
    }
    const result = saved(request.body as DeclarationPayload, id!)
    backend.declarations[index] = result
    return { body: result }
  }

  function submit(request: MockRequest): MockResponse {
    const current = drafts(backend)
    const body = request.body as {
      declaration_ids: number[]
      declarations_hash: string
    }
    const ids = [...body.declaration_ids].sort((a, b) => a - b)
    if (
      current.map((d) => d.id).join() != ids.join() ||
      draftsHash(current) != body.declarations_hash
    ) {
      return {
        status: 400,
        body: { detail: "The changes changed since the preview." },
      }
    }
    current.forEach((d) => (d.status = "submitted"))
    const result: Submission = {
      id: backend.submissions.length + 1,
      status: "submitted",
      consent_at: "2026-10-20T10:00:00Z",
      submitted_by: backend.member?.email ?? null,
      changes_count: current.length,
    }
    backend.submissions.push(result)
    return { status: 201, body: result }
  }

  backend.requests = mockApi({
    "*": (request) => {
      backend.beforeRequest?.(request)
      const match = ORG_ROUTE.exec(request.route)
      const route = match?.[1] ?? ""
      const normalized = match ? `${BASE}${route ? `/${route}` : ""}` : null
      const failure =
        backend.failures[`${request.method} ${normalized ?? request.route}`]
      if (failure) {
        return failure
      }
      if (request.route == "hub/me") {
        return backend.member
          ? { body: backend.member }
          : { status: 403, body: {} }
      }
      if (request.route == "hub/organizations") {
        const query = request.params.get("search")!.toLowerCase()
        const results = Object.values(ENTITIES).filter((e) =>
          [e.name, e.short_name].some((n) => n?.toLowerCase().includes(query)),
        )
        return { body: { results, lookup: null } }
      }
      if (!match) {
        return { status: 404, body: {} }
      }
      if (route.startsWith("declarations")) {
        const id = route.split("/")[1]
        return declarations(request, id ? Number(id) : undefined)
      }
      switch (route) {
        case "":
          return { body: { ...ORG, preview_reason: null } }
        case "transfers":
          return {
            body: { transfers: backend.transfers, entities: ENTITIES },
          }
        case "submissions":
          return request.method == "GET"
            ? { body: backend.submissions }
            : submit(request)
        case "publication-preview":
          return {
            body: {
              ...backend.preview,
              entities: ENTITIES,
              declaration_ids: drafts(backend).map((d) => d.id),
              declarations_hash: draftsHash(drafts(backend)),
            },
          }
        case "organizations": {
          const name = (request.body as { name: string }).name
          return {
            status: 201,
            body: entity({
              id: name.toLowerCase().replace(/\s+/g, "-"),
              name,
              is_new: true,
              is_public: false,
            }),
          }
        }
      }
      return { status: 404, body: {} }
    },
  })
  return backend
}

// The requests that changed the organization's data, as `<method> <route>`
export function changes(backend: HubBackend): string[] {
  return backend.requests
    .filter((r) => r.method != "GET" && ORG_ROUTE.test(r.route))
    .map((r) => `${r.method} ${ORG_ROUTE.exec(r.route)![1]}`)
}
