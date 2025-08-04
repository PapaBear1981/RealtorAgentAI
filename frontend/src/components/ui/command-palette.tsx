"use client"

import * as React from "react"
import { Command } from "cmdk"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { getNavigationItems } from "@/components/layout/Navigation"
import { useAuthStore } from "@/stores/auth"

export function CommandPalette() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [open, setOpen] = React.useState(false)

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const items = getNavigationItems(user)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="p-0 overflow-hidden">
        <Command label="Command Palette">
          <Command.Input
            placeholder="Type a command or search..."
            className="h-11 w-full border-b px-4 outline-none"
          />
          <Command.List>
            <Command.Empty className="p-4 text-sm">No results found.</Command.Empty>
            <Command.Group heading="Navigation">
              {items.map((item) => (
                <Command.Item
                  key={item.href}
                  onSelect={() => {
                    setOpen(false)
                    router.push(item.href)
                  }}
                  className="cursor-pointer px-4 py-2 text-sm"
                >
                  {item.label}
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
