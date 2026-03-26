import { useEffect, useState } from 'react'

/**
 * Staggered entrance helper.
 * Returns array of booleans visible[i].
 * Each index becomes true after (i * delayMs) ms on mount.
 * Cleans up all timeouts on unmount.
 */
export default function useAnimatedMount(count, delayMs = 80) {
  const [visible, setVisible] = useState(() => Array(count).fill(false))

  useEffect(() => {
    const ids = []

    for (let i = 0; i < count; i++) {
      const id = setTimeout(() => {
        setVisible(prev => {
          const next = [...prev]
          next[i] = true
          return next
        })
      }, i * delayMs)
      ids.push(id)
    }

    return () => {
      ids.forEach(id => clearTimeout(id))
    }
  }, [count, delayMs])

  return visible
}
