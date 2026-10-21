import "@/assets/css/main.css";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faGithub, faLinkedin } from "@fortawesome/free-brands-svg-icons";
import {
  faAngleRight,
  faArrowLeft,
  faArrowRight,
  faArrowUpRightFromSquare,
  faAt,
  faBan,
  faBars,
  faBuildingColumns,
  faBullhorn,
  faCalendar,
  faChartColumn,
  faCheck,
  faChevronLeft,
  faCircleCheck,
  faCircleExclamation,
  faCircleInfo,
  faCircleQuestion,
  faClock,
  faClone,
  faDownload,
  faEllipsis,
  faEllipsisVertical,
  faEnvelope,
  faEquals,
  faEye,
  faEyeSlash,
  faGlobe,
  faHourglassHalf,
  faHouse,
  faImage,
  faLink,
  faListUl,
  faLocationDot,
  faLock,
  faMagnifyingGlass,
  faMagnifyingGlassChart,
  faNotEqual,
  faPaperPlane,
  faPen,
  faPlus,
  faRotateLeft,
  faScaleBalanced,
  faSpinner,
  faSquareCheck,
  faSquareXmark,
  faTrash,
  faTriangleExclamation,
  faUser,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { definePreset } from "@primevue/themes";
import Aura from "@primevue/themes/aura";
import PrimeVue from "primevue/config";
import DialogService from "primevue/dialogservice";
import Tooltip from 'primevue/tooltip';
import { createApp } from "vue";
// @ts-expect-error No available types for vue-matomo
import VueMatomo from "vue-matomo";

import App from "@/App.vue";
import router from "@/router";

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
    // Messages with a thin neutral frame, unlike the info boxes
    // (`.info-box`), whatever their severity: `MessageAtom` shows it with
    // an icon.
    message: {
      root: {
        borderRadius: "5px",
      },
      content: {
        padding: "min(1em, 3vw) min(1rem, 1vw)",
      },
      text: {
        fontWeight: "400",
      },
      colorScheme: {
        light: Object.fromEntries(
          ["info", "success", "warn", "error"].map((severity) => [
            severity,
            {
              // Opaque, for the messages floating over the page
              background: "var(--color-background)",
              borderColor: "{surface.200}",
              color: "{neutral.950}",
              shadow: "none",
              closeButton: {
                hoverBackground: "{surface.100}",
                focusRing: { color: "{primary.color}" },
              },
            },
          ]),
        ),
      },
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
  faAngleRight,
  faArrowRight,
  faArrowUpRightFromSquare,
  faAt,
  faBan,
  faBars,
  faBuildingColumns,
  faCalendar,
  faChartColumn,
  faCheck,
  faChevronLeft,
  faUser,
  faClock,
  faCircleQuestion,
  faCircleInfo,
  faCircleCheck,
  faCircleExclamation,
  faTriangleExclamation,
  faDownload,
  faEllipsisVertical,
  faEllipsis,
  faEnvelope,
  faEye,
  faEyeSlash,
  faGithub,
  faLinkedin,
  faBullhorn,
  faGlobe,
  faHourglassHalf,
  faHouse,
  faImage,
  faLink,
  faListUl,
  faLocationDot,
  faMagnifyingGlass,
  faMagnifyingGlassChart,
  faPen,
  faPlus,
  faRotateLeft,
  faScaleBalanced,
  faSpinner,
  faSquareCheck,
  faSquareXmark,
  faTrash,
  faXmark,
  faArrowLeft,
  faClone,
  faLock,
  faPaperPlane,
  faEquals,
  faNotEqual,
]
library.add(...usedIcons)
app.component("font-awesome-icon", FontAwesomeIcon)

app.use(router)

app.directive("tooltip", Tooltip)

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
