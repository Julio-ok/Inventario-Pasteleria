import sqlite3
import os

class InsufficientIngredientsError(Exception):
    """Excepción lanzada cuando no hay suficientes ingredientes para la producción."""
    pass

def crear_ingrediente(db_path, nombre, cantidad_inicial, unidad):
    """
    Inserta un nuevo ingrediente en la base de datos.
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
            "INSERT INTO ingredientes (nombre, cantidad, unidad) VALUES (?, ?, ?);",
            (nombre.strip(), cantidad_inicial, unidad.strip())
        )
        conn.commit()
        print(f"Ingrediente '{nombre}' creado con éxito.")
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
    receta_dict: Diccionario mapeando el nombre del ingrediente a la cantidad requerida por unidad de pastel.
    Ejemplo: {"Harina": 0.5, "Huevo": 4}
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
    Lanza InsufficientIngredientsError si el stock de ingredientes no es suficiente.
    Añade al stock de pasteles la cantidad neta producida (cantidad_producida - cantidad_merma).
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

        # 2. Obtener ingredientes y cantidades requeridas por la receta de este pastel
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
        receta_a_descontar = [] # Lista de tuplas (ingrediente_id, total_requerido)
        
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

    print("\n--- PRUEBA DE CREACIÓN DE INGREDIENTE ---")
    try:
        new_ing_id = crear_ingrediente(DB_FILE, "Fresa", 5.0, "kg")
        # Intentar crear duplicado
        crear_ingrediente(DB_FILE, "Fresa", 2.0, "kg")
    except ValueError as e:
        print("ÉXITO: Se bloqueó duplicado de ingrediente. Mensaje:", e)

    print("\n--- PRUEBA DE CREACIÓN DE PRODUCTO CON RECETA DINÁMICA ---")
    try:
        # Nuevo pastel "Pastel de Fresa" que requiere:
        # Harina: 0.4 kg
        # Huevo: 3 piezas
        # Fresa: 1.0 kg
        receta_fresa = {
            "Harina": 0.4,
            "Huevo": 3,
            "Fresa": 1.0
        }
        crear_producto_con_receta(DB_FILE, "Pastel de Fresa", 2, receta_fresa)
    except Exception as e:
        print("ERROR en creación de producto:", e)

    print("\n--- PRUEBA DE PRODUCCIÓN CON NUEVO PRODUCTO ---")
    # Stock inicial: Harina(12), Huevo(100), Fresa(5)
    # Producir: 3 Pasteles de Fresa (requiere Harina: 1.2kg, Huevo: 9 piezas, Fresa: 3.0kg)
    try:
        registrar_produccion(DB_FILE, "Pastel de Fresa", 3.0, 0.0)
    except Exception as e:
        print("ERROR inesperado en producción de Fresa:", e)

    print("\n--- STOCK FINAL DE CONTROL ---")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad, unidad, estado FROM ingredientes;")
    print("Ingredientes:", c.fetchall())
    c.execute("SELECT nombre, stock_unidades FROM pasteles;")
    print("Pasteles:", c.fetchall())
    conn.close()
