/// <reference types="vite/client" />

interface ViteTypeOptions {
  // By adding this line, you can make the type of ImportMetaEnv strict
  // to disallow unknown keys.
  strictImportMetaEnv: unknown
}

interface ImportMetaEnv {
  readonly VITE_API_ROOT: string
  readonly VITE_CUSTOM_HTTP_HEADER?: string
  readonly VITE_CUSTOM_HTTP_HEADER_VALUE?: string
  readonly VITE_MATOMO_HOST?: string
  readonly VITE_MATOMO_SITE_ID?: string
  readonly VITE_WELCOME_POPUP?: "true"
  readonly VITE_INFRA_HISTOGRAM_OPT_OUT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
