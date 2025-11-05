Ziel: „Bild/Text → hübsche Plastik-Katze → G-Code → echter Druck“
A) Schon erledigt (relevant für das Ziel)

End-to-End Pipeline vorhanden: Text/Bild → CAD → Slicer → Printer (Mock), Testlauf („2 cm Würfel“) ok.

KI-Parsing & Orchestrierung: AI Research Agent + ParentAgent funktionieren.

Geometrie-Tooling: Trimesh, numpy-stl, manifold3d sind im Stack.

API/Backend: FastAPI + WebSockets vorhanden; viele Endpunkte nutzbar.

Image→3D: Prototyp vorhanden (z. B. test_circle.png → STL).
Ich vermute: Das taugt noch nicht für komplexe organische Formen wie Katzen.

B) Was noch fehlt – exakt für „hübsche“ Katzenfigur
1) 3D-Modellqualität (Bild/Text → druckbares Katzen-Mesh)

Single-Bild-zu-3D Modul integrieren (für Foto → 3D-Katze).

Anbindung als eigener Service/Agent (/api/convert/image-to-3d/animal), Rückgabe: geschlossene, wasserdichte Meshes.

Ich vermute: Der aktuelle Image→3D-Pfad macht nur primitive Geometrien → Upgrade nötig.

Text-zu-3D Pfad (für „Katze in Sitzpose“) mit Varianten (3–5 Entwürfe).

Mesh-Aufbereitung automatisieren (Pipeline):

Loch-Schluss, Non-Manifold-Fix, Normals reparieren (manifold3d/Trimesh).

Verwölbung glätten (Laplacian-Smoothing), Vereinfachen (Decimate) – ohne Details (Ohren, Schnurrhaare) zu zerstören.

Skalierung in mm, Ausrichtung (Bauch auf Bett), Z-Versatz 0.

Druckbarkeits-Checks: minimale Wanddicke ≥ 2× Düsendurchmesser, minimale Details ≥ 3× Layerhöhe.

„Hübsch“-Kriterium:

Qualitäts-Bewertung (z. B. Schönheits-Score mit Bild-Ähnlichkeit + Silhouetten-Klarheit).

Top-Variante automatisch wählen (oder Top-3 im UI anzeigen).

Ich vermute: So ein Score fehlt noch → hinzufügen.

2) Slicing & Material

Organische Form-Profile im Slicer:

Layerhöhe 0,12–0,2 mm; niedrige Beschleunigung für feine Ohren; Seam-Position nach hinten; Monotonic Top-Layer falls verfügbar.

Support-Strategie für Ohren/Schwanz (Kontakt-Z-Abstand, Support-Dichte 10–12 %).

Hohl + Abflusslöcher (optional) zur Material- und Zeitersparnis (z. B. 2–3 mm Wand, 2–3 Löcher Ø 3–5 mm an Unterseite).

Mehrfarbig (optional):

Single-Nozzle: Farbwechsel-G-Code (M600) an Layer-Marken; UI-Prompt zum Filamentwechsel.

Multi-Material (falls vorhanden): Farben zu STL-Teilen oder Farb-Zonen mappen.

3) Drucker-Integration (echte Hardware)

Serielle Anbindung finalisieren (pyserial): Auto-Erkennung Port/BAUD, Handshake (M115), Profil laden (Bauvolumen, Düse, Temps).

Sicherheits-Checks: Thermistor-Lesung (M105), Endstops, Dry-Run ohne Heizen, Watchdog (Timeout/Abort).

Kalibrier-Jobs als Tasks:

First-Layer-Test (50×50-Patch), Flow-Kalibrierung, Retraction, Linear Advance (falls Firmware).

Speichern als Druckerprofil v1.

4) Web-UI (nur was fürs Ziel nötig ist)

Upload & Prompt-Maske: Bild hochladen oder Text eingeben; Auswahl „Sitzend | Stehend | Schlafend“.

3D-Vorschau mit Orientierung, Support-Vorschau, Zeit/Material-Schätzung.

Job-Kontrolle (WebSocket): Start/Stop/Pause, Fortschritt, Temperatur-Plot; M600-Dialog bei Farbwechsel.

5) Middleware & Stabilität

Middleware-Fix in api/main.py: richtige Reihenfolge (CORS → Security → Rate-Limit → Compression), Blocker für API-Tests entfernen.

