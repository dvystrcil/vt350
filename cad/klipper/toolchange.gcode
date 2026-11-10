; VT350 tool changes through MadMax's macros in Kalico batch mode (vt350#116 AC4): a pickup and a dock for each head.
; Run by cad/klipper/test_kalico_batch.py; its timeline is committed as toolchange_timeline.jsonl.
G28
G90
G1 X175 Y175 Z10 F6000
; both heads docked: the toolchanger starts with no tool (toolchanger.cfg initialize_gcode)
INITIALIZE_TOOLCHANGER
; pick up T0 (left)
T0
; dock T0, pick up T1 (right)
T1
; dock T1
UNSELECT_TOOL
