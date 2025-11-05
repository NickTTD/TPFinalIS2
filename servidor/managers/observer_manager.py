#!/usr/bin/env python3
"""
managers/observer_manager.py - Gestor de observers
Patrón Observer + Singleton
"""

import logging
import threading
from typing import Any, Dict, List

from observers import Observer, ClientObserver


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