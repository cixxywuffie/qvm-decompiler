---
name: qvm-analysis
description: Analyze Quake III mod QVM bytecode from a supplied PK3 using this project's decompiler. Use when investigating modules, instructions, strings, calls, game behavior, or server-client flows without the original source code.
---

# Analisis de QVM de mods de Quake III

Usa esta skill para investigar un comportamiento concreto de un mod a partir
de su PK3. Utiliza el decompilador de este proyecto como herramienta principal.
No presentes el resultado como codigo C original o completamente reconstruido.

## Preparacion

1. Solicita al usuario que añada el PK3 del mod al proyecto o indique su ruta.
   Si no esta disponible, detente y solicitalo. Pide tambien la version del mod
   y el comportamiento que se desea investigar, si no se conocen.
2. Identifica el paquete y calcula su SHA-256. Si hay varios PK3 o versiones,
   pregunta cual se debe analizar; no supongas que todos tienen los mismos QVM.
3. Trata el PK3 como ZIP y lista sus entradas. Identifica los QVM disponibles:
   normalmente `vm\qagame.qvm` es el modulo del servidor, `vm\cgame.qvm` el
   del cliente y `vm\ui.qvm` la interfaz, pero verifica los archivos presentes.
   Las entradas ZIP pueden usar `/` como separador.
4. No modifiques el PK3. Lee las entradas directamente cuando sea posible; si
   necesitas extraerlas, extrae solo los archivos seleccionados a una carpeta
   de trabajo, sin sobrescribir archivos existentes ni confiar en rutas ZIP.

Ejemplo desde la raiz del proyecto, en PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\ruta\mod.pk3'
@'
from pathlib import Path
from zipfile import ZipFile

path = Path(r"C:\ruta\mod.pk3")
with ZipFile(path) as archive:
    for info in archive.infolist():
        if info.filename.lower().endswith(".qvm"):
            print(f"{info.filename} ({info.file_size} bytes)")
'@ | python -
```

## Analisis

1. Analiza el modulo pertinente con `qvm_decompiler.qvm.QvmFile.from_bytes`.
   Comprueba la cabecera, el numero de instrucciones y
   `trailing_code_bytes`; comunica cualquier error o dato sin interpretar.
   Para usar el codigo sin instalar el paquete, añade `src` a `sys.path`:

   ```powershell
   @'
   import sys
   from zipfile import ZipFile

   sys.path.insert(0, "src")
   from qvm_decompiler.qvm import QvmFile

   with ZipFile(r"C:\ruta\mod.pk3") as archive:
       raw = archive.read("vm/qagame.qvm")  # Usa la entrada realmente presente.
   qvm = QvmFile.from_bytes(raw, "vm/qagame.qvm")
   print(qvm.header)
   print("Instrucciones:", len(qvm.instructions))
   print("Bytes finales sin decodificar:", qvm.trailing_code_bytes)
   '@ | python -
   ```

2. Usa `qvm_decompiler.formatter.disassemble(qvm)` para consultar el bytecode
   y `pseudocode(qvm)` como apoyo orientativo. Si se ha extraido un QVM,
   tambien puedes usar `python -m qvm_decompiler` con `--mode disasm` o
   `--mode pseudocode`, asegurando que `src` este en `PYTHONPATH` o que el
   paquete este instalado.
3. Busca cadenas relevantes en los segmentos de datos y literales del archivo
   original. Usa `header.data_offset`, `header.data_length` y
   `header.lit_length`; el objeto `QvmFile` no conserva esos bytes.
   Examina referencias directas y tablas de punteros, no solo texto cercano.
   Un valor numerico coincidente no demuestra por si solo una referencia.
4. Sigue instrucciones, argumentos, condiciones, saltos y llamadas tanto
   hacia sus destinos como hacia sus llamadores. Trata las llamadas indirectas
   y saltos calculados como posibles rutas adicionales; una busqueda de
   llamadas directas no demuestra que sea la unica ruta. Interpreta syscalls
   con la ABI del motor y modulo correspondientes, verificando la version.
5. Si el flujo cruza servidor, cliente o interfaz, analiza los modulos
   correspondientes y relaciona mensajes, argumentos y condiciones. No
   deduzcas que un formato o comportamiento de un mod se aplica a otro.
6. Contrasta las hipotesis con archivos producidos, registros o pruebas en
   ejecucion cuando esten disponibles. Indica los casos y modalidades que
   siguen sin comprobar.

## Direcciones y limites

- `qvm.instructions[index]` se indexa por **numero de instruccion**;
  `Instruction.address` es el **offset en bytes relativo al segmento de
  codigo**. El offset dentro del archivo es `header.code_offset + address`.
- En el bytecode QVM estandar, los destinos directos de salto y de llamadas
  a funciones se interpretan como indices de instruccion, no como offsets
  en bytes. Verifica cada operando en su contexto: `const` tambien puede
  representar datos, valores numericos o una syscall.
- Las direcciones de cadenas en memoria de datos no son offsets de archivo
  ni direcciones de codigo. Distingue los tres espacios al documentar pruebas.
- El pseudocodigo es experimental: no recupera nombres, tipos ni estructuras
  originales, y no reconstruye completamente el flujo de control. Puede perder
  el estado de pila entre ramas, dejar llamadas sin resolver y mostrar limites
  de funcion o retornos de forma incorrecta. Confirma los resultados en el
  bytecode antes de concluir.
- Si existen cadenas residuales o coincidencias con datos arbitrarios, no las
  atribuyas a una funcion sin verificar las referencias y su uso.

## Resultado

Presenta los hallazgos con el nombre y hash del PK3, modulo, version conocida
e identificadores verificables: indice de instruccion y offset de bytecode.
Separa comportamiento confirmado por instrucciones, observaciones de
ejecucion e hipotesis pendientes. Explica las rutas no analizadas y no afirmes
que el codigo C original se ha recuperado. Genera documentos o artefactos solo
si el usuario los solicita.
