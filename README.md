Inventario Pastelería Expert — Google Antigravity Test

Proyecto experimental hecho como prueba de la nueva herramienta de Google Antigravity, explorando generación asistida de código, lógica de negocio y UI para un sistema de inventario de pastelería.

📦 Inventario Pastelería Expert
📖 Descripción General

Inventario Pastelería Expert es un sistema web de gestión de inventario diseñado para pequeñas y medianas pastelerías o panaderías. La aplicación permite controlar materias primas, inventario de productos terminados, lotes de producción y mermas.

Además, incluye alertas en tiempo real para:

Bajo inventario
Necesidad de reabastecimiento
Próxima caducidad de ingredientes

Todo esto ayuda a mantener la continuidad operativa y mejorar el control interno del negocio.

✨ Características Principales
1. Control de Stock

Monitoreo en tiempo real de ingredientes y productos terminados, incluyendo validaciones automáticas para evitar inventarios negativos.

2. Gestión de Mermas

Registro de desperdicios de producción y pérdidas manuales, con estadísticas acumuladas mensuales.

3. Alertas de Reabastecimiento

Regla de negocio que marca automáticamente la Harina con estado REORDEN cuando el stock baja de 10 kg.

4. Alertas de Caducidad

Los ingredientes pueden tener fecha de expiración:

Productos próximos a vencer (menos de 5 días) se resaltan visualmente.
Productos vencidos generan alertas críticas en rojo.
5. Gestión Dinámica de Recetas

Permite definir recetas por producto, especificando ingredientes y cantidades requeridas por unidad producida.
El sistema descuenta automáticamente el stock al fabricar productos.

6. Interfaz Responsive

Interfaz moderna en modo oscuro con:

Vista compacta de ingredientes
Vista en cuadrícula para productos terminados
⚙️ Guía de Instalación
📋 Requisitos Previos
Python 3.9 o superior
SQLite 3 (incluido con Python)
Git
Navegador moderno (Chrome, Firefox, Edge)

La base de datos utilizada es:

database.db
🚀 Instalación
1. Clonar el repositorio
git clone https://github.com/Julio-ok/Inventario-Pasteleria.git
cd Inventario-Pasteleria
2. Inicializar la base de datos
python3 setup_db.py

Este script:

Crea el esquema SQLite definido en schema.sql
Genera las tablas iniciales necesarias para el proyecto
3. Ejecutar el servidor
python3 server.py

La aplicación estará disponible en:

http://localhost:8080
4. (Opcional) Crear entorno virtual

Recomendado para aislar el entorno de desarrollo.

Linux / macOS
python3 -m venv venv
source venv/bin/activate
Windows
python
.\venv\Scripts\activate

El proyecto no utiliza dependencias externas, por lo que no es necesario ejecutar:

pip install
📁 Estructura del Proyecto
Inventario-Pasteleria/
├── .agent/
│   └── skills/
│       └── pasteleria-expert/
│           └── SKILL.md
│
├── database.db
├── index.html
├── inventory_logic.py
├── server.py
├── schema.sql
├── setup_db.py
├── .gitignore
└── README.md
📌 Descripción de Archivos
Archivo	Descripción
inventory_logic.py	Lógica principal del sistema de inventario
server.py	Servidor HTTP y API REST
schema.sql	Estructura y triggers de SQLite
setup_db.py	Script de creación/reinicio de base de datos
index.html	Frontend en HTML/CSS/JavaScript
database.db	Base de datos SQLite generada automáticamente
👨‍💻 Créditos
Reglas de Negocio y Diseño

Julio César

Definición de:

políticas de inventario
manejo de caducidades
reglas de reorden
experiencia de usuario
lógica operativa del sistema
Generación e Implementación de Código

Google Antigravity

Generación asistida de:

Backend en Python
Base de datos SQLite
API REST
Interfaz web responsive
HTML/CSS/JavaScript
