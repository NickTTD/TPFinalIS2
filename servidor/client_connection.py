#!/usr/bin/env python3
"""
client_connection.py - Gestor de conexión de cliente
Maneja una conexión individual de cliente
"""

import json
import logging
import socket
from typing import Any, Dict, Optional

from request_handler import RequestHandler


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
                        # Socket cerrado por el cliente
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