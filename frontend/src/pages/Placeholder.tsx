export default function Placeholder({ titulo }: { titulo: string }) {
  return (
    <div>
      <h2 className="text-xl font-semibold">{titulo}</h2>
      <p className="text-slate-500 mt-4">
        Esta sección aún no tiene interfaz. El backend ya la soporta; se irá
        construyendo por dominios.
      </p>
    </div>
  )
}
