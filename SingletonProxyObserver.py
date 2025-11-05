#!/usr/bin/env python3
"""
SingletonProxyObserverTPFI.py - Versión OOP mejorada
Servidor Proxy con patrón Singleton y Observer para gestión de CorporateData
Ingeniería de Software II - UADER-FCyT-IS2

ESTE ES EL CÓDIGO VIEJO MONOLÍTICO QUE FUE REFACTORIZADO EN LA CARPETA SERVIDOR
"""

from abc import ABC, abstractmethod
import argparse
from datetime import datetime
from decimal import Decimal
import json
import logging
import socket
import sys
import threading
from typing import Any, Dict, List, Optional
import uuid as uuid_lib

import boto3


class DecimalConverter:
    """Utilidad para conversión de tipos Decimal de DynamoDB"""
    
    @staticmethod
    def to_native(obj):
        """Convierte objetos Decimal a tipos nativos de Python"""
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: DecimalConverter.to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DecimalConverter.to_native(i) for i in obj]
        return obj
    
    @staticmethod
    def to_decimal(obj):
        """Convierte números nativos a Decimal para DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, int):
            return Decimal(obj)
        elif isinstance(obj, dict):
            return {k: DecimalConverter.to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DecimalConverter.to_decimal(i) for i in obj]
        return obj


class SessionManager:
    """Gestor de sesiones único (Singleton)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SessionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    def generate_id(self) -> str:
        """Genera un ID de sesión único con uuid4(random)"""
        return str(uuid_lib.uuid4()) 


class LogEntry:
    """Representa una entrada de log"""
    
    def __init__(self, uuid: str, session: str, action: str,
                 record_id: Optional[str] = None, 
                 additional_data: Optional[Dict] = None):
        self.id = str(uuid_lib.uuid4())
        self.uuid = uuid
        self.session = session
        self.action = action
        self.timestamp = datetime.now().isoformat()
        self.record_id = record_id
        self.additional_data = additional_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entrada a diccionario"""
        entry = {
            'id': self.id,
            'uuid': self.uuid,
            'session': self.session,
            'action': self.action,
            'timestamp': self.timestamp,
        }
        
        if self.record_id:
            entry['record_id'] = self.record_id
        
        if self.additional_data:
            entry['additional_data'] = json.dumps(self.additional_data, default=str)
        
        return entry


class CorporateDataRecord:
    """Representa un registro de CorporateData"""
    
    DEFAULT_FIELDS = {
        'cp': '',
        'CUIT': '',
        'domicilio': '',
        'idreq': '',
        'idSeq': '',
        'localidad': '',
        'provincia': '',
        'sede': '',
        'seqID': '',
        'telefono': '',
        'web': ''
    }
    
    def __init__(self, record_id: str, data: Optional[Dict[str, Any]] = None):
        self.id = record_id
        self.data = data if data else {}
    
    def update(self, new_data: Dict[str, Any]) -> 'CorporateDataRecord':
        """Actualiza el registro con nuevos datos"""
        self.data.update(new_data)
        return self
    
    def ensure_defaults(self):
        """Asegura que todos los campos por defecto existan"""
        for field, default_value in self.DEFAULT_FIELDS.items():
            if field not in self.data:
                self.data[field] = default_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el registro a diccionario completo"""
        result = {'id': self.id}
        result.update(self.data)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorporateDataRecord':
        """Crea un registro desde un diccionario"""
        record_id = data.get('id')
        record_data = {k: v for k, v in data.items() if k != 'id'}
        return cls(record_id, record_data)


