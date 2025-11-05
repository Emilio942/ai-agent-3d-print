# Formelsammlung

Dieses Dokument enthält eine Sammlung von Formeln, die im Projekt "AI Agent 3D Print" verwendet werden.

## `core/advanced_features.py`

### `process_batch`

- **Erfolgsrate:** `Erfolgsrate = (Anzahl abgeschlossener Anfragen / Gesamtzahl der Anfragen) * 100`

  - **Formel:** `success_rate = batch_result["completed"] / batch_result["total_requests"] * 100`

### `get_success_rate`

- **Erfolgsrate:** `Erfolgsrate = (Anzahl erfolgreicher Drucke / Gesamtzahl der letzten Drucke) * 100`

  - **Formel:** `success_rate = (successful / len(recent_prints)) * 100`

## `core/ai_design_enhancer.py`

### `GeometryAnalyzer`

- **Oberflächenberechnung:** `Dreiecksfläche = 0.5 * ||Kantenvektor1 x Kantenvektor2||`

  - **Formel:** `triangle_area = 0.5 * np.linalg.norm(np.cross(edge1, edge2))`

- **Volumenberechnung:** `Volumen += (Vektor1 ⋅ (Vektor2 x Vektor3)) / 6.0`

  - **Formel:** `volume += np.dot(v1, np.cross(v2, v3)) / 6.0`

- **Volumen des Begrenzungsrahmens:** `Breite * Höhe * Tiefe`

  - **Formel:** `width * height * depth`

- **Seitenverhältnis:** `Längste Dimension / Kürzeste Dimension`

  - **Formel:** `max(dimensions) / min(dimensions)`

- **Überhanganalyse:** `(Anzahl der Überhangdreiecke / Gesamtzahl der Dreiecke) * 100`

  - **Formel:** `(overhang_triangles / total_triangles * 100)`

- **Schätzung des Stützvolumens:** `min(Überhanganteil * 0.3, 50.0)`

  - **Formel:** `min(overhang_percentage * 0.3, 50.0)`

- **Verhältnis von Oberfläche zu Volumen:** `Oberfläche / Volumen`

  - **Formel:** `sa_vol_ratio = surface_area / volume`

- **Druckbarkeitsskala:** `Basispunktzahl - (Überhanganteil * 0.5) - (Dünne Wände * 2) - (Kleine Merkmale * 1.5)`

  - **Formel:** `base_score -= overhangs_pct * 0.5`, `base_score -= thin_walls * 2`, `base_score -= small_features * 1.5`

- **Komplexitätsskala:** Verschiedene Faktoren, einschließlich `Oberfläche / Volumen` und `Anzahl der Brücken * 5`

- **Fehlerrisikoskala:** Verschiedene Faktoren, einschließlich `Dünne Wände * 3` und `Schwachstellen * 2`

- **Geschätzte Erfolgsrate:** `max(0, 100 - Fehlerrisikoskala)`

### `AIOptimizationEngine`

- **Generierung von Trainingsdaten für Fehler:** `Fehlerbewertung = ...` (basierend auf Heuristiken)

- **Generierung von Trainingsdaten für Optimierung:** `Optimierungspotenzial = ...` (basierend auf Heuristiken)

- **Generierung von Optimierungsvorschlägen:**
  - `geschätzte_Zeitersparnis = Überhanganteil * 0.02`
  - `geschätzte_Materialersparnis = Überhanganteil * 0.3`
  - `Konfidenzbewertung = min(0.9, Fehlerwahrscheinlichkeit + 0.3)`

### `AIDesignEnhancer`

- **Gesamtbewertung:** Gewichtete Kombination verschiedener Bewertungen.

  - **Formel:** `score = (metrics.printability_score * weights['printability'] + (100 - metrics.complexity_score) * abs(weights['complexity']) + (100 - metrics.failure_risk_score) * abs(weights['failure_risk']) + metrics.estimated_success_rate * weights['success_rate'])`

- **Verbesserungspotenzial:** `(Summe der potenziellen Verbesserungen * Gewichtung) / Summe der Gewichtungen`

  - **Formel:** `total_potential += potential * weight`, `(total_potential / weight_sum)`

- **Häufigkeit gemeinsamer Probleme:** `(Anzahl / Gesamtzahl der Analysen) * 100`

  - **Formel:** `percentage = (count / len(history)) * 100`

## `core/ai_image_to_3d.py`

### `AIImageTo3DConverter`

- **Bildverarbeitung (Größenänderung):**
  - `Verhältnis = Maximale Größe / Maximale Bilddimension`
  - `Neue Größe = (Dimension * Verhältnis)`

- **Tiefenschätzung:**
  - `Gradientengröße = sqrt(Gradient_x^2 + Gradient_y^2)`
  - `Tiefenkarte += Gradientengröße * 0.3`

- **Höhenkartengenerierung:**
  - `Normalisierte Tiefe = Tiefenkarte / 255.0`
  - `Höhenkarte = Normalisierte Tiefe * Tiefenskala * Maximale Höhe`
  - `Höhenkarte += Basisdicke`

