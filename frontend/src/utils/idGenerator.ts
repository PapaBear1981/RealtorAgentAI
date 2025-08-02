// Utility for generating unique IDs to prevent React key collisions
let idCounter = 0

export const generateUniqueId = (prefix?: string): string => {
  idCounter += 1
  const timestamp = Date.now()
  const id = `${timestamp}-${idCounter}`
  return prefix ? `${prefix}_${id}` : id
}

// Reset counter (useful for testing)
export const resetIdCounter = (): void => {
  idCounter = 0
}