class DynamoDBProxy:
    """Patrón Proxy para acceso a DynamoDB (Singleton)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DynamoDBProxy, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.dynamodb = boto3.resource('dynamodb')
        self.data_table = self.dynamodb.Table('CorporateData')
        self.log_table = self.dynamodb.Table('CorporateLog')
        self._initialized = True
    
    def log_action(self, log_entry: LogEntry) -> bool:
        """Registra una acción en la tabla CorporateLog"""
        try:
            entry_dict = log_entry.to_dict()
            entry_dict = DecimalConverter.to_decimal(entry_dict)
            self.log_table.put_item(Item=entry_dict)
            return True
        except Exception as e:
            logging.error(f"Error al registrar log: {e}")
            return False
    
    def get_record(self, record_id: str) -> Optional[CorporateDataRecord]:
        """Obtiene un registro de CorporateData"""
        try:
            response = self.data_table.get_item(Key={'id': record_id})
            
            if 'Item' in response:
                item = DecimalConverter.to_native(response['Item'])
                return CorporateDataRecord.from_dict(item)
            else:
                return None
        except Exception as e:
            logging.error(f"Error al obtener registro {record_id}: {e}")
            return None
    
    def list_records(self) -> List[CorporateDataRecord]:
        """Lista todos los registros de CorporateData"""
        try:
            items = []
            response = self.data_table.scan()
            items.extend(response.get('Items', []))
            
            # Manejo de paginación
            while 'LastEvaluatedKey' in response:
                response = self.data_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            records = []
            for item in items:
                native_item = DecimalConverter.to_native(item)
                records.append(CorporateDataRecord.from_dict(native_item))
            
            return records
        except Exception as e:
            logging.error(f"Error al listar registros: {e}")
            return []
    
    def save_record(self, record: CorporateDataRecord) -> bool:
        """Guarda un registro en CorporateData"""
        try:
            record_dict = record.to_dict()
            record_dict = DecimalConverter.to_decimal(record_dict)
            self.data_table.put_item(Item=record_dict)
            return True
        except Exception as e:
            logging.error(f"Error al guardar registro {record.id}: {e}")
            return False


class Observer(ABC):
    """Clase base abstracta para observers"""
    
    @abstractmethod
    def update(self, data: Dict[str, Any]):
        """Método a implementar por observers concretos"""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Verifica si el observer está activo"""
        pass
    
    @abstractmethod
    def close(self):
        """Cierra el observer"""
        pass


class ClientObserver(Observer):
    """Observer para clientes suscritos"""
    
    def __init__(self, client_socket: socket.socket, uuid: str):
        self.client_socket = client_socket
        self.uuid = uuid
        self._active = True
    
    def update(self, data: Dict[str, Any]):
        """Envía actualizaciones al cliente suscrito"""
        if not self._active:
            return
        
        try:
            message = json.dumps(data, default=str)
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error al notificar cliente {self.uuid}: {e}")
            self._active = False
    
    def is_active(self) -> bool:
        """Verifica si el observer está activo"""
        return self._active
    
    def close(self):
        """Cierra la conexión del observer"""
        self._active = False
        try:
            self.client_socket.close()
        except:
            pass


