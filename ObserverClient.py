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
import logging
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
        
        logging.debug(f"Cliente inicializado - UUID: {self.uuid}")
    
    def log(self, message: str, level: str = 'debug'):
        """Registra mensaje si está en modo verbose"""
        if self.verbose or level != 'debug':
            log_func = getattr(logging, level, logging.debug)
            log_func(message)
    
    def get_machine_uuid(self) -> str:
        """Obtiene un identificador único de la máquina."""
        try:
            logging.debug("Generando UUID de máquina...")
            machine_id = uuid.getnode()
            machine_uuid = uuid.UUID(int=machine_id)
            uuid_str = str(machine_uuid)
            logging.debug(f"UUID generado: {uuid_str}")
            return uuid_str
        except Exception as e:
            logging.warning(f"Error al generar UUID desde getnode(): {e}. Usando hostname.")
            hostname = platform.node()
            uuid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))
            logging.debug(f"UUID generado desde hostname: {uuid_str}")
            return uuid_str
    
    def connect(self) -> bool:
        """Establece conexión con el servidor y envía solicitud de suscripción."""
        try:
            logging.debug("Iniciando proceso de conexión...")
            
            if self.sock:
                logging.debug("Cerrando socket anterior...")
                try:
                    self.sock.close()
                except Exception as e:
                    logging.debug(f"Error al cerrar socket anterior: {e}")
            
            logging.debug("Creando nuevo socket...")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            logging.debug("Socket creado con timeout de 10 segundos")
            
            logging.info(f"Intentando conectar a {self.host}:{self.port}...")
            self.sock.connect((self.host, self.port))
            logging.info(f"✓ Conectado a {self.host}:{self.port}")
            
            subscribe_request = {
                "UUID": self.uuid,
                "ACTION": "subscribe"
            }
            
            logging.debug(f"Preparando solicitud de suscripción: {subscribe_request}")
            logging.debug("Enviando solicitud de suscripción...")
            request_json = json.dumps(subscribe_request)
            self.sock.sendall(request_json.encode('utf-8'))
            logging.debug(f"Solicitud enviada ({len(request_json)} bytes)")
            
            self.sock.settimeout(None)
            logging.debug("Timeout del socket removido, esperando respuesta...")
            
            response = self.receive_message()
            if response:
                logging.debug(f"Respuesta de suscripción recibida: {json.dumps(response)}")
                self.print_notification(response, is_subscription=True)
                logging.info("Suscripción confirmada por el servidor")
            else:
                logging.warning("No se recibió respuesta de confirmación de suscripción")
            
            return True
            
        except socket.timeout:
            logging.warning(f"Timeout al conectar con {self.host}:{self.port}")
            return False
        except ConnectionRefusedError:
            logging.error(f"Conexión rechazada por {self.host}:{self.port} - ¿Servidor activo?")
            return False
        except socket.gaierror as e:
            logging.error(f"Error de resolución de nombre para {self.host}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error inesperado al conectar: {type(e).__name__}: {e}")
            return False
    
    def receive_message(self) -> Optional[dict]:
        """Recibe un mensaje JSON del servidor."""
        try:
            logging.debug("Esperando mensaje del servidor...")
            data = b''
            buffer_size = 8192
            
            while True:
                logging.debug(f"Intentando recibir hasta {buffer_size} bytes...")
                chunk = self.sock.recv(buffer_size)
                
                if not chunk:
                    logging.warning("Socket cerrado por el servidor (recv retornó 0 bytes)")
                    return None
                
                data += chunk
                logging.debug(f"Recibidos {len(chunk)} bytes (total acumulado: {len(data)} bytes)")
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    logging.debug(f"Mensaje JSON completo recibido y decodificado correctamente")
                    logging.debug(f"Contenido del mensaje: {json.dumps(message, default=str)}")
                    return message
                except json.JSONDecodeError as e:
                    logging.debug(f"JSON incompleto, continuando recepción... (Error: {e})")
                    continue
                    
        except socket.timeout:
            logging.warning("Timeout al recibir mensaje del servidor")
            return None
        except ConnectionResetError:
            logging.warning("Conexión reiniciada por el servidor")
            return None
        except OSError as e:
            logging.error(f"Error de socket al recibir mensaje: {e}")
            return None
        except Exception as e:
            logging.error(f"Error inesperado al recibir mensaje: {type(e).__name__}: {e}")
            return None
    
    def print_notification(self, notification: dict, is_subscription: bool = False):
        """Imprime y guarda una notificación."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not is_subscription:
            self.notification_count += 1
            logging.info(f"Notificación #{self.notification_count} recibida")
        else:
            logging.debug("Procesando confirmación de suscripción")
        
        output = {
            "timestamp": timestamp,
            "notification_number": self.notification_count if not is_subscription else 0,
            "type": "subscription_confirmation" if is_subscription else "data_update",
            "data": notification
        }
        
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
        
        if self.output_file:
            try:
                logging.debug(f"Guardando notificación en archivo {self.output_file}...")
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    json.dump(output, f, indent=4, default=str, ensure_ascii=False)
                    f.write('\n')
                
                logging.info(f"Notificación guardada exitosamente en {self.output_file}")
            except IOError as e:
                logging.error(f"Error de I/O al guardar en archivo {self.output_file}: {e}")
            except Exception as e:
                logging.error(f"Error inesperado al guardar en archivo: {type(e).__name__}: {e}")
    
    def listen(self):
        """Escucha continuamente las notificaciones del servidor."""
        self.running = True
        logging.info("Iniciando modo escucha del cliente Observer")
        
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
        
        logging.info("Intentando conexión inicial...")
        while self.running and not self.connect():
            logging.warning(f"Conexión fallida. Reintentando en {self.retry_interval} segundos...")
            time.sleep(self.retry_interval)
        
        if not self.running:
            logging.info("Cliente detenido antes de establecer conexión")
            return
        
        print("✓ Suscrito exitosamente. Esperando notificaciones...")
        print("  (Presione Ctrl+C para detener)")
        print()
        logging.info("Cliente suscrito y esperando notificaciones...")
        
        while self.running:
            try:
                logging.debug("Esperando próxima notificación...")
                notification = self.receive_message()
                
                if notification is None:
                    logging.warning("Conexión perdida con el servidor")
                    logging.info("Iniciando proceso de reconexión...")
                    reconnected = False
                    reconnect_attempts = 0
                    
                    while self.running and not reconnected:
                        reconnect_attempts += 1
                        logging.info(f"Intento de reconexión #{reconnect_attempts} en {self.retry_interval} segundos...")
                        time.sleep(self.retry_interval)
                        reconnected = self.connect()
                    
                    if reconnected:
                        logging.info(f"✓ Reconectado exitosamente después de {reconnect_attempts} intentos")
                    
                    continue
                
                logging.debug("Notificación recibida, procesando...")
                self.print_notification(notification)
                
            except KeyboardInterrupt:
                logging.info("Interrupción de teclado detectada (Ctrl+C)")
                print("\n\nDeteniendo cliente...")
                break
            except Exception as e:
                logging.error(f"Error inesperado en el loop principal: {type(e).__name__}: {e}")
                logging.info(f"Esperando {self.retry_interval} segundos antes de continuar...")
                time.sleep(self.retry_interval)
        
        logging.info("Saliendo del modo escucha")
        self.stop()
    
    def stop(self):
        """Detiene el cliente y cierra la conexión"""
        self.running = False
        logging.info("Deteniendo cliente Observer...")
        
        if self.sock:
            try:
                logging.debug("Enviando mensaje de desuscripción...")
                unsubscribe_request = {
                    "UUID": self.uuid,
                    "ACTION": "unsubscribe"
                }
                request_json = json.dumps(unsubscribe_request)
                self.sock.sendall(request_json.encode('utf-8'))
                logging.info("Mensaje de desuscripción enviado al servidor")
                time.sleep(0.1)
            except Exception as e:
                logging.warning(f"Error al enviar desuscripción: {e}")
            
            try:
                logging.debug("Cerrando socket...")
                self.sock.close()
                logging.info("Conexión cerrada correctamente")
            except Exception as e:
                logging.debug(f"Error al cerrar socket: {e}")
        
        print("\n" + "=" * 70)
        print("RESUMEN DE SESIÓN")
        print("=" * 70)
        print(f"Notificaciones recibidas: {self.notification_count}")
        if self.output_file:
            print(f"Archivo de salida: {self.output_file}")
        print("=" * 70)
        print("\nCliente detenido.")
        
        logging.info(f"Sesión finalizada - Total de notificaciones: {self.notification_count}")


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
    
    if args.retry < 5:
        print("Error: El intervalo de reintento debe ser al menos 5 segundos", file=sys.stderr)
        sys.exit(1)
    
    # Configurar logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr  # Enviar logs a stderr para no mezclar con las notificaciones en stdout
    )
    
    logging.info("="*70)
    logging.info("ObserverClient iniciando...")
    logging.info(f"Configuración: {args.server}:{args.port}")
    logging.info(f"Modo verbose: {'Activado' if args.verbose else 'Desactivado'}")
    logging.info("="*70)
    
    client = ObserverClient(
        host=args.server,
        port=args.port,
        output_file=args.output,
        verbose=args.verbose,
        retry_interval=args.retry
    )
    
    try:
        client.listen()
        logging.info("Cliente finalizado normalmente")
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info("Cliente detenido por el usuario (KeyboardInterrupt)")
        client.stop()
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Error fatal en main: {type(e).__name__}: {e}")
        logging.debug("Traceback completo:", exc_info=True)
        client.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()