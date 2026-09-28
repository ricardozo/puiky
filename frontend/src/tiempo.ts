// Utilidades del cronómetro compartidas por las vistas que inician/paran tiempo.

// Largo del pomodoro elegido en la pantalla Tiempo (preferencia del navegador).
export function pomoMin(): number {
  try {
    const v = Number(localStorage.getItem('puiky_pomodoro_min'))
    return v >= 5 && v <= 240 ? v : 45
  } catch {
    return 45
  }
}

const p2 = (n: number) => String(n).padStart(2, '0')

export function fmtCrono(seg: number): string {
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  const s = Math.floor(seg % 60)
  return h > 0 ? `${h}:${p2(m)}:${p2(s)}` : `${m}:${p2(s)}`
}
