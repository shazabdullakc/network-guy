import { useEffect, useRef, useState } from 'react'

/**
 * Wraps IntersectionObserver.
 * Returns boolean isVisible.
 * Fires once — unobserves after first intersection.
 */
export default function useIntersection(ref, options = {}) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.unobserve(el)
        }
      },
      {
        threshold: 0.15,
        rootMargin: '0px 0px -40px 0px',
        ...options,
      }
    )

    observer.observe(el)

    return () => {
      observer.disconnect()
    }
  }, [ref, options])

  return isVisible
}
