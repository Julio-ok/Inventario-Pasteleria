import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import os
import sys

# Añadir el directorio actual al path por si acaso
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inventory_logic import registrar_produccion, InsufficientIngredientsError

PORT = 8080
DB_PATH = "/home/julioc/antigravity/Inventario-Pasteleria/database.db"
HTML_PATH = "/home/julioc/antigravity/Inventario-Pasteleria/index.html"

class PasteleriaAPIHandler(http.server.BaseHTTPRequestHandler):
    
    # Silenciar logs estándar en consola para un reporte más limpio,
    # pero imprimir si hay errores de servidor.
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.serve_html()
        elif self.path == "/api/status":
            self.serve_api_status()
        else:
            self.send_error(404, "Página no encontrada")

    def do_POST(self):
        if self.path == "/api/produce":
            self.handle_api_produce()
        else:
            self.send_error(404, "Endpoint no encontrado")

    def serve_html(self):
        try:
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Error al leer index.html: {str(e)}")

    def serve_api_status(self):
        if not os.path.exists(DB_PATH):
            self.send_json({"error": "La base de datos no existe. Ejecuta el inicializador."}, 500)
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()

            # 1. Ingredientes
            cursor.execute("SELECT id, nombre, cantidad_kg, estado FROM ingredientes;")
            ingredients = [{"id": r[0], "nombre": r[1], "cantidad_kg": r[2], "estado": r[3]} for r in cursor.fetchall()]

            # 2. Pasteles
            cursor.execute("SELECT id, nombre, stock_unidades FROM pasteles;")
            pasteles = [{"id": r[0], "nombre": r[1], "stock_unidades": r[2]} for r in cursor.fetchall()]

            # 3. Alertas (últimas 15)
            cursor.execute("SELECT id, mensaje, fecha FROM alertas ORDER BY fecha DESC LIMIT 15;")
            alertas = [{"id": r[0], "mensaje": r[1], "fecha": r[2]} for r in cursor.fetchall()]

            # 4. Producción (últimas 15)
            cursor.execute("""
                SELECT p.id, pa.nombre, p.cantidad_producida, p.cantidad_merma, p.fecha 
                FROM produccion p 
                JOIN pasteles pa ON p.pastel_id = pa.id 
                ORDER BY p.fecha DESC 
                LIMIT 15;
            """)
            produccion = [{"id": r[0], "nombre": r[1], "cantidad_producida": r[2], "cantidad_merma": r[3], "fecha": r[4]} for r in cursor.fetchall()]

            conn.close()

            self.send_json({
                "ingredients": ingredients,
                "pasteles": pasteles,
                "alertas": alertas,
                "produccion": produccion
            })

        except Exception as e:
            self.send_json({"error": f"Error de base de datos: {str(e)}"}, 500)

    def handle_api_produce(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
            pastel_nombre = payload.get("pastel_nombre")
            cantidad_producida = float(payload.get("cantidad_producida", 0))
            cantidad_merma = float(payload.get("cantidad_merma", 0))
            
            if not pastel_nombre:
                self.send_json({"error": "Falta el nombre del pastel."}, 400)
                return

            # Ejecutar lógica del negocio
            registrar_produccion(DB_PATH, pastel_nombre, cantidad_producida, cantidad_merma)
            
            self.send_json({
                "message": f"Producción de {cantidad_producida} {pastel_nombre} registrada con éxito. Merma: {cantidad_merma}."
            })
            
        except InsufficientIngredientsError as e:
            self.send_json({"error": str(e)}, 400)
        except ValueError as e:
            self.send_json({"error": str(e)}, 400)
        except Exception as e:
            self.send_json({"error": f"Error interno: {str(e)}"}, 500)

    def send_json(self, data, status_code=200):
        try:
            response = json.dumps(data)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))
        except Exception as e:
            # Si hay un error enviando, no podemos hacer mucho más que loggearlo
            print(f"Error al enviar respuesta JSON: {str(e)}")

def run_server():
    # Permitir reusar dirección inmediatamente
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PasteleriaAPIHandler) as httpd:
        print(f"Servidor iniciado en http://localhost:{PORT}")
        print("Presiona Ctrl+C en la terminal para apagarlo.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nApagando servidor...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
