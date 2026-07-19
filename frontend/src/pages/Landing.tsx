// Portada pública (pre-login): explica qué es Puiky a quien entra sin sesión.
import Concepto from './Concepto'

export default function Landing({ onEntrar }: { onEntrar: () => void }) {
  return (
    <div className="min-h-screen bg-ground text-ink">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-line bg-surface-2/85 backdrop-blur px-4 sm:px-8 py-3">
        <div className="flex items-center gap-2.5">
          <img
            src="/logo-simbolo.png"
            alt="Puiky"
            className="size-8 rounded-lg object-cover"
          />
          <span className="font-serif text-lg">Puiky</span>
        </div>
        <button onClick={onEntrar} className="btn text-sm py-2">
          Iniciar sesión
        </button>
      </header>

      <main className="px-4 sm:px-8 py-8 sm:py-12">
        <div className="mx-auto max-w-3xl">
          <Concepto />

          <div className="mt-12 flex flex-col items-center gap-3 border-t border-line pt-10 text-center">
            <p className="text-muted">¿Ya tienes acceso?</p>
            <button onClick={onEntrar} className="btn px-6 py-2.5">
              Iniciar sesión
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
