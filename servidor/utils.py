#!/usr/bin/env python3
"""
utils.py - Utilidades generales
Conversión de tipos y configuración de logging
"""

import logging
from decimal import Decimal
from typing import Any


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


def configure_logging(verbose: bool = False):
    """Configura el logging de la aplicación"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )