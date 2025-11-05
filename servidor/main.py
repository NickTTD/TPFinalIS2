#!/usr/bin/env python3
"""
main.py - Punto de entrada
SingletonProxyObserverTPFI - Servidor Proxy con patrones Singleton y Observer
Ingeniería de Software II - UADER-FCyT-IS2
"""

import argparse
import logging
import sys

from utils import configure_logging
from server import SingletonProxyObserverServer


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Servidor Proxy con patrones Singleton y Observer para CorporateData',
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

  python main.py start [opciones]

Opciones:
  -p, --port <número>    Puerto en el que escuchará el servidor (default: 8080)
  -v, --verbose          Activa el modo verbose (muestra logs detallados)

Ejemplos:
  python main.py start
  python main.py start -p 9090 -v

Si no se incluye 'start', el servidor no se inicia y se muestra esta ayuda.
""")
        sys.exit(0)
    
    # Configurar logging
    configure_logging(args.verbose)
    
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