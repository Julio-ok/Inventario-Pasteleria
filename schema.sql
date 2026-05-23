-- Habilitar claves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- Tabla de Ingredientes
CREATE TABLE IF NOT EXISTS ingredientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    cantidad REAL NOT NULL DEFAULT 0.0 CHECK(cantidad >= 0.0),
    unidad TEXT NOT NULL DEFAULT 'kg',
    estado TEXT NOT NULL DEFAULT 'OK' CHECK(estado IN ('OK', 'REORDEN'))
);

-- Tabla de Pasteles/Productos
CREATE TABLE IF NOT EXISTS pasteles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    stock_unidades INTEGER NOT NULL DEFAULT 0 CHECK(stock_unidades >= 0)
);

-- Tabla de Recetas (Relación Muchos a Muchos)
CREATE TABLE IF NOT EXISTS recetas (
    pastel_id INTEGER NOT NULL,
    ingrediente_id INTEGER NOT NULL,
    cantidad_requerida REAL NOT NULL CHECK(cantidad_requerida > 0.0),
    PRIMARY KEY (pastel_id, ingrediente_id),
    FOREIGN KEY (pastel_id) REFERENCES pasteles(id) ON DELETE CASCADE,
    FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE
);

-- Tabla de Registro de Producción
CREATE TABLE IF NOT EXISTS produccion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pastel_id INTEGER NOT NULL,
    cantidad_producida REAL NOT NULL CHECK(cantidad_producida >= 0.0),
    cantidad_merma REAL NOT NULL DEFAULT 0.0 CHECK(cantidad_merma >= 0.0),
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(pastel_id) REFERENCES pasteles(id)
);

-- Tabla de Alertas de Negocio
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensaje TEXT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- REGLA 3: Si la harina baja de 10kg, el estado cambia a REORDEN (al insertar)
CREATE TRIGGER IF NOT EXISTS trigger_harina_reorden_insert
AFTER INSERT ON ingredientes
FOR EACH ROW
BEGIN
    UPDATE ingredientes
    SET estado = CASE
        WHEN NEW.nombre = 'Harina' AND NEW.cantidad < 10.0 THEN 'REORDEN'
        ELSE 'OK'
    END
    WHERE id = NEW.id AND nombre = 'Harina';
END;

-- REGLA 3: Si la harina baja de 10kg, el estado cambia a REORDEN (al actualizar)
CREATE TRIGGER IF NOT EXISTS trigger_harina_reorden_update
AFTER UPDATE OF cantidad ON ingredientes
FOR EACH ROW
BEGIN
    UPDATE ingredientes
    SET estado = CASE
        WHEN NEW.nombre = 'Harina' AND NEW.cantidad < 10.0 THEN 'REORDEN'
        ELSE 'OK'
    END
    WHERE id = NEW.id AND nombre = 'Harina';
END;

-- REGLA 2: La merma genera alerta si supera el 15% de la producción
CREATE TRIGGER IF NOT EXISTS trigger_alerta_merma_insert
AFTER INSERT ON produccion
FOR EACH ROW
WHEN NEW.cantidad_merma > 0.15 * NEW.cantidad_producida
BEGIN
    INSERT INTO alertas (mensaje)
    VALUES ('ALERTA: La merma del lote ' || NEW.id || ' para el pastel ID ' || NEW.pastel_id || ' es de ' || NEW.cantidad_merma || ', lo cual supera el 15% de la producción (' || NEW.cantidad_producida || ').');
END;