class ObserverManager:
    """Gestiona los observers suscritos (Patrón Observer + Singleton)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ObserverManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.observers: List[Observer] = []
        self._initialized = True
    
    def subscribe(self, observer: Observer):
        """Suscribe un nuevo observer"""
        with self._lock:
            self.observers.append(observer)
            if isinstance(observer, ClientObserver):
                logging.info(f"Cliente {observer.uuid} suscrito. Total: {len(self.observers)}")
    
    def unsubscribe(self, observer: Observer):
        """Desuscribe un observer"""
        with self._lock:
            if observer in self.observers:
                observer.close()
                self.observers.remove(observer)
                if isinstance(observer, ClientObserver):
                    logging.info(f"Cliente {observer.uuid} desuscrito. Total: {len(self.observers)}")
    
    def notify_all(self, data: Dict[str, Any]):
        """Notifica a todos los observers activos"""
        with self._lock:
            inactive_observers = []
            
            for observer in self.observers:
                if observer.is_active():
                    observer.update(data)
                else:
                    inactive_observers.append(observer)
            
            # Limpiar observers inactivos
            for observer in inactive_observers:
                self.unsubscribe(observer)


class RequestHandler:
    """Maneja las solicitudes de los clientes"""
    
    def __init__(self, proxy: DynamoDBProxy, observer_manager: ObserverManager, 
                 session_manager: SessionManager, verbose: bool = False):
        self.proxy = proxy
        self.observer_manager = observer_manager
        self.session_manager = session_manager
        self.verbose = verbose
    
    def log(self, message: str):
        """Registra mensaje si está en modo verbose"""
        if self.verbose:
            logging.debug(message)
    
    def handle_get(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción GET"""
        uuid = request.get('UUID', 'unknown')
        record_id = request.get('ID')
        
        if not record_id:
            return {"Error": "Falta el campo 'ID' para la acción 'get'"}
        
        self.log(f"GET solicitado - UUID: {uuid}, ID: {record_id}")
        
        # Registrar en log
        log_entry = LogEntry(uuid, session, 'get', record_id)
        self.proxy.log_action(log_entry)
        
        # Obtener registro
        record = self.proxy.get_record(record_id)
        
        if record:
            self.log(f"Registro {record_id} encontrado")
            return record.to_dict()
        else:
            self.log(f"Registro {record_id} no encontrado")
            return {"Error": f"No se encontró el registro con ID '{record_id}'"}
    
    def handle_list(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción LIST"""
        uuid = request.get('UUID', 'unknown')
        
        self.log(f"LIST solicitado - UUID: {uuid}")
        
        # Registrar en log
        log_entry = LogEntry(uuid, session, 'list')
        self.proxy.log_action(log_entry)
        
        # Obtener todos los registros
        records = self.proxy.list_records()
        
        if records:
            self.log(f"Se encontraron {len(records)} registros")
            records_dict = [record.to_dict() for record in records]
            return {"records": records_dict, "count": len(records)}
        else:
            self.log("No se encontraron registros")
            return {"records": [], "count": 0}
    
    def handle_set(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción SET"""
        uuid = request.get('UUID', 'unknown')
        record_id = request.get('ID')
        
        if not record_id:
            return {"Error": "Falta el campo 'ID' para la acción 'set'"}
        
        self.log(f"SET solicitado - UUID: {uuid}, ID: {record_id}")
        
        # Extraer datos del registro (excluir campos de control)
        data = {k: v for k, v in request.items() 
                if k not in ['UUID', 'ID', 'ACTION']}
        
        # Registrar en log
        log_entry = LogEntry(uuid, session, 'set', record_id, data)
        self.proxy.log_action(log_entry)
        
        # Obtener registro existente o crear nuevo
        record = self.proxy.get_record(record_id)
        
        if record:
            # Actualizar registro existente
            record.update(data)
        else:
            # Crear nuevo registro
            record = CorporateDataRecord(record_id, data)
            record.ensure_defaults()
        
        # Guardar registro
        if self.proxy.save_record(record):
            self.log(f"Registro {record_id} guardado exitosamente")
            
            # Notificar a todos los observers suscritos
            notification = {
                "action": "update",
                "record": record.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
            self.observer_manager.notify_all(notification)
            
            return record.to_dict()
        else:
            self.log(f"Error al guardar registro {record_id}")
            return {"Error": f"No se pudo guardar el registro con ID '{record_id}'"}
    
    def handle_subscribe(self, request: Dict[str, Any], session: str,
                        client_socket: socket.socket) -> Dict[str, Any]:
        """Maneja la acción SUBSCRIBE"""
        uuid = request.get('UUID', 'unknown')
        
        self.log(f"SUBSCRIBE solicitado - UUID: {uuid}")
        
        # Registrar en log
        log_entry = LogEntry(uuid, session, 'subscribe')
        self.proxy.log_action(log_entry)
        
        # Suscribir el cliente
        observer = ClientObserver(client_socket, uuid)
        self.observer_manager.subscribe(observer)
        
        return {
            "status": "subscribed",
            "uuid": uuid,
            "message": "Cliente suscrito exitosamente. Recibirá notificaciones de cambios."
        }
    
    def handle_unsubscribe(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción UNSUBSCRIBE"""
        uuid = request.get('UUID', 'unknown')
        
        self.log(f"UNSUBSCRIBE solicitado - UUID: {uuid}")
        logging.info(f"Cliente {uuid} solicitó desuscripción")
        
        # Registrar en log
        log_entry = LogEntry(uuid, session, 'unsubscribe')
        self.proxy.log_action(log_entry)
        
        # Buscar y desuscribir el cliente
        observer_to_remove = None
        with self.observer_manager._lock:
            for observer in self.observer_manager.observers:
                if isinstance(observer, ClientObserver) and observer.uuid == uuid:
                    observer_to_remove = observer
                    break

        if observer_to_remove:
            self.observer_manager.unsubscribe(observer_to_remove)
            return {
                "status": "unsubscribed",
                "uuid": uuid,
                "message": "Cliente desuscrito exitosamente."
            }
        
        return {
            "status": "not_found",
            "uuid": uuid,
            "message": "Cliente no encontrado en la lista de suscriptores."
        }



class ClientConnection:
    """Maneja una conexión individual de cliente"""
  
    def __init__(self, client_socket: socket.socket, address: tuple,
                 request_handler: RequestHandler, session: str):
        self.client_socket = client_socket
        self.address = address
        self.request_handler = request_handler
        self.session = session
        self.buffer_size = 8192
    
    def receive_request(self) -> Optional[Dict[str, Any]]:
        """Recibe y decodifica la solicitud del cliente"""
        try:
            data = b''
            while True:
                chunk = self.client_socket.recv(self.buffer_size)
                if not chunk:
                    break
                data += chunk
                
                # Intentar decodificar para ver si está completo
                try:
                    request = json.loads(data.decode('utf-8'))
                    return request
                except json.JSONDecodeError:
                    continue
            
            return None
        except Exception as e:
            logging.debug(f"Error al recibir datos: {e}")
            return None
    
    def send_response(self, response: Dict[str, Any]):
        """Envía respuesta al cliente"""
        try:
            response_json = json.dumps(response, default=str)
            self.client_socket.sendall(response_json.encode('utf-8'))
        except Exception as e:
            logging.debug(f"Error al enviar respuesta: {e}")
    
    def process(self):
        """Procesa la conexión del cliente"""
        self.request_handler.log(f"Nueva conexión desde {self.address} - Sesión: {self.session}")
        
        try:
            # Recibir solicitud
            request = self.receive_request()
            
            if not request:
                self.request_handler.log(f"Conexión cerrada por {self.address} sin datos")
                return
            
            action = request.get('ACTION', '').lower()
            self.request_handler.log(f"Acción recibida: {action}")
            
            # Procesar según la acción
            response = None
            keep_alive = False
            
            if action == 'get':
                response = self.request_handler.handle_get(request, self.session)
            elif action == 'list':
                response = self.request_handler.handle_list(request, self.session)
            elif action == 'set':
                response = self.request_handler.handle_set(request, self.session)
            elif action == 'subscribe':
                response = self.request_handler.handle_subscribe(
                    request, self.session, self.client_socket
                )
                keep_alive = True  # No cerrar socket para suscripciones
            elif action == 'unsubscribe':
                response = self.request_handler.handle_unsubscribe(request, self.session)
                # keep_alive se mantiene False para cerrar la conexión
            else:
                response = {"Error": f"Acción desconocida: {action}"}
            
            # Enviar respuesta
            if response:
                self.send_response(response)
            
            # Si es suscripción, seguir escuchando por si llega unsubscribe
            if keep_alive:
                self.listen_for_unsubscribe()
            else:
                self.close()
        
        except json.JSONDecodeError as e:
            self.request_handler.log(f"Error al decodificar JSON: {e}")
            self.send_response({"Error": "JSON inválido"})
            self.close()
        
        except Exception as e:
            self.request_handler.log(f"Error al procesar cliente: {e}")
            self.send_response({"Error": f"Error en el servidor: {str(e)}"})
            self.close()
    
    def close(self):
        """Cierra la conexión del cliente"""
        try:
            self.client_socket.close()
            self.request_handler.log(f"Conexión cerrada con {self.address}")
        except:
            pass
    
    def listen_for_unsubscribe(self):
        """Escucha por mensajes adicionales del cliente suscrito (principalmente UNSUBSCRIBE)"""
        self.request_handler.log(f"Manteniendo conexión abierta para {self.address}")
        
        try:
            # Configurar timeout para no bloquear indefinidamente
            self.client_socket.settimeout(1.0)
            data = b''
            
            while True:
                try:
                    # Intentar recibir datos
                    chunk = self.client_socket.recv(self.buffer_size)
                    
                    if not chunk:
                        # Socket cerrado por el cliente (recv retorna b'' cuando se cierra)
                        self.request_handler.log(f"Cliente {self.address} cerró la conexión")
                        break
                    
                    data += chunk
                    
                    # Intentar decodificar JSON
                    try:
                        request = json.loads(data.decode('utf-8'))
                        action = request.get('ACTION', '').lower()
                        self.request_handler.log(f"Acción recibida en suscripción: {action}")
                        
                        if action == 'unsubscribe':
                            # Procesar unsubscribe
                            response = self.request_handler.handle_unsubscribe(request, self.session)
                            self.send_response(response)
                            break
                        else:
                            # Acción no permitida en estado suscrito
                            error_response = {"Error": f"Acción '{action}' no permitida en estado suscrito"}
                            self.send_response(error_response)
                            # Resetear buffer
                            data = b''
                    except json.JSONDecodeError:
                        # JSON incompleto, seguir acumulando
                        continue
                
                except socket.timeout:
                    # Timeout es normal, seguir esperando
                    continue
                except ConnectionResetError:
                    self.request_handler.log(f"Cliente {self.address} resetó la conexión")
                    break
                except Exception as e:
                    self.request_handler.log(f"Error al escuchar cliente suscrito: {e}")
                    break
        
        finally:
            self.close()


class SingletonProxyObserverServer:
    """Servidor principal que integra todos los componentes"""
    
    def __init__(self, port: int = 8080, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.running = False
        
        # Componentes principales
        self.proxy = DynamoDBProxy()
        self.observer_manager = ObserverManager()
        self.session_manager = SessionManager()
        self.request_handler = RequestHandler(
            self.proxy, self.observer_manager, 
            self.session_manager, verbose
        )
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Maneja una conexión de cliente en un thread separado"""
        session = self.session_manager.generate_id()
        connection = ClientConnection(
            client_socket, address, 
            self.request_handler, session
        )
        connection.process()
    
    def start(self):
        """Inicia el servidor"""
        self.running = True
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Stream = TCP
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            
            logging.info("="*70)
            logging.info("SingletonProxyObserverTPFI - Servidor iniciado (OOP)")
            logging.info("="*70)
            logging.info(f"Escuchando en puerto: {self.port}")
            logging.info(f"Modo verbose: {'Activado' if self.verbose else 'Desactivado'}")
            logging.info(f"Tablas DynamoDB: CorporateData, CorporateLog")
            logging.info("="*70)
            logging.info("Esperando conexiones...")
            
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    
                    # Crear thread para manejar el cliente
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                
                except KeyboardInterrupt:
                    logging.info("Deteniendo servidor...")
                    break
                except Exception as e:
                    if self.running:
                        logging.error(f"Error al aceptar conexión: {e}")
        
        finally:
            self.running = False
            server_socket.close()
            logging.info("Servidor detenido.")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Servidor Proxy con patrones Singleton y Observer para CorporateData (OOP)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('start', nargs='?', help='Inicia el servidor si se incluye este argumento')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Puerto en el que escuchará el servidor (default: 8080)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Modo verbose, muestra información detallada')
    
    args = parser.parse_args()
    
    if args.start != 'start':
        print("""
Uso del servidor SingletonProxyObserver:

  python SingletonProxyObserver.py start [opciones]

Opciones:
  -p, --port <número>    Puerto en el que escuchará el servidor (default: 8080)
  -v, --verbose          Activa el modo verbose (muestra logs detallados)

Ejemplos:
  python SingletonProxyObserver.py start
  python SingletonProxyObserver.py start -p 9090 -v

Si no se incluye 'start', el servidor no se inicia y se muestra esta ayuda.
""")
        sys.exit(0)
    
    # logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Crear y arrancar servidor
    server = SingletonProxyObserverServer(port=args.port, verbose=args.verbose)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logging.info("Servidor detenido por el usuario.")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Error fatal: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
