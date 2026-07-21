"""Siembra datos de demostración en un inquilino (para capturas / video).

Uso:
    python -m app.seed_demo <slug>            # siembra (se niega si ya hay datos)
    python -m app.seed_demo <slug> --reset    # borra los datos del inquilino y resiembra

Rellena finanzas (varios meses), notas, proyectos/Kanban, tareas (con recurrentes),
recordatorios (con recurrentes), responsabilidades, mercado y notas ligadas a un
proyecto (para el cuaderno de proyecto). Pensado para grabar el video demo.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.finances import Account, Budget, Category, Transaction
from app.models.market import MarketProduct, MarketPurchase
from app.models.notebooks import Notebook
from app.models.notes import Note, NoteLink
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import ChecklistItem, Task
from app.provision import slug_a_schema
from app.timeutils import now_local

_EMB = [0.001] * 768  # vector de relleno (la búsqueda semántica no aplica al demo)

# Tablas de dominio a vaciar con --reset (CASCADE resuelve las FKs).
_TABLAS = (
    "trip_item, shopping_trip, market_purchase, market_product, "
    "note_link, note, notebook, checklist_item, task, project, portfolio, "
    "transaction, budget, reminder, responsibility, category, account"
)


def sembrar(db: Session) -> None:
    hoy = date.today()
    ahora = now_local()

    cats: dict[str, Category] = {}
    for n in ["Comida", "Transporte", "Servicios", "Salud", "Ocio", "Mercado",
              "Salario", "Educación", "Suscripciones", "Otros"]:
        c = Category(nombre=n, activa=True)
        db.add(c)
        cats[n] = c

    accs: dict[str, Account] = {}
    for n, tipo, saldo in [
        ("Bancolombia", "banco", 3850000),
        ("Nequi", "digital", 420000),
        ("Efectivo", "efectivo", 180000),
        ("Ahorros", "ahorros", 6200000),
    ]:
        a = Account(nombre=n, tipo=tipo, saldo=Decimal(saldo))
        db.add(a)
        accs[n] = a
    db.flush()

    def tx(tipo, monto, acc, cat=None, dest=None, nota=None, dias=0):
        db.add(Transaction(
            tipo=tipo, monto=Decimal(monto), account_id=accs[acc].id,
            category_id=cats[cat].id if cat else None,
            cuenta_destino_id=accs[dest].id if dest else None,
            fecha=hoy - timedelta(days=dias), nota=nota,
        ))

    # Mes actual
    tx("gasto", 45000, "Efectivo", "Comida", nota="mercado del sábado", dias=2)
    tx("gasto", 10000, "Nequi", "Comida", nota="pan y café", dias=1)
    tx("gasto", 18000, "Nequi", "Transporte", nota="taxi", dias=3)
    tx("gasto", 62000, "Bancolombia", "Servicios", nota="recibo de luz", dias=4)
    tx("gasto", 35000, "Bancolombia", "Ocio", nota="cine", dias=5)
    tx("gasto", 40000, "Efectivo", "Salud", nota="farmacia", dias=6)
    tx("gasto", 44900, "Bancolombia", "Suscripciones", nota="Netflix", dias=6)
    tx("ingreso", 2500000, "Bancolombia", "Salario", nota="quincena", dias=7)
    tx("transferencia", 500000, "Bancolombia", dest="Ahorros", nota="ahorro del mes", dias=8)
    # Mes pasado (para la navegación ◀ por mes)
    tx("gasto", 520000, "Bancolombia", "Mercado", nota="mercado del mes", dias=35)
    tx("gasto", 190000, "Bancolombia", "Comida", nota="restaurantes", dias=38)
    tx("gasto", 120000, "Bancolombia", "Servicios", nota="internet", dias=40)
    tx("gasto", 95000, "Nequi", "Transporte", nota="gasolina", dias=42)
    tx("gasto", 60000, "Bancolombia", "Ocio", nota="salida", dias=44)
    tx("ingreso", 2500000, "Bancolombia", "Salario", nota="quincena", dias=37)
    # Hace dos meses
    tx("gasto", 480000, "Bancolombia", "Mercado", nota="mercado del mes", dias=66)
    tx("gasto", 150000, "Bancolombia", "Salud", nota="médico", dias=70)
    tx("gasto", 200000, "Bancolombia", "Educación", nota="curso", dias=72)

    db.add(Budget(category_id=cats["Comida"].id, tope=Decimal(300000), periodo="mensual"))
    db.add(Budget(category_id=cats["Mercado"].id, tope=Decimal(600000), periodo="mensual"))
    db.add(Budget(category_id=cats["Ocio"].id, tope=Decimal(150000), periodo="mensual"))

    # --- Notas sueltas ---
    nb: dict[str, Notebook] = {}
    for n in ["Personal", "Trabajo"]:
        x = Notebook(nombre=n)
        db.add(x)
        nb[n] = x
    db.flush()
    for cuad, tit, cont in [
        ("Personal", "Ideas de regalo para mamá", "Un perfume, un libro de jardinería, o una cena sorpresa el domingo."),
        ("Personal", "Libros por leer", "El infinito en un junco\nHábitos atómicos\nSapiens\nEl poder del ahora"),
        ("Trabajo", "Puntos para la reunión del lunes", "Revisar el avance del proyecto.\nDefinir el presupuesto del trimestre.\nAsignar responsables."),
        ("Trabajo", "Contactos clave", "Proveedor cocina — 300 123 4567\nContador — 310 765 4321"),
    ]:
        db.add(Note(notebook_id=nb[cuad].id, titulo=tit, contenido=cont, embedding=_EMB))

    # --- Portafolios y proyectos ---
    pf_casa = Portfolio(nombre="Casa")
    pf_clientes = Portfolio(nombre="Clientes")
    db.add_all([pf_casa, pf_clientes])
    db.flush()

    proj_cocina = Project(
        nombre="Remodelación de la cocina", portfolio_id=pf_casa.id, estado="activo",
        fecha_inicio=hoy - timedelta(days=20), fecha_fin=hoy + timedelta(days=40),
        descripcion="Renovar la cocina: mesón, pintura y electrodomésticos.",
    )
    proj_colef = Project(
        nombre="Portal COLEF", portfolio_id=pf_clientes.id, estado="activo",
        fecha_inicio=hoy - timedelta(days=60), fecha_fin=hoy + timedelta(days=120),
        descripcion="Portal de convocatorias del cliente COLEF.",
    )
    db.add_all([proj_cocina, proj_colef])
    db.flush()

    def tarea(proj, titulo, estado, dias=None, avance=0, desc=None, recurrencia=None):
        t = Task(
            project_id=proj.id, titulo=titulo, estado=estado, avance_pct=avance,
            fecha_limite=(hoy + timedelta(days=dias)) if dias is not None else None,
            descripcion=desc, recurrencia=recurrencia,
        )
        db.add(t)
        return t

    tarea(proj_cocina, "Medir el espacio", "terminada", avance=100)
    tarea(proj_cocina, "Cotizar el mesón", "planeada", dias=2)
    tarea(proj_cocina, "Elegir color de pintura", "planeada", dias=6)
    t_ej = tarea(proj_cocina, "Comprar electrodomésticos", "en_ejecucion", dias=1, avance=40, desc="Nevera, estufa y campana.")
    tarea(proj_cocina, "Instalar la iluminación", "en_pausa", dias=12)

    tarea(proj_colef, "Abrir convocatoria 5", "planeada", dias=10)
    tarea(proj_colef, "Cerrar convocatoria 4", "en_ejecucion", dias=3, avance=30)
    tarea(proj_colef, "Cuenta de cobro COLEF", "en_ejecucion", dias=5, recurrencia="mensual",
          desc="Pasar la cuenta de cobro del mes.")
    tarea(proj_colef, "Enviar informe mensual", "planeada", dias=8, recurrencia="mensual")
    db.flush()

    for i, (txt, hecho) in enumerate(
        [("Nevera", True), ("Estufa", True), ("Campana", False), ("Microondas", False), ("Licuadora", False)]
    ):
        db.add(ChecklistItem(task_id=t_ej.id, texto=txt, hecho=hecho, orden=i))

    # --- Nota ligada a un proyecto (crea el cuaderno de proyecto) ---
    nb_colef = Notebook(nombre="Portal COLEF")
    db.add(nb_colef)
    db.flush()
    n_colef = Note(
        notebook_id=nb_colef.id, titulo="Requisitos de la convocatoria",
        contenido="Fechas, formato del informe y datos para la cuenta de cobro.",
        embedding=_EMB,
    )
    db.add(n_colef)
    db.flush()
    db.add(NoteLink(note_id=n_colef.id, entidad_tipo="project", entidad_id=proj_colef.id))

    # --- Recordatorios (uno recurrente) ---
    db.add(Reminder(texto="Pagar la tarjeta de crédito", disparar_en=ahora + timedelta(days=1)))
    db.add(Reminder(texto="Llamar al dentista", disparar_en=ahora + timedelta(days=0)))
    db.add(Reminder(
        texto="Enviar la cuenta de cobro", disparar_en=ahora + timedelta(days=2),
        recurrencia="mensual",
    ))

    # --- Responsabilidades (una con cuenta+monto para «Registrar pago») ---
    db.add(Responsibility(
        nombre="Administración", recurrencia="mensual",
        proximo_venc=hoy + timedelta(days=3), monto=Decimal(270000),
        account_id=accs["Bancolombia"].id, category_id=cats["Servicios"].id,
    ))
    for nombre, rec, dias, monto in [
        ("Arriendo", "mensual", 5, 1450000),
        ("Internet y TV", "mensual", 9, 120000),
        ("Revisión del carro", "anual", 60, None),
    ]:
        db.add(Responsibility(
            nombre=nombre, recurrencia=rec, proximo_venc=hoy + timedelta(days=dias),
            monto=Decimal(monto) if monto else None,
        ))

    # --- Mercado: productos + algunas compras (para "por comprar") ---
    prods: dict[str, MarketProduct] = {}
    for nombre, cadencia, ult in [
        ("Leche", 4, 6),        # ya toca (pasó la cadencia)
        ("Huevos", 7, 9),       # ya toca
        ("Café", 20, 5),        # aún no
        ("Pan", 3, 4),          # ya toca
        ("Arroz", 30, 10),      # aún no
        ("Papel higiénico", 21, 25),  # ya toca
    ]:
        p = MarketProduct(nombre=nombre, cadencia_dias=cadencia, category_id=cats["Mercado"].id)
        db.add(p)
        prods[nombre] = p
        db.flush()
        db.add(MarketPurchase(
            product_id=p.id, fecha=hoy - timedelta(days=ult),
            cantidad=Decimal(1), precio=Decimal(0),
        ))


def resetear(db: Session) -> None:
    db.execute(text(f"TRUNCATE {_TABLAS} CASCADE"))


def main() -> None:
    args = sys.argv[1:]
    reset = "--reset" in args
    args = [a for a in args if a != "--reset"]
    if len(args) != 1:
        raise SystemExit("Uso: python -m app.seed_demo <slug> [--reset]")
    schema = slug_a_schema(args[0])
    with SessionLocal() as db:
        db.execute(text(f'SET search_path TO "{schema}", public'))
        if reset:
            resetear(db)
        else:
            ya = (
                db.execute(text("SELECT count(*) FROM account")).scalar()
                or db.execute(text("SELECT count(*) FROM note")).scalar()
            )
            if ya:
                raise SystemExit(
                    f"El inquilino {schema} ya tiene datos; usa --reset para "
                    "borrarlos y resembrar, o revisa el slug."
                )
        sembrar(db)
        db.commit()
    print(f"Datos demo sembrados en {schema}{' (reset)' if reset else ''}.")


if __name__ == "__main__":
    main()
