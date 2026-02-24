import { ref } from "vue"

const isContactModalOpen = ref(false)

export function useContactModal() {
  const openContactModal = () => (
    console.log("Opening contact modal"),
    isContactModalOpen.value = true
  )
  const closeContactModal = () => (
    console.log("Closing contact modal"),
    isContactModalOpen.value = false
  )
  return { isContactModalOpen, openContactModal, closeContactModal }
}
