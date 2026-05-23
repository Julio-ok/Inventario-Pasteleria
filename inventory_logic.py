import sqlite3
import os

class InsufficientIngredientsError(Exception):
    """Excepción lanzada cuando no hay suficientes ingredientes o stock para la producción o pérdida."""
    pass

def crear_ingrediente(db_path, nombre, cantidad_inicial, unidad, fecha_caducidad=""):
    """
    Inserta un nuevo ingrediente en la base de datos con su fecha de caducidad.
    """
    if not nombre or nombre.strip() == "":
        raise ValueError("El nombre del ingrediente no puede estar vacío.")
    if cantidad_inicial < 0:
        raise ValueError("La cantidad inicial no puede ser negativa.")
    if not unidad or unidad.strip() == "":
        raise ValueError("La unidad de medida no puede estar vacía.")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO ingredientes (nombre, cantidad, unidad, fecha_caducidad) VALUES (?, ?, ?, ?);",
            (nombre.strip(), cantidad_inicial, unidad.strip(), fecha_caducidad.strip())
        )
        conn.commit()
        print(f"Ingrediente '{nombre}' creado con éxito (Vence: '{fecha_caducidad}').")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"El ingrediente '{nombre}' ya existe.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def crear_producto_con_receta(db_path, nombre, stock_inicial, receta_dict):
    """
    Inserta un nuevo producto (pastel/gelatina) y define su receta.
    receta_dict: Diccionario mapeando el nombre del ingrediente a la cantidad requerida.
    """
    if not nombre or nombre.strip() == "":
        raise ValueError("El nombre del producto no puede estar vacío.")
    if stock_inicial < 0:
        raise ValueError("El stock inicial no puede ser negativo.")
    if not receta_dict:
        raise ValueError("La receta del producto no puede estar vacía.")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Insertar el pastel
        cursor.execute(
            "INSERT INTO pasteles (nombre, stock_unidades) VALUES (?, ?);",
            (nombre.strip(), int(stock_inicial))
        )
        pastel_id = cursor.lastrowid
        
        # 2. Insertar ingredientes de la receta
        for ing_nombre, cant_req in receta_dict.items():
            if float(cant_req) <= 0:
                raise ValueError(f"La cantidad requerida para '{ing_nombre}' debe ser mayor a 0.")
            
            # Obtener el ID del ingrediente
            cursor.execute("SELECT id FROM ingredientes WHERE nombre = ?;", (ing_nombre,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"El ingrediente '{ing_nombre}' especificado en la receta no existe.")
            ing_id = row[0]
            
            # Insertar en la tabla de recetas
            cursor.execute(
                "INSERT INTO recetas (pastel_id, ingrediente_id, cantidad_requerida) VALUES (?, ?, ?);",
                (pastel_id, ing_id, float(cant_req))
            )
            
        conn.commit()
        print(f"Producto '{nombre}' y su receta creados con éxito.")
        return pastel_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def registrar_produccion(db_path, pastel_nombre, cantidad_producida, cantidad_merma):
    """
    Registra la producción de un pastel, descontando los ingredientes dinámicamente de la base de datos.
    """
    if cantidad_producida < 0 or cantidad_merma < 0:
        raise ValueError("La producción y la merma no pueden ser negativas.")
    
    if cantidad_merma > cantidad_producida:
        raise ValueError("La merma no puede ser mayor que la cantidad producida.")

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

        # 2. Obtener ingredientes y cantidades requeridas
        cursor.execute("""
            SELECT i.id, i.nombre, r.cantidad_requerida, i.cantidad, i.unidad 
            FROM recetas r
            JOIN ingredientes i ON r.ingrediente_id = i.id
            WHERE r.pastel_id = ?;
        """, (pastel_id,))
        receta_rows = cursor.fetchall()
        
        if not receta_rows:
            raise ValueError(f"El producto '{pastel_nombre}' no tiene una receta configurada.")

        # Verificar si hay suficiente stock de cada ingrediente
        insuficientes = []
        receta_a_descontar = []
        
        for ing_id, ing_nombre, req_unitario, disponible, unidad in receta_rows:
            total_requerido = req_unitario * cantidad_producida
            if disponible < total_requerido:
                insuficientes.append(
                    f"{ing_nombre} (Requerido: {total_requerido}{unidad}, Disponible: {disponible}{unidad})"
                )
            receta_a_descontar.append((ing_id, total_requerido))
        
        if insuficientes:
            raise InsufficientIngredientsError(
                "Stock insuficiente para iniciar la producción: " + ", ".join(insuficientes)
            )

        # Iniciar transacción para actualizar atómicamente
        cursor.execute("BEGIN TRANSACTION;")

        # Descontar ingredientes
        for ing_id, total_requerido in receta_a_descontar:
            cursor.execute(
                "UPDATE ingredientes SET cantidad = cantidad - ? WHERE id = ?;",
                (total_requerido, ing_id)
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
        print(f"Producción de {cantidad_producida} '{pastel_nombre}' registrada exitosamente.")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def registrar_perdida(db_path, tipo, referencia_id, cantidad, motivo):
    """
    Registra una pérdida/merma en el inventario real (ingrediente o producto).
    Valida que no quede en negativo.
    """
    if tipo not in ('ingrediente', 'producto'):
        raise ValueError("El tipo de pérdida debe ser 'ingrediente' o 'producto'.")
    if cantidad <= 0:
        raise ValueError("La cantidad de la pérdida debe ser mayor a 0.")
    if not motivo or motivo.strip() == "":
        raise ValueError("El motivo de la pérdida no puede estar vacío.")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        if tipo == 'ingrediente':
            # Verificar existencia y stock
            cursor.execute("SELECT nombre, cantidad, unidad FROM ingredientes WHERE id = ?;", (referencia_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"El ingrediente con ID {referencia_id} no existe.")
            nombre_item, disponible, unidad = row

            if disponible < cantidad:
                raise InsufficientIngredientsError(
                    f"Stock insuficiente para registrar pérdida de {nombre_item}: Disponible {disponible}{unidad}, requerida pérdida de {cantidad}{unidad}."
                )

            # Descontar stock
            cursor.execute("UPDATE ingredientes SET cantidad = cantidad - ? WHERE id = ?;", (cantidad, referencia_id))

        else:  # tipo == 'producto'
            # Verificar existencia y stock
            cursor.execute("SELECT nombre, stock_unidades FROM pasteles WHERE id = ?;", (referencia_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"El producto con ID {referencia_id} no existe.")
            nombre_item, disponible = row
            unidad = "uds"

            if disponible < cantidad:
                raise InsufficientIngredientsError(
                    f"Stock insuficiente para registrar pérdida de {nombre_item}: Disponible {disponible} uds, requerida pérdida de {cantidad} uds."
                )

            # Descontar stock
            cursor.execute("UPDATE pasteles SET stock_unidades = stock_unidades - ? WHERE id = ?;", (int(cantidad), referencia_id))

        # Registrar pérdida
        cursor.execute(
            "INSERT INTO perdidas (tipo, referencia_id, nombre_item, cantidad, unidad, motivo) VALUES (?, ?, ?, ?, ?, ?);",
            (tipo, referencia_id, nombre_item, cantidad, unidad, motivo.strip())
        )

        conn.commit()
        print(f"Pérdida de {cantidad} {unidad} de '{nombre_item}' por '{motivo}' registrada con éxito.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Bloque de prueba simulada
if __name__ == "__main__":
    DB_FILE = "/home/julioc/antigravity/Inventario-Pasteleria/database.db"
    
    # Reiniciar base de datos para pruebas
    print("--- Inicializando base de datos para validación de pérdidas ---")
    import subprocess
    subprocess.run(["python3", "/home/julioc/.gemini/antigravity/scratch/setup_db.py"], capture_output=True)

    print("\n--- PRUEBA 1: Registro de pérdida exitosa de ingrediente ---")
    # Harina tiene 15kg
    try:
        registrar_perdida(DB_FILE, 'ingrediente', 1, 3.5, 'vencido')
    except Exception as e:
        print("ERROR inesperado:", e)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad, unidad FROM ingredientes WHERE id = 1;")
    print("Stock de Harina (debería ser 11.5 kg):", c.fetchone())
    conn.close()

    print("\n--- PRUEBA 2: Intento de pérdida excesiva (Bloqueo stock negativo) ---")
    # Harina restante: 11.5kg. Intentar perder 12kg.
    try:
        registrar_perdida(DB_FILE, 'ingrediente', 1, 12.0, 'derramado')
        print("ERROR: Se permitió pérdida que deja stock en negativo!")
    except InsufficientIngredientsError as e:
        print("ÉXITO: Se bloqueó la pérdida correctamente. Mensaje:")
        print(f"  -> {e}")
    except Exception as e:
        print("ERROR inesperado:", e)

    print("\n--- PRUEBA 3: Registro de pérdida de producto ---")
    # Pastel de Chocolate tiene 5 unidades
    try:
        registrar_perdida(DB_FILE, 'producto', 1, 2, 'quemado')
    except Exception as e:
        print("ERROR inesperado:", e)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, stock_unidades FROM pasteles WHERE id = 1;")
    print("Stock de Pasteles (debería ser 3 unidades):", c.fetchone())
    c.execute("SELECT * FROM perdidas;")
    print("Tabla de pérdidas final:")
    for row in c.fetchall():
        print(row)
    conn.close()
