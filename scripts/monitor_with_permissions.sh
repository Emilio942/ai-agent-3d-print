#!/bin/bash
"""
3D-Drucker Monitoring mit temporären Berechtigungen

Dieses Script löst temporär das Berechtigungsproblem für USB-Serial-Kommunikation.
"""

echo "🔐 Setze temporäre Berechtigungen für USB-Serial-Zugriff..."

# Prüfe ob /dev/ttyUSB0 existiert
if [ -e "/dev/ttyUSB0" ]; then
    echo "✅ 3D-Drucker gefunden auf /dev/ttyUSB0"
    
    # Setze temporäre Berechtigungen
    echo "🔧 Setze Berechtigungen..."
    sudo chmod 666 /dev/ttyUSB0
    
    if [ $? -eq 0 ]; then
        echo "✅ Berechtigungen gesetzt"
        echo "🚀 Starte 3D-Drucker Überwachung..."
        
        # Wechsle ins Projektverzeichnis und starte das Python-Script
        cd "$(dirname "$0")/.."
        python scripts/monitor_printer.py
    else
        echo "❌ Fehler beim Setzen der Berechtigungen"
        exit 1
    fi
else
    echo "❌ Kein 3D-Drucker auf /dev/ttyUSB0 gefunden"
    echo "🔍 Suche nach anderen USB-Serial-Geräten..."
    ls -la /dev/ttyUSB* 2>/dev/null || echo "Keine USB-Serial-Geräte gefunden"
    exit 1
fi
