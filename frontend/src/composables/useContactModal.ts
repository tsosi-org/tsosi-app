import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"


export function useContactModal() {
  const route = useRoute()
  const router = useRouter()
  const contactHash = "#contact"

  const openContactModal = () => {
    router.push({
      ...route,
      hash: contactHash,
    })
  }

  const closeContactModal = () => {
    // Going back would leave the site when it was opened on the modal URL:
    // vue-router stores the previous location of the app in `history.state`.
    if (window.history.state?.back) {
      router.back()
    } else {
      router.replace({ path: route.path, query: route.query, hash: "" })
    }
  }

  const isContactModalOpen = computed<boolean>({
    get: () => route.hash === contactHash,
    set: (isOpen) => {
      if (isOpen) {
        openContactModal()
      } else {
        closeContactModal()
      }
    },
  })

  return { isContactModalOpen, openContactModal, closeContactModal }
}
