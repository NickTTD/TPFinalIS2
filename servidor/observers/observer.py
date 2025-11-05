#!/usr/bin/env python3
"""
observers/observer.py - Clase base abstracta Observer
Patrón Observer
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


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