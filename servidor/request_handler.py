"""
request_handler.py - Gestor de solicitudes
Procesa las acciones del cliente
"""

import logging
import socket
from datetime import datetime
from typing import Any, Dict

from db import DynamoDBProxy, CorporateDataRecord, LogEntry
from managers import ObserverManager, SessionManager
from observers import ClientObserver


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