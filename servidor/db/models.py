#!/usr/bin/env python3
"""
db/models.py - Modelos de datos
LogEntry y CorporateDataRecord
"""

import json
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Dict, Optional


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