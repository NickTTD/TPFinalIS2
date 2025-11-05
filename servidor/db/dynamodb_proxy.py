"""
db/dynamodb_proxy.py - Proxy para acceso a DynamoDB
Patrón Proxy + Singleton
"""

import logging
import threading
from typing import List, Optional

import boto3

from .models import CorporateDataRecord, LogEntry
from utils import DecimalConverter


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