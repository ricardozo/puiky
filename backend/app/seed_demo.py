"""Siembra datos de demostración en un inquilino (para capturas / video).

Uso:  python -m app.seed_demo <slug>

Rellena finanzas, notas, proyectos/Kanban, tareas, recordatorios y
responsabilidades con un set realista y bonito. Se NIEGA a sembrar si el
inquilino ya tiene datos (para no pisar a un usuario real).
"""

import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.finances import Account, Budget, Category, Transaction
from app.models.notebooks import Notebook
from app.models.notes import Note
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import ChecklistItem, Task
from app.provision import slug_a_schema
from app.timeutils import now_local

_EMB = [0.001] * 768  # vector de relleno (la búsqueda semántica no aplica al demo)


def sembrar(db: Session) -> None:
    hoy = date.today()
    ahora = now_local()

    cats: dict[str, Category] = {}
    for n in ["Comida", "Transporte", "Servicios", "Salud", "Ocio", "Mercado", "Salario", "Educación"]:
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

    tx("gasto", 45000, "Efectivo", "Comida", nota="mercado del sábado", dias=2)
    tx("gasto", 10000, "Nequi", "Comida", nota="pan y café", dias=1)
    tx("gasto", 18000, "Nequi", "Transporte", nota="taxi", dias=3)
    tx("gasto", 62000, "Bancolombia", "Servicios", nota="recibo de luz", dias=4)
    tx("gasto", 35000, "Bancolombia", "Ocio", nota="cine", dias=5)
    tx("gasto", 40000, "Efectivo", "Salud", nota="farmacia", dias=6)
    tx("ingreso", 2500000, "Bancolombia", "Salario", nota="quincena", dias=7)
    tx("transferencia", 500000, "Bancolombia", dest="Ahorros", nota="ahorro del mes", dias=8)

    db.add(Budget(category_id=cats["Comida"].id, tope=Decimal(50000), periodo="mensual"))
    db.add(Budget(category_id=cats["Transporte"].id, tope=Decimal(100000), periodo="mensual"))
    db.add(Budget(category_id=cats["Ocio"].id, tope=Decimal(80000), periodo="mensual"))

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

    pf = Portfolio(nombre="Casa")
    db.add(pf)
    db.flush()
    proj = Project(nombre="Remodelación de la cocina", portfolio_id=pf.id, estado="activo")
    db.add(proj)
    db.flush()

    def tarea(titulo, estado, dias=None, avance=0, desc=None):
        t = Task(
            project_id=proj.id, titulo=titulo, estado=estado, avance_pct=avance,
            fecha_limite=(hoy + timedelta(days=dias)) if dias is not None else None,
            descripcion=desc,
        )
        db.add(t)
        return t

    tarea("Medir el espacio", "terminada", avance=100)
    tarea("Cotizar el mesón", "planeada", dias=2)
    tarea("Elegir color de pintura", "planeada", dias=6)
    t_ej = tarea("Comprar electrodomésticos", "en_ejecucion", dias=1, avance=40, desc="Nevera, estufa y campana.")
    tarea("Instalar la iluminación", "en_pausa", dias=12)
    db.flush()
    for i, (txt, hecho) in enumerate(
        [("Nevera", True), ("Estufa", True), ("Campana", False), ("Microondas", False), ("Licuadora", False)]
    ):
        db.add(ChecklistItem(task_id=t_ej.id, texto=txt, hecho=hecho, orden=i))

    for texto, dias in [("Pagar la tarjeta de crédito", 1), ("Renovar el SOAT del carro", 3), ("Llamar al dentista", 0)]:
        db.add(Reminder(texto=texto, disparar_en=ahora + timedelta(days=dias)))

    for nombre, rec, dias, monto in [
        ("Arriendo", "mensual", 5, 1450000),
        ("Internet y TV", "mensual", 9, 120000),
        ("Netflix", "mensual", 14, 44900),
        ("Revisión del carro", "anual", 60, None),
    ]:
        db.add(Responsibility(
            nombre=nombre, recurrencia=rec, proximo_venc=hoy + timedelta(days=dias),
            monto=Decimal(monto) if monto else None,
        ))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m app.seed_demo <slug>")
    schema = slug_a_schema(sys.argv[1])
    with SessionLocal() as db:
        db.execute(text(f'SET search_path TO "{schema}", public'))
        ya = (
            db.execute(text("SELECT count(*) FROM account")).scalar()
            or db.execute(text("SELECT count(*) FROM note")).scalar()
        )
        if ya:
            raise SystemExit(
                f"El inquilino {schema} ya tiene datos; no se siembra (evita pisar datos reales)."
            )
        sembrar(db)
        db.commit()
    print(f"Datos demo sembrados en {schema}.")


if __name__ == "__main__":
    main()
