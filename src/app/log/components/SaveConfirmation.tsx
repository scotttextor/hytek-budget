'use client'

import { useEffect } from 'react'

interface Props {
  visible: boolean
  offline: boolean
  onDismiss: () => void
}

export function SaveConfirmation({ visible, offline, onDismiss }: Props) {
  useEffect(() => {
    if (!visible) return
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      navigator.vibrate(50)
    }
    const t = setTimeout(onDismiss, 2000)
    return () => clearTimeout(t)
  }, [visible, onDismiss])

  return (
    <div
      aria-hidden={!visible}
      className={`fixed left-0 right-0 top-0 z-50 transform bg-green-600 py-3 text-center text-sm font-semibold text-white shadow-lg transition-transform duration-200 ${
        visible ? 'translate-y-0' : '-translate-y-full'
      }`}
    >
      {offline ? 'Logged — will sync when online' : 'Logged — syncing'}
    </div>
  )
}
