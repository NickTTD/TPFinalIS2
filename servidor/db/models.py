#!/usr/bin/env python3
"""
db/models.py - Modelos de datos
LogEntry y CorporateDataRecord
"""

import json
import uuid as uuid_lib
import platform
from datetime import datetime
from typing import Any, Dict, Optional

# Importar SessionManager para obtener cpu_uuid
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from managers.session_manager import SessionManager


class LogEntry:
    """Representa una entrada de log con información de CPU"""
    
    def __init__(self, uuid: str, session: str, action: str,
                 record_id: Optional[str] = None, 
                 additional_data: Optional[Dict] = None):
        self.id = str(uuid_lib.uuid4())
        self.uuid = uuid
        self.session = session
        self.action = action
        # Usar timestamp UTC para consistencia global
        self.timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.record_id = record_id
        self.additional_data = additional_data
        # Obtener datos de CPU desde SessionManager
        self.cpu_data = self._get_cpu_data()
    
    def _get_cpu_data(self) -> Dict[str, Any]:
        """Obtiene información de la CPU desde SessionManager"""
        session_manager = SessionManager()
        cpu_info = session_manager.get_cpu_info()
        return cpu_info
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Retorna la información de CPU almacenada"""
        return self.cpu_data.copy()
    
    def get_cpu_uuid(self) -> str:
        """Retorna el UUID único de la CPU"""
        return self.cpu_data['cpu_uuid']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entrada a diccionario incluyendo datos de CPU"""
        entry = {
            'id': self.id,
            'uuid': self.uuid,
            'session': self.session,
            'action': self.action,
            'timestamp': self.timestamp,
        }
        
        if self.record_id:
            entry['record_id'] = self.record_id
        
        # Agregar datos de CPU
        entry['cpu_uuid'] = self.cpu_data['cpu_uuid']
        entry['processor'] = self.cpu_data['processor']
        entry['machine'] = self.cpu_data['machine']
        entry['system'] = self.cpu_data['system']
        
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