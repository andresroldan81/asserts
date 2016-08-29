# -*- coding: utf-8 -*-

"""Modulo para verificación del protocolo SMTP.

Este modulo permite verificar vulnerabilidades propias de SMTP como:

    * Comando VRFY activo,

Alexander Botero - Redexel
"""

# standard imports
import logging
import smtplib

# 3rd party imports
# none

# local imports
# none


def has_vrfy(ip, port):

    server = smtplib.SMTP(ip, port)
    vrfy = server.verify('Admin')
    if str('250') in vrfy:
        logging.info('SMTP "VRFY" method, Details=%s, %s',
                     ip + ':' + str(port), 'OPEN')
    else:
        logging.info('SMTP "VRFY" method, Details=%s, %s',
                     ip + ':' + str(port), 'CLOSE')

    server.quit()
