#!/bin/bash

# depuración
set -x

# salir al primer error
set -e

# importar entorno (ANSIBLE_*)
source $(git rev-parse --show-toplevel)/env.sh

# Probando modulo de root
ansible container -m ping 

# Probando credenciales no privilegiados y de root
ansible container -m shell -a "id"
ansible container -m shell -a "id" -b
