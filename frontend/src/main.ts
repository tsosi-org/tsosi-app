import "@/assets/css/main.css"

import { createApp } from "vue"
import PrimeVue from "primevue/config"
import Aura from "@primevue/themes/aura"
import { definePreset } from "@primevue/themes"
import DialogService from "primevue/dialogservice"
// @ts-expect-error No available types for vue-matomo
import VueMatomo from "vue-matomo"
import { library } from "@fortawesome/fontawesome-svg-core"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faLocationDot,
  faArrowUpRightFromSquare,
  faImage,
  faMagnifyingGlass,
  faSquareCheck,
  faSquareXmark,
  faDownload,
  faEllipsisVertical,
  faHouse,
  faBuildingColumns,
  faMagnifyingGlassChart,
  faAngleRight,
  faListUl,
  faChartColumn,
  faCircleQuestion,
  faBars,
  faXmark,
  faCheck,
  faCalendar,
  faGlobe,
  faLink,
  faEnvelope,
  faAt,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons"
import { faGithub } from "@fortawesome/free-brands-svg-icons"

import router from "@/router"
import App from "@/App.vue"


const app = createApp(App)

// Register PrimeVue library
const MyPreset = definePreset(Aura, {
  primitive: {
    brand: {
      50: "#e6eefa",
      100: "#c6d5e3",
      200: "#a7b8ca",
      300: "#879bb2",
      400: "#6f869f",
      500: "#57728d",
      600: "#4a647c",
      700: "#3a5066",
      800: "#2c3e50",
      900: "#1a2a39",
      950: "#1a2a39",
    },
  },
  semantic: {
    primary: {
      50: "{brand.50}",
      100: "{brand.100}",
      200: "{brand.200}",
      300: "{brand.300}",
      400: "{brand.400}",
      500: "{brand.500}",
      600: "{brand.600}",
      700: "{brand.700}",
      800: "{brand.800}",
      900: "{brand.900}",
      950: "{brand.950}",
    },
  },
  components: {
    tabs: {
      tab: {
        active: {
          color: "{primary.900}",
        },
      },
      tabpanel: {
        padding: "min(1.125rem, 5vh) min(0.875rem, 1vw)",
        color: "var(--p-neutral-950)",
      },
    },
    dialog: {
      color: "var(--p-neutral-950)",
    },
  },
})

app.use(PrimeVue, {
  theme: {
    preset: MyPreset,
    options: {
      darkModeSelector: false,
      // The cssLayer enables primevue styling to be applied aftef
      // our custom CSS.
      cssLayer: true,
    },
  },
})
app.use(DialogService)

// Registering used Font Awesome icons
const usedIcons = [
  faLocationDot,
  faArrowUpRightFromSquare,
  faImage,
  faMagnifyingGlass,
  faSquareCheck,
  faSquareXmark,
  faDownload,
  faEllipsisVertical,
  faHouse,
  faBuildingColumns,
  faMagnifyingGlassChart,
  faAngleRight,
  faListUl,
  faChartColumn,
  faCircleQuestion,
  faBars,
  faXmark,
  faCheck,
  faCalendar,
  faGlobe,
  faLink,
  faGithub,
  faEnvelope,
  faAt,
  faSpinner,
]
library.add(...usedIcons)
app.component("font-awesome-icon", FontAwesomeIcon)

app.use(router)

// Matomo plugin for Vue.js
const hasMatomoInfo =
  import.meta.env.VITE_MATOMO_HOST && import.meta.env.VITE_MATOMO_SITE_ID
if (hasMatomoInfo) {
  app.use(VueMatomo, {
    host: import.meta.env.VITE_MATOMO_HOST,
    siteId: import.meta.env.VITE_MATOMO_SITE_ID,
    router: router,
    // We need cookies to uniquely identify users
    disableCookies: false,
    preInitActions: [["trackPageView"], ["HeatmapSessionRecording::disable"]],
  })
}
app.mount("#app")

export const appContext = app._context
