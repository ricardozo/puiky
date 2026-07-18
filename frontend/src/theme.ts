import { useState } from 'react'

type Theme = 'light' | 'dark'

function actual(): Theme {
  const guardado = localStorage.getItem('puiky_theme')
  if (guardado === 'light' || guardado === 'dark') return guardado
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(actual())
  const aplicar = (t: Theme) => {
    document.documentElement.setAttribute('data-theme', t)
    localStorage.setItem('puiky_theme', t)
    setTheme(t)
  }
  return { theme, toggle: () => aplicar(theme === 'dark' ? 'light' : 'dark') }
}
