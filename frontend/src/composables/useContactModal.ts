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
    router.back()
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
