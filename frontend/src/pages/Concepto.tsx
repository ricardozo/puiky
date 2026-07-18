// Página que explica qué es Puiky: origen del nombre, filosofía y qué hace cada sección.

const SECCIONES = [
  {
    icon: '📝',
    titulo: 'Notas',
    texto:
      'Todo lo que no quieres olvidar. Escribes en lenguaje natural y Puiky las guarda en cuadernos. La búsqueda es semántica: encuentras por significado, no solo por palabras exactas.',
  },
  {
    icon: '📋',
    titulo: 'Proyectos',
    texto:
      'Portafolios, proyectos y un tablero Kanban para mover tareas por estado. Cada proyecto puede tener sus hojas y su checklist de avance.',
  },
  {
    icon: '✅',
    titulo: 'Tareas',
    texto:
      'Lo que tienes que hacer, ordenado por fecha de vencimiento y con el proyecto al que pertenece. Buscas, marcas avance y completas.',
  },
  {
    icon: '💰',
    titulo: 'Finanzas',
    texto:
      'Cuentas, movimientos y presupuestos. Registras gastos e ingresos por voz o texto, y ves el resultado por cuenta y por categoría en el rango de fechas que quieras.',
  },
  {
    icon: '🔁',
    titulo: 'Responsabilidades',
    texto:
      'Compromisos que se repiten —el arriendo, un pago, una llamada— con su próxima fecha. Puiky te avisa antes de que venzan.',
  },
  {
    icon: '⏰',
    titulo: 'Recordatorios',
    texto:
      'Avisos puntuales. El programador insiste hasta que los resuelves o los pospones, para que nada se pierda.',
  },
]

export default function Concepto() {
  return (
    <div className="max-w-3xl space-y-10">
      <header className="space-y-4">
        <img
          src="/logo-simbolo.png"
          alt="Puiky"
          className="size-16 rounded-2xl object-cover shadow-[var(--shadow)]"
        />
        <div>
          <p className="eyebrow">pquyquy · muisca</p>
          <h1 className="font-serif text-4xl mt-2 tracking-tight">
            Puiky, tu segundo cerebro
          </h1>
        </div>
        <p className="text-lg text-muted leading-relaxed">
          En muisca, <span className="text-brand">pquyquy</span> nombra a la vez el
          corazón, la mente y la memoria: el lugar donde se piensa y se recuerda.
          Puiky es eso — un lugar donde dejas lo que piensas, lo que debes y lo que
          quieres recordar, y que te lo devuelve cuando lo necesitas.
        </p>
      </header>

      <section className="space-y-4">
        <h2 className="eyebrow">La idea</h2>
        <div className="card p-6 space-y-3 text-muted leading-relaxed">
          <p>
            No es una app que llenas con formularios. Le hablas —por la web o por
            Telegram, escribiendo o por voz— en tus propias palabras, y Puiky entiende
            qué quieres y lo hace: crea una nota, registra un gasto, agenda un
            recordatorio, mueve una tarea.
          </p>
          <p>
            Recuerda el hilo de la conversación, resuelve a qué te refieres sin que
            tengas que repetir nombres exactos, y siempre te pide confirmación antes
            de borrar algo. Es tuyo y solo tuyo: tu información no se cruza con la de
            nadie más.
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="eyebrow">Qué guarda</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {SECCIONES.map((s) => (
            <div key={s.titulo} className="card p-5">
              <div className="text-2xl">{s.icon}</div>
              <h3 className="font-serif text-xl mt-2">{s.titulo}</h3>
              <p className="text-sm text-muted mt-1.5 leading-relaxed">{s.texto}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="eyebrow">Cómo se usa</h2>
        <div className="card p-6 space-y-3 text-muted leading-relaxed">
          <p>
            <span className="text-ink font-medium">Por Telegram</span> — para el día a
            día: «gasté 20 mil en comida», «recuérdame llamar al banco mañana a las 3»,
            un audio contando cómo te fue. Puiky responde y confirma.
          </p>
          <p>
            <span className="text-ink font-medium">Por la web</span> — para ver el
            panorama: revisar tus cuentas, mover tareas en el tablero, leer tus notas,
            filtrar tus finanzas por fecha.
          </p>
        </div>
      </section>

      <footer className="text-sm text-faint pt-2">
        Inspirado en la Laguna de Guatavita.
      </footer>
    </div>
  )
}
