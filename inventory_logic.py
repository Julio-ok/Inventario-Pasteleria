import sqlite3
import os

class InsufficientIngredientsError(Exception):
    """Excepción lanzada cuando no hay suficientes ingredientes para la producción."""
    pass

# Definición de Recetas (Ingredientes necesarios por cada unidad de pastel en kg)
RECETAS = {
    "Pastel de Chocolate Tres Leches": {
        "Harina": 0.5,      # 0.5 kg por pastel
        "Huevo": 0.2,       # 0.2 kg por pastel (aprox. 4 huevos)
        "Chocolate": 0.3    # 0.3 kg por pastel
    }
}

def registrar_produccion(db_path, pastel_nombre, cantidad_producida, cantidad_merma):
    """
    Registra la producción de un pastel, descontando los ingredientes de forma atómica.
    Lanza InsufficientIngredientsError si el stock de ingredientes no es suficiente.
    Añade al stock de pasteles la cantidad neta producida (cantidad_producida - cantidad_merma).
    """
    if cantidad_producida < 0 or cantidad_merma < 0:
        raise ValueError("La producción y la merma no pueden ser negativas.")
    
    if cantidad_merma > cantidad_producida:
        raise ValueError("La merma no puede ser mayor que la cantidad producida.")

    if pastel_nombre not in RECETAS:
        raise ValueError(f"Receta para '{pastel_nombre}' no encontrada en el sistema.")

    receta = RECETAS[pastel_nombre]
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    try:
        # 1. Obtener ID del pastel
        cursor.execute("SELECT id, stock_unidades FROM pasteles WHERE nombre = ?;", (pastel_nombre,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"El pastel '{pastel_nombre}' no está registrado en la base de datos.")
        pastel_id, stock_actual_pasteles = row

        # 2. Verificar y descontar ingredientes
        # Obtenemos los stocks actuales de los ingredientes requeridos
        ingredientes_actuales = {}
        cursor.execute(
            f"SELECT nombre, cantidad_kg FROM ingredientes WHERE nombre IN ({','.join(['?']*len(receta))});",
            list(receta.keys())
        )
        for nombre, cantidad in cursor.fetchall():
            ingredientes_actuales[nombre] = cantidad

        # Validamos que existan todos los ingredientes de la receta en la base de datos
        for ing in receta.keys():
            if ing not in ingredientes_actuales:
                raise ValueError(f"El ingrediente '{ing}' requerido para la receta no existe en la base de datos.")

        # Verificar si hay suficiente stock de cada ingrediente
        insuficientes = []
        for ing, req_unitario in receta.items():
            total_requerido = req_unitario * cantidad_producida
            disponible = ingredientes_actuales[ing]
            if disponible < total_requerido:
                insuficientes.append(
                    f"{ing} (Requerido: {total_requerido}kg, Disponible: {disponible}kg)"
                )
        
        if insuficientes:
            raise InsufficientIngredientsError(
                "Stock insuficiente para iniciar la producción: " + ", ".join(insuficientes)
            )

        # Iniciar transacción para actualizar atómicamente
        cursor.execute("BEGIN TRANSACTION;")

        # Descontar ingredientes
        for ing, req_unitario in receta.items():
            total_requerido = req_unitario * cantidad_producida
            cursor.execute(
                "UPDATE ingredientes SET cantidad_kg = cantidad_kg - ? WHERE nombre = ?;",
                (total_requerido, ing)
            )

        # Aumentar stock de pasteles (solo los aptos para venta: producidos - merma)
        cantidad_neta = cantidad_producida - cantidad_merma
        cursor.execute(
            "UPDATE pasteles SET stock_unidades = stock_unidades + ? WHERE id = ?;",
            (int(cantidad_neta), pastel_id)
        )

        # Registrar la producción y la merma
        cursor.execute(
            "INSERT INTO produccion (pastel_id, cantidad_producida, cantidad_merma) VALUES (?, ?, ?);",
            (pastel_id, cantidad_producida, cantidad_merma)
        )

        conn.commit()
        print(f"Producción de {cantidad_producida} '{pastel_nombre}' registrada exitosamente (Merma: {cantidad_merma}).")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Bloque de prueba simulada
if __name__ == "__main__":
    DB_FILE = "/home/julioc/antigravity/Inventario-Pasteleria/database.db"
    
    # Reiniciar base de datos para pruebas limpias usando el script previo
    print("--- Inicializando base de datos para pruebas de lógica ---")
    import subprocess
    subprocess.run(["python3", "/home/julioc/.gemini/antigravity/scratch/setup_db.py"], capture_output=True)

    print("\n--- PRUEBA DE STOCK INICIAL ---")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad_kg, estado FROM ingredientes;")
    print("Ingredientes:", c.fetchall())
    c.execute("SELECT nombre, stock_unidades FROM pasteles;")
    print("Pasteles:", c.fetchall())
    conn.close()

    print("\n--- PRUEBA 1: Producción exitosa (10 pasteles) ---")
    # Requiere: Harina (5kg), Huevo (2kg), Chocolate (3kg)
    # Disponible inicial: Harina (12kg), Huevo (5kg), Chocolate (8kg)
    try:
        registrar_produccion(DB_FILE, "Pastel de Chocolate Tres Leches", 10.0, 1.0)
    except Exception as e:
        print("ERROR inesperado en Prueba 1:", e)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad_kg, estado FROM ingredientes;")
    print("Stock de Ingredientes después de la producción:", c.fetchall())
    c.execute("SELECT nombre, stock_unidades FROM pasteles;")
    print("Stock de Pasteles (debería ser 5 inicial + 9 neto = 14):", c.fetchall())
    c.execute("SELECT * FROM alertas;")
    print("Alertas generadas (debería haber una alerta por la merma del 10%? No, es 10% <= 15%):", c.fetchall())
    conn.close()

    print("\n--- PRUEBA 2: Producción con merma excesiva (10 pasteles, 2 mermados = 20%) ---")
    # Requiere: Harina (5kg), Huevo (2kg), Chocolate (3kg)
    # Disponible actual: Harina (7kg), Huevo (3kg), Chocolate (5kg)
    try:
        registrar_produccion(DB_FILE, "Pastel de Chocolate Tres Leches", 10.0, 2.0)
    except Exception as e:
        print("ERROR inesperado en Prueba 2:", e)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM alertas;")
    print("Alertas generadas (debería incluir una nueva alerta del 20%):")
    for a in c.fetchall():
        print(a)
    conn.close()

    print("\n--- PRUEBA 3: Intento de producción con stock insuficiente (Bloqueo de stock negativo) ---")
    # Requiere: Harina (5kg), Huevo (2kg), Chocolate (3kg)
    # Disponible actual: Harina (2kg), Huevo (1kg), Chocolate (2kg)
    try:
        registrar_produccion(DB_FILE, "Pastel de Chocolate Tres Leches", 10.0, 0.0)
        print("ERROR: Se permitió la producción a pesar del stock insuficiente!")
    except InsufficientIngredientsError as e:
        print("ÉXITO: Se bloqueó la producción por falta de ingredientes. Mensaje:")
        print(f"  -> {e}")
    except Exception as e:
        print("ERROR inesperado en Prueba 3:", e)

    print("\n--- STOCK FINAL DE CONTROL ---")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad_kg, estado FROM ingredientes;")
    print("Ingredientes (ninguno debe ser negativo):", c.fetchall())
    c.execute("SELECT nombre, stock_unidades FROM pasteles;")
    print("Pasteles:", c.fetchall())
    conn.close()
