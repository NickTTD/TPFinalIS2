#!/usr/bin/env python3
"""
ObserverClient.py
Cliente Observer para recibir notificaciones de cambios en CorporateData
Ingeniería de Software II - UADER-FCyT-IS2
"""

import socket
import json
import argparse
import sys
import time
import uuid
import platform
from datetime import datetime
from typing import Optional

class ObserverClient:
    """Cliente que se suscribe para recibir notificaciones de cambios"""
    
    def __init__(self, host: str = 'localhost', port: int = 8080, 
                 output_file: Optional[str] = None, verbose: bool = False,
                 retry_interval: int = 30):
        self.host = host
        self.port = port
        self.output_file = output_file
        self.verbose = verbose
        self.retry_interval = retry_interval
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.notification_count = 0
        self.uuid = self.get_machine_uuid()
    
    def get_machine_uuid(self) -> str:
        """
        Obtiene un identificador único de la máquina.
        Intenta usar el UUID del hardware, si no está disponible genera uno basado en el hostname.
        """
        try:
            machine_id = uuid.getnode()
            machine_uuid = uuid.UUID(int=machine_id)
            return str(machine_uuid)
        except:
            hostname = platform.node()
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))
    
    def log(self, message: str, level: str = "INFO"):
        """Imprime mensaje si está en modo verbose"""
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] [{level}] {message}", file=sys.stderr)
    
    def connect(self) -> bool:
        """
        Establece conexión con el servidor y envía solicitud de suscripción.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # Cerrar socket existente si hay uno
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            # Crear nuevo socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)  # Timeout para conectar
            
            self.log(f"Intentando conectar a {self.host}:{self.port}...")
            self.sock.connect((self.host, self.port))
            self.log(f"✓ Conectado a {self.host}:{self.port}", "SUCCESS")
            
            # Enviar solicitud de suscripción
            subscribe_request = {
                "UUID": self.uuid,
                "ACTION": "subscribe"
            }
            
            self.log(f"Enviando solicitud de suscripción...")
            request_json = json.dumps(subscribe_request)
            self.sock.sendall(request_json.encode('utf-8'))
            
            # Eliminar timeout para recibir datos (permanece abierto)
            self.sock.settimeout(None)
            
            # Recibir confirmación de suscripción
            response = self.receive_message()
            if response:
                self.log(f"Respuesta de suscripción: {json.dumps(response)}", "SUCCESS")
                self.print_notification(response, is_subscription=True)
            
            return True
            
        except socket.timeout:
            self.log(f"Timeout al conectar con {self.host}:{self.port}", "ERROR")
            return False
        except ConnectionRefusedError:
            self.log(f"Conexión rechazada por {self.host}:{self.port}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error al conectar: {e}", "ERROR")
            return False
    
    def receive_message(self) -> Optional[dict]:
        """
        Recibe un mensaje JSON del servidor.
        
        Returns:
            Diccionario con el mensaje o None si hay error
        """
        try:
            data = b''
            buffer_size = 8192
            
            while True:
                chunk = self.sock.recv(buffer_size)
                
                if not chunk:
                    # Conexión cerrada por el servidor
                    return None
                
                data += chunk
                
                # Intentar decodificar el JSON
                try:
                    message = json.loads(data.decode('utf-8'))
                    return message
                except json.JSONDecodeError:
                    # JSON incompleto, seguir recibiendo
                    continue
                    
        except socket.timeout:
            self.log("Timeout al recibir mensaje", "WARNING")
            return None
        except ConnectionResetError:
            self.log("Conexión reiniciada por el servidor", "WARNING")
            return None
        except Exception as e:
            self.log(f"Error al recibir mensaje: {e}", "ERROR")
            return None
    
    def print_notification(self, notification: dict, is_subscription: bool = False):
        """
        Imprime y guarda una notificación.
        
        Args:
            notification: Diccionario con la notificación
            is_subscription: Si es True, indica que es la confirmación de suscripción
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Incrementar contador solo si no es suscripción
        if not is_subscription:
            self.notification_count += 1
        
        # Preparar salida
        output = {
            "timestamp": timestamp,
            "notification_number": self.notification_count if not is_subscription else 0,
            "type": "subscription_confirmation" if is_subscription else "data_update",
            "data": notification
        }
        
        # Mostrar en stdout
        print("=" * 70)
        if is_subscription:
            print("CONFIRMACIÓN DE SUSCRIPCIÓN")
        else:
            print(f"NOTIFICACIÓN #{self.notification_count}")
        print("=" * 70)
        print(f"Timestamp: {timestamp}")
        print("-" * 70)
        print(json.dumps(notification, indent=4, default=str, ensure_ascii=False))
        print("=" * 70)
        print()
        sys.stdout.flush()
        
        # Guardar en archivo si fue especificado
        if self.output_file:
            try:
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    json.dump(output, f, indent=4, default=str, ensure_ascii=False)
                    f.write('\n')
                
                self.log(f"Notificación guardada en {self.output_file}")
            except Exception as e:
                self.log(f"Error al guardar en archivo: {e}", "ERROR")
    
    def listen(self):
        """
        Escucha continuamente las notificaciones del servidor.
        Maneja reconexiones automáticas en caso de desconexión.
        """
        self.running = True
        
        print("=" * 70)
        print("OBSERVER CLIENT - Cliente de Notificaciones")
        print("=" * 70)
        print(f"UUID del cliente: {self.uuid}")
        print(f"Servidor: {self.host}:{self.port}")
        print(f"Archivo de salida: {self.output_file if self.output_file else 'stdout'}")
        print(f"Intervalo de reconexión: {self.retry_interval} segundos")
        print(f"Modo verbose: {'Activado' if self.verbose else 'Desactivado'}")
        print("=" * 70)
        print()
        
        # Intentar conexión inicial
        while self.running and not self.connect():
            self.log(f"Reintentando en {self.retry_interval} segundos...")
            time.sleep(self.retry_interval)
        
        if not self.running:
            return
        
        print("✓ Suscrito exitosamente. Esperando notificaciones...")
        print("  (Presione Ctrl+C para detener)")
        print()
        
        # Loop principal de recepción
        while self.running:
            try:
                # Recibir notificación
                notification = self.receive_message()
                
                if notification is None:
                    # Conexión perdida
                    self.log("Conexión perdida. Intentando reconectar...", "WARNING")
                    
                    # Intentar reconexión
                    reconnected = False
                    while self.running and not reconnected:
                        self.log(f"Reintentando conexión en {self.retry_interval} segundos...")
                        time.sleep(self.retry_interval)
                        reconnected = self.connect()
                    
                    if reconnected:
                        self.log("✓ Reconectado exitosamente", "SUCCESS")
                    
                    continue
                
                # Procesar notificación
                self.print_notification(notification)
                
            except KeyboardInterrupt:
                print("\n\nDeteniendo cliente...")
                break
            except Exception as e:
                self.log(f"Error inesperado: {e}", "ERROR")
                self.log(f"Reintentando en {self.retry_interval} segundos...")
                time.sleep(self.retry_interval)
        
        self.stop()
    
    def stop(self):
        """Detiene el cliente y cierra la conexión"""
        self.running = False
        
        if self.sock:
            try:
                self.sock.close()
                self.log("Conexión cerrada")
            except:
                pass
        
        print("\n" + "=" * 70)
        print("RESUMEN DE SESIÓN")
        print("=" * 70)
        print(f"Notificaciones recibidas: {self.notification_count}")
        if self.output_file:
            print(f"Archivo de salida: {self.output_file}")
        print("=" * 70)
        print("\nCliente detenido.")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Cliente Observer para recibir notificaciones de CorporateData',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python observerclient.py
  python observerclient.py -s=localhost -p=8080
  python observerclient.py -s=192.168.1.100 -p=9090 -o=notifications.json
  python observerclient.py -o=notifications.json -v
  python observerclient.py -s=localhost -p=8080 -o=output.json -v --retry=60

El cliente se mantendrá escuchando notificaciones hasta que se detenga
manualmente con Ctrl+C. En caso de pérdida de conexión, reintentará
automáticamente cada 30 segundos (o el intervalo configurado).
        """
    )
    
    parser.add_argument('-s', '--server', default='localhost',
                        help='Hostname o IP del servidor (default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Puerto del servidor (default: 8080)')
    parser.add_argument('-o', '--output', required=False,
                        help='Archivo JSON de salida para guardar notificaciones (opcional)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Modo verbose, muestra información detallada en stderr')
    parser.add_argument('--retry', type=int, default=30,
                        help='Intervalo de reintento en segundos (default: 30)')
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.retry < 5:
        print("Error: El intervalo de reintento debe ser al menos 5 segundos", 
              file=sys.stderr)
        sys.exit(1)
    
    # Crear cliente
    client = ObserverClient(
        host=args.server,
        port=args.port,
        output_file=args.output,
        verbose=args.verbose,
        retry_interval=args.retry
    )
    
    try:
        # Iniciar escucha
        client.listen()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nCliente detenido por el usuario.")
        client.stop()
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {e}", file=sys.stderr)
        client.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()