Rate-Limit/Validierung: Dateigrößen-Limit für Bilder, Prompt-Länge, Timeouts für 3D-Generierung; Queue/Worker für lange Jobs.

6) Tests & Definition of Done

Golden-Run Tests:

tests/e2e/test_cat_text.py: „Katze, sitzend, 10 cm“ → wasserdichtes STL, Slicing < 90 s, G-Code generiert.

tests/e2e/test_cat_image.py: Foto → STL → G-Code → Mock-Druck OK.

Hardware-Smoke-Test:

Heizbett/Düse erreichen Ziel, Homing, 20×20 Kalibrier-Quadrat ohne Skipping.

Real-Print-Akzeptanz:

Katze 100 mm Höhe, Ohren sauber, kein Warp, <2 Stringing-Fäden, Zeit < 10 h (FDM, 0,2 mm).

Abbruch-Sicherheit: Pause/Abort ohne Hitzestau, Lüfter aus, Heizelemente sicher aus.

C) Minimaler Pfad zum Ziel (Prioritäten & Reihenfolge)

Sprint 1 — „Druckbares Katzen-Mesh“

Bild→3D-Modul integrieren (oder Text→3D-Variante), Export wasserdicht.

Mesh-Fix-Pipeline (manifold-fix, smooth, scale, orient).

Druckbarkeits-Checks (Wanddicke/Details) + Auto-Hollow optional.
DoD: POST /api/convert/cat liefert druckbares STL (prüfbar mit Trimesh: watertight=True).

Sprint 2 — „Slicing & Hardware“
4. Katzen-Slicer-Profil + Support-Preset.
5. Serielle Anbindung + Druckerprofil + Sicherheits-Checks.
6. Hardware-Smoke-Test (Kalibrier-Quadrat).
DoD: POST /api/print/cat startet echten Druck bis Layer 10 fehlerfrei.

Sprint 3 — „Hübsch & UX“
7. Varianten-Generator + Schönheits-Score → Top-Variante wählen.
8. UI: Upload/Prompt, 3D-Vorschau, Zeit/Material, Start/Pause/Abort.
9. Farbwechsel-Workflow (M600) optional.
DoD: Benutzer wählt Foto oder Text, sieht Vorschau, startet Druck; Ergebnis erfüllt Akzeptanzkriterien.

Sprint 4 — „Härtung & Tests“
10. Middleware-Fix + Rate-Limit + Queue.
11. E2E-Tests (Text/Bild), Hardware-Akzeptanzdruck, Dokumentation.
DoD: Alle Tests grün, ein realer „Katze 10 cm“-Druck dokumentiert.

D) Konkrete Aufgabenliste (zum Abhaken)

 image_to_3d_cat() Service implementieren (Ein-Bild-Rekonstruktion, STL out).

 mesh_clean_cat() Pipeline: close holes → fix non-manifold → smooth → decimate → scale/orient.

 printability_check() (Wanddicke, Detailgröße, Überhänge, Volumen).

 auto_hollow() + Abflusslöcher an Unterseite.

 Slicer-Preset „cat_high_detail“ (Layerhöhe/Seam/Support).

 Serielle Erkennung + M115 + Temperatur-Lesung + Not-Stop.

 Kalibrier-Suite (First-Layer, Flow, Retraction) + Profil speichern.

 Varianten-Generator (3–5 Modelle) + Schönheits-Score, Top-1 wählen.

 UI: Upload/Prompt, 3D-Viewer, Support-Vorschau, Schätzungen, Progress.

 Farbwechsel (M600) optional mit UI-Prompt.

 Middleware-Reihenfolge fixen + Rate-Limit + File-Size-Limit.

 E2E-Tests (Text/Bild), Hardware-Smoke, Akzeptanzdruck dokumentieren.

E) Akzeptanztest (End-to-End, realer Druck)

Eingabe:

Text: „Katze, sitzend, 10 cm, glatte Oberfläche“ oder

Bild: cat.jpg (seitlich).

Systemausgabe:

STL wasserdicht, richtig skaliert und ausgerichtet.

Slicing mit Profil cat_high_detail.

G-Code mit korrekten Temps/Speed.

Druck:

Erster Layer haftet; keine losen Supports; Ohren sauber; <2 Fäden.

Zeit < 10 h, Material < 120 g (FDM, 0,4 mm Düse, PLA).

Abschluss:

UI zeigt „Fertig“, Zeit/Material protokolliert; Abbruch/Pause getestet.