- **3D-Mesh-Erstellung (UV-Koordinaten):**
  - `u = x_flach / (Breite - 1)`
  - `v = y_flach / (Höhe - 1)`

- **Dateigrößenberechnung:**
  - `Größe in MB = Dateigröße in Bytes / (1024 * 1024)`

## `core/cat_to_3d.py`

### `_scale_to_target_height`

- **Skalierungsfaktor:** `Skalierungsfaktor = Zielhöhe in mm / Z-Höhe`

  - **Formel:** `s = float(target_height_mm) / z_height`

### `printability_check`

- **Winkelberechnung:** `Winkel = Grad(arccos(|Normalenvektor_z|))`

  - **Formel:** `angles = np.degrees(np.arccos(np.abs(nz)))`

- **Überhanganteil:** `Überhangfläche / Gesamtfläche`

  - **Formel:** `overhang_fraction = over_area / total_area`

- **Massenberechnung:** `(Volumen in mm³ / 1000.0) * Dichte`

  - **Formel:** `mass_g = (vol_mm3 / 1000.0) * density`

- **Anforderung an die Wandstärke:** `2.0 * Düsendurchmesser in mm`

  - **Formel:** `wall_req = 2.0 * float(params.nozzle_diameter_mm)`

- **Anforderung an die Detailgenauigkeit:** `3.0 * Schichthöhe in mm`

  - **Formel:** `detail_req = 3.0 * float(params.layer_height_mm)`

### `auto_hollow_and_add_drains`

- **Voxel-Pitch:** `max(0.8, min(Wandstärke / 3.0, 2.0))`

  - **Formel:** `pitch = max(0.8, min(wt / 3.0, 2.0))`

- **Erosionsradius:** `max(1, int(round(Wandstärke / Pitch)))`

  - **Formel:** `radius = max(1, int(round(wt / pitch)))`

- **Winkel für die Platzierung von Abflusslöchern:** `2.0 * pi * (k / n)`

  - **Formel:** `ang = 2.0 * math.pi * (k / n)`

## `agents/cad_agent.py`

### `CADAgent`

- **Materialvolumen und -gewicht:**
  - `Volumen in cm³ = Volumen in mm³ / 1000`
  - `Gewicht in g = Volumen in cm³ * Materialdichte`

- **Höhenkarte aus Bild:**
  - `Höhenkarte = (Graustufenbild / 255.0) * Höhenskala + Basisdicke`
  - `Skalierung = Maximale Größe / max(Höhe, Breite)`
  - `x = np.linspace(0, Breite - 1, Breite) * Pixelgröße in mm`
  - `y = np.linspace(0, Höhe - 1, Höhe) * Pixelgröße in mm`

- **Würfelvolumen:** `Länge * Breite * Höhe`

- **Zylindervolumen:** `π * Radius² * Höhe`

- **Kugelvolumen:** `(4/3) * π * Radius³`

- **Torusvolumen:** `2 * π² * Hauptradius * Nebenradius²`

- **Torus-Parametergleichungen:**
  - `x = (Hauptradius + Nebenradius * cos(v)) * cos(u)`
  - `y = (Hauptradius + Nebenradius * cos(v)) * sin(u)`
  - `z = Nebenradius * sin(v)`

- **Kegelvolumen:** `(1/3) * π * Grundradius² * Höhe`

- **Kegelstumpfvolumen:** `(1/3) * π * Höhe * (Grundradius² + Grundradius * Spitzenradius + Spitzenradius²)`

- **Oberflächenschätzung (aus Begrenzungsrahmen):** `2 * (dx*dy + dy*dz + dz*dx)`

- **Netzqualitätsbewertung:** `Verhältnis = Anzahl der Flächen / Anzahl der Eckpunkte`

- **Abstandsberechnung (Numpy):** `Abstände = ||Eckpunkte - Mittelpunkt||`

- **Voxel-Pitch:** `max(Größe des Begrenzungsrahmens) / Auflösung`

## `agents/slicer_agent.py`

### `SlicerAgent`

- **Mock-Slicer-Schätzungen:**
  - `Geschätzte Druckzeit = Anzahl der Schichten * 2`
  - `Materialverbrauch = Anzahl der Schichten * 0.5`

- **G-Code-Analyse:**
  - `Geschätzte Druckzeit = (Anzahl der Schichten * 2) + (Gesamtzahl der Bewegungen * 0.05)`

- **Druckzeitschätzung (aus Dateigröße):**
  - `Geschätzte Zeit = Dateigröße in MB * 10 * Zeitmultiplikator`

- **Druckzeitschätzung (aus G-Code-Metriken):**
  - `Basiszeit = Anzahl der Schichten * 2.0`
  - `Bewegungszeit = Gesamtzahl der Bewegungen * 0.01`
  - `max(Basiszeit + Bewegungszeit, 1.0)`

- **Materialverbrauchsschätzung (aus G-Code-Metriken):**
  - `Materialverbrauch = Anzahl der Schichten * 0.5`
