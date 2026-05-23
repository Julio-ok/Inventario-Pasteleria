# 🍰 Pastelería Expert - Control de Inventario Inteligente v1.0

Sistema local interactivo de control de inventario y registro de producción para pastelerías, diseñado para garantizar el cumplimiento automático de reglas críticas de negocio mediante disparadores (triggers) en base de datos SQLite y validación en backend de Python.

## 🚀 Características del Sistema

- **Tablero Visual en Tiempo Real**: Interfaz web premium con diseño oscuro responsivo.
  - 🟢 **Verde (En Stock)**: Ingredientes y pasteles listos para su uso y venta.
  - 🟡 **Amarillo (REORDEN)**: Alerta visual activa cuando un ingrediente crítico baja de su stock mínimo (ej. Harina < 10kg).
  - 🔴 **Rojo (Sin Stock)**: Indicador inmediato de desabasto o producto agotado.
- **Registro Atómico de Producción**: Lógica matemática en Python que descuenta los ingredientes de cada receta por lote producido e incrementa el stock de pasteles aptos para venta.
- **Prevención de Stock Negativo**: Validación en backend y base de datos que bloquea transacciones que dejen el stock de insumos o productos por debajo de cero.
- **Detección Automática de Merma Excesiva**: Sistema que genera alertas de negocio persistentes si la merma registrada en un lote supera el **15%** de la producción total del mismo.

---

## 🛠️ Arquitectura y Componentes

- **Base de Datos ([database.db](database.db))**: Almacén SQLite configurado con restricciones de integridad referencial (`FOREIGN KEYS`) y de rango (`CHECK`).
- **Disparadores SQL ([schema.sql](schema.sql))**: Automatizan las alertas de merma y el cambio a estado `REORDEN` para ingredientes de forma reactiva e inmediata en la base de datos.
- **Lógica de Negocio ([inventory_logic.py](inventory_logic.py))**: Controla el descuento de ingredientes y valida la suficiencia de stock lanzando excepciones personalizadas en caso de insuficiencia.
- **Servidor API ([server.py](server.py))**: Servidor HTTP REST ligero escrito en Python nativo (sin dependencias externas) que expone endpoints para consultar el estado del inventario e ingresar lotes de producción.
- **Interfaz Web ([index.html](index.html))**: Aplicación de una sola página (SPA) moderna, elegante e interactiva que se actualiza periódicamente y notifica mediante *Toasts* sobre éxitos y fallas.

---

## 📖 Reglas de Negocio Automatizadas

1. **Stock no negativo**: Tanto ingredientes (`cantidad_kg`) como pasteles (`stock_unidades`) tienen restricciones a nivel tabla (`CHECK >= 0.0`).
2. **Alerta de Merma > 15%**: Un `TRIGGER AFTER INSERT` en la tabla `produccion` detecta si `cantidad_merma > 0.15 * cantidad_producida` e inserta una alerta de negocio en la tabla `alertas`.
3. **Harina < 10kg en REORDEN**: Dos `TRIGGERS` (tanto en insert como en update de `ingredientes`) cambian el estado de la harina a `REORDEN` si su cantidad en kilogramos cae por debajo de 10. Si sube a 10 o más, el estado vuelve a `OK` automáticamente.

---

## 💻 Instalación y Uso

1. **Clonar el repositorio**:
   ```bash
   git clone <url-del-repositorio>
   cd Inventario-Pasteleria
   ```

2. **Inicializar la Base de Datos**:
   Si deseas restaurar o iniciar la base de datos limpia con datos de prueba, puedes ejecutar:
   ```bash
   python3 -c "import sqlite3; ... (o usar el script setup_db.py si está disponible)"
   ```
   *Nota: El servidor API inicializa la base de datos automáticamente si esta no existe.*

3. **Iniciar el Servidor API**:
   Ejecuta el servidor web local:
   ```bash
   python3 server.py
   ```

4. **Acceder a la Interfaz**:
   Abre tu navegador de preferencia e ingresa a:
   👉 [http://localhost:8080](http://localhost:8080)

---

## 📂 Estructura del Repositorio

```text
├── .agent/
│   └── skills/
│       └── pasteleria-expert/
│           └── SKILL.md         # Reglas de negocio e instrucciones del agente repostero
├── index.html                   # Interfaz de usuario web (Front-end)
├── inventory_logic.py           # Funciones de lógica de negocio y pruebas (Python)
├── server.py                    # Servidor API HTTP Backend (Python)
├── schema.sql                   # Estructura DDL y Triggers de SQLite
├── database.db                  # Base de datos SQLite local
└── README.md                    # Documentación del proyecto (este archivo)
```
