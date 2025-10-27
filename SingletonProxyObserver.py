#!/usr/bin/env python3
"""
SingletonProxyObserverTPFI.py
Servidor Proxy con patrón Singleton y Observer para gestión de CorporateData
Ingeniería de Software II - UADER-FCyT-IS2
"""

import socket
import json
import argparse
import sys
import threading
import boto3
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from boto3.dynamodb.conditions import Key
import uuid as uuid_lib

class DynamoDBProxy:
    """Patrón Proxy para acceso a DynamoDB"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DynamoDBProxy, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el proxy si no ha sido inicializado antes"""
        if self._initialized:
            return
        
        self.dynamodb = boto3.resource('dynamodb')
        self.data_table = self.dynamodb.Table('CorporateData')
        self.log_table = self.dynamodb.Table('CorporateLog')
        self.session_counter = 0
        self._initialized = True
    
    def _generate_session_id(self) -> str:
        """Genera un ID de sesión único"""
        with self._lock:
            self.session_counter += 1
            return f"SESSION-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.session_counter}"
    
    # DynamoDB requiere que todos los números sean Decimal, de eso se encargan las siguientes 2 funciones
    def _decimal_to_native(self, obj):
        """Convierte objetos Decimal a tipos nativos de Python"""
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: self._decimal_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_native(i) for i in obj]
        return obj
    
    def _native_to_decimal(self, obj):
        """Convierte números nativos a Decimal para DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, int):
            return Decimal(obj)
        elif isinstance(obj, dict):
            return {k: self._native_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._native_to_decimal(i) for i in obj]
        return obj
    
    def log_action(self, uuid: str, session: str, action: str, 
                   record_id: Optional[str] = None, additional_data: Optional[Dict] = None):
        """
        Registra una acción en la tabla CorporateLog
        
        Args:
            uuid: UUID del cliente
            session: ID de sesión
            action: Acción realizada
            record_id: ID del registro (opcional)
            additional_data: Datos adicionales (opcional)
        """
        try:
            log_entry = {
                'id': str(uuid_lib.uuid4()),
                'uuid': uuid,
                'session': session,
                'action': action,
                'timestamp': datetime.now().isoformat(),
            }
            
            if record_id:
                log_entry['record_id'] = record_id
            
            if additional_data:
                log_entry['additional_data'] = json.dumps(additional_data, default=str)
            
            log_entry = self._native_to_decimal(log_entry)
            self.log_table.put_item(Item=log_entry)
            
            return True
        except Exception as e:
            print(f"Error al registrar log: {e}", file=sys.stderr)
            return False
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un registro de CorporateData
        
        Args:
            record_id: ID del registro a obtener
            
        Returns:
            Diccionario con el registro o None si no existe
        """
        try:
            response = self.data_table.get_item(Key={'id': record_id})
            
            if 'Item' in response:
                return self._decimal_to_native(response['Item'])
            else:
                return None
        except Exception as e:
            print(f"Error al obtener registro {record_id}: {e}", file=sys.stderr)
            return None
    
    def list_records(self) -> List[Dict[str, Any]]:
        """
        Lista todos los registros de CorporateData
        
        Returns:
            Lista de diccionarios con todos los registros
        """
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
            
            return [self._decimal_to_native(item) for item in items]
        except Exception as e:
            print(f"Error al listar registros: {e}", file=sys.stderr)
            return []
    
    def set_record(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crea o actualiza un registro en CorporateData
        
        Args:
            record_id: ID del registro
            data: Datos del registro
            
        Returns:
            Registro actualizado o None si hubo error
        """
        try:
            # Obtener registro existente si existe
            existing_record = self.get_record(record_id)
            
            if existing_record:
                # Actualizar solo los campos proporcionados
                updated_record = existing_record.copy()
                updated_record.update(data)
            else:
                # Crear nuevo registro con los datos proporcionados
                updated_record = {'id': record_id}
                updated_record.update(data)
                
                # Inicializar campos no proporcionados como vacíos
                default_fields = [
                    'cp', 'CUIT', 'domicilio', 'idreq', 'idSeq', 
                    'localidad', 'provincia', 'sede', 'seqID', 'telefono', 'web'
                ]
                for field in default_fields:
                    if field not in updated_record:
                        updated_record[field] = ''
            
            # Convertir a Decimal para DynamoDB
            updated_record = self._native_to_decimal(updated_record)
            
            # Guardar en DynamoDB
            self.data_table.put_item(Item=updated_record)
            
            # Retornar en formato nativo
            return self._decimal_to_native(updated_record)
        except Exception as e:
            print(f"Error al actualizar registro {record_id}: {e}", file=sys.stderr)
            return None


class Observer:
    """Clase base para observers"""
    
    def update(self, data: Dict[str, Any]):
        """Método a implementar por observers concretos"""
        pass


class ClientObserver(Observer):
    """Observer para clientes suscritos"""
    
    def __init__(self, client_socket: socket.socket, uuid: str):
        self.client_socket = client_socket
        self.uuid = uuid
        self.active = True
    
    def update(self, data: Dict[str, Any]):
        """Envía actualizaciones al cliente suscrito"""
        if not self.active:
            return
        
        try:
            message = json.dumps(data, default=str)
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error al notificar cliente {self.uuid}: {e}", file=sys.stderr)
            self.active = False
    
    def close(self):
        """Cierra la conexión del observer"""
        self.active = False
        try:
            self.client_socket.close()
        except:
            pass


class ObserverManager:
    """Gestiona los observers suscritos (Patrón Observer)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ObserverManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el gestor si no ha sido inicializado antes"""
        if self._initialized:
            return
        
        self.observers: List[ClientObserver] = []
        self._initialized = True
    
    def subscribe(self, client_socket: socket.socket, uuid: str) -> ClientObserver:
        """
        Suscribe un nuevo observer
        
        Args:
            client_socket: Socket del cliente
            uuid: UUID del cliente
            
        Returns:
            Observer creado
        """
        with self._lock:
            observer = ClientObserver(client_socket, uuid)
            self.observers.append(observer)
            print(f"Cliente {uuid} suscrito. Total suscritos: {len(self.observers)}")
            return observer
    
    def unsubscribe(self, observer: ClientObserver):
        """
        Desuscribe un observer
        
        Args:
            observer: Observer a desuscribir
        """
        with self._lock:
            if observer in self.observers:
                observer.close()
                self.observers.remove(observer)
                print(f"Cliente {observer.uuid} desuscrito. Total suscritos: {len(self.observers)}")
    
    def notify_all(self, data: Dict[str, Any]):
        """
        Notifica a todos los observers activos
        
        Args:
            data: Datos a enviar
        """
        with self._lock:
            inactive_observers = []
            
            for observer in self.observers:
                if observer.active:
                    observer.update(data)
                else:
                    inactive_observers.append(observer)
            
            # Limpiar observers inactivos
            for observer in inactive_observers:
                self.unsubscribe(observer)


class SingletonProxyObserverServer:
    """Servidor principal que integra Singleton, Proxy y Observer"""
    
    def __init__(self, port: int = 8080, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.proxy = DynamoDBProxy()
        self.observer_manager = ObserverManager()
        self.running = False
    
    def log(self, message: str):
        """Imprime mensaje si está en modo verbose"""
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] {message}")
    
    def handle_get(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción GET"""
        uuid = request.get('UUID', 'unknown')
        record_id = request.get('ID')
        
        if not record_id:
            return {"Error": "Falta el campo 'ID' para la acción 'get'"}
        
        self.log(f"GET solicitado - UUID: {uuid}, ID: {record_id}")
        
        # Registrar en log
        self.proxy.log_action(uuid, session, 'get', record_id)
        
        # Obtener registro
        record = self.proxy.get_record(record_id)
        
        if record:
            self.log(f"Registro {record_id} encontrado")
            return record
        else:
            self.log(f"Registro {record_id} no encontrado")
            return {"Error": f"No se encontró el registro con ID '{record_id}'"}
    
    def handle_list(self, request: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Maneja la acción LIST"""
        uuid = request.get('UUID', 'unknown')
        
        self.log(f"LIST solicitado - UUID: {uuid}")
        
        # Registrar en log
        self.proxy.log_action(uuid, session, 'list')
        
        # Obtener todos los registros
        records = self.proxy.list_records()
        
        if records:
            self.log(f"Se encontraron {len(records)} registros")
            return {"records": records, "count": len(records)}
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
        self.proxy.log_action(uuid, session, 'set', record_id, data)
        
        # Actualizar registro
        updated_record = self.proxy.set_record(record_id, data)
        
        if updated_record:
            self.log(f"Registro {record_id} actualizado exitosamente")
            
            # Notificar a todos los observers suscritos
            notification = {
                "action": "update",
                "record": updated_record,
                "timestamp": datetime.now().isoformat()
            }
            self.observer_manager.notify_all(notification)
            
            return updated_record
        else:
            self.log(f"Error al actualizar registro {record_id}")
            return {"Error": f"No se pudo actualizar el registro con ID '{record_id}'"}
    
    def handle_subscribe(self, request: Dict[str, Any], session: str, 
                         client_socket: socket.socket) -> Dict[str, Any]:
        """Maneja la acción SUBSCRIBE"""
        uuid = request.get('UUID', 'unknown')
        
        self.log(f"SUBSCRIBE solicitado - UUID: {uuid}")
        
        # Registrar en log
        self.proxy.log_action(uuid, session, 'subscribe')
        
        # Suscribir el cliente
        observer = self.observer_manager.subscribe(client_socket, uuid)
        
        return {
            "status": "subscribed",
            "uuid": uuid,
            "message": "Cliente suscrito exitosamente. Recibirá notificaciones de cambios."
        }
    
    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Maneja la conexión de un cliente"""
        session = self.proxy._generate_session_id()
        self.log(f"Nueva conexión desde {address} - Sesión: {session}")
        
        try:
            # Recibir datos
            data = b''
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                data += chunk
                
                # Intentar decodificar para ver si está completo
                try:
                    request = json.loads(data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue
            
            if not data:
                self.log(f"Conexión cerrada por {address} sin datos")
                return
            
            request = json.loads(data.decode('utf-8'))
            action = request.get('ACTION', '').lower()
            
            self.log(f"Acción recibida: {action}")
            
            # Procesar según la acción
            if action == 'get':
                response = self.handle_get(request, session)
                client_socket.sendall(json.dumps(response, default=str).encode('utf-8'))
                
            elif action == 'list':
                response = self.handle_list(request, session)
                client_socket.sendall(json.dumps(response, default=str).encode('utf-8'))
                
            elif action == 'set':
                response = self.handle_set(request, session)
                client_socket.sendall(json.dumps(response, default=str).encode('utf-8'))
                
            elif action == 'subscribe':
                response = self.handle_subscribe(request, session, client_socket)
                client_socket.sendall(json.dumps(response, default=str).encode('utf-8'))
                # No cerrar el socket, se mantiene abierto para notificaciones
                return
                
            else:
                response = {"Error": f"Acción desconocida: {action}"}
                client_socket.sendall(json.dumps(response, default=str).encode('utf-8'))
        
        except json.JSONDecodeError as e:
            self.log(f"Error al decodificar JSON: {e}")
            response = {"Error": "JSON inválido"}
            try:
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            except:
                pass
        
        except Exception as e:
            self.log(f"Error al manejar cliente: {e}")
            response = {"Error": f"Error en el servidor: {str(e)}"}
            try:
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            except:
                pass
        
        finally:
            # Solo cerrar si no es una suscripción
            if action != 'subscribe':
                try:
                    client_socket.close()
                    self.log(f"Conexión cerrada con {address}")
                except:
                    pass
    
    def start(self):
        """Inicia el servidor"""
        self.running = True
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            
            print(f"{'='*70}")
            print(f"SingletonProxyObserverTPFI - Servidor iniciado")
            print(f"{'='*70}")
            print(f"Escuchando en puerto: {self.port}")
            print(f"Modo verbose: {'Activado' if self.verbose else 'Desactivado'}")
            print(f"Tablas DynamoDB: CorporateData, CorporateLog")
            print(f"{'='*70}")
            print("Esperando conexiones...")
            print()
            
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
                    print("\nDeteniendo servidor...")
                    break
                except Exception as e:
                    if self.running:
                        print(f"Error al aceptar conexión: {e}", file=sys.stderr)
        
        finally:
            self.running = False
            server_socket.close()
            print("Servidor detenido.")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Servidor Proxy con patrones Singleton y Observer para CorporateData',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Puerto en el que escuchará el servidor (default: 8080)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Modo verbose, muestra información detallada')
    
    args = parser.parse_args()
    
    # Crear y arrancar servidor
    server = SingletonProxyObserverServer(port=args.port, verbose=args.verbose)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nServidor detenido por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"Error fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
