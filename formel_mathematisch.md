# Formelsammlung (Mathematische Notation)

Dieses Dokument enthält eine Sammlung von Formeln aus dem Projekt "AI Agent 3D Print" in mathematischer Notation.

## `core/advanced_features.py`

- **Erfolgsrate:**
  - $$\text{Erfolgsrate} = \frac{\text{Anzahl abgeschlossener Anfragen}}{\text{Gesamtzahl der Anfragen}} \times 100$$

- **Erfolgsrate (Drucke):**
  - $$\text{Erfolgsrate} = \frac{\text{Anzahl erfolgreicher Drucke}}{\text{Gesamtzahl der letzten Drucke}} \times 100$$

## `core/ai_design_enhancer.py`

- **Oberflächenberechnung (Dreieck):**
  - $$A_{\Delta} = \frac{1}{2} \| \vec{e}_1 \times \vec{e}_2 \|$$

- **Volumenberechnung (Tetraeder):**
  - $$V = \frac{1}{6} | \vec{v}_1 \cdot (\vec{v}_2 \times \vec{v}_3) |$$

- **Volumen des Begrenzungsrahmens:**
  - $$V_{\text{box}} = w \cdot h \cdot d$$

- **Seitenverhältnis:**
  - $$\\text{Seitenverhältnis} = \frac{\max(d_1, d_2, d_3)}{\min(d_1, d_2, d_3)}$$

- **Überhanganalyse:**
  - $$P_{\text{overhang}} = \frac{N_{\text{Überhangdreiecke}}}{N_{\text{Gesamtdreiecke}}} \times 100$$

- **Schätzung des Stützvolumens:**
  - $$V_{\text{support}} \approx \min(P_{\text{overhang}} \times 0.3, 50)$$

- **Verhältnis von Oberfläche zu Volumen:**
  - $$r_{\text{SA/V}} = \frac{A}{V}$$

- **Druckbarkeitsskala:**
  - $$S_{\text{printability}} = 100 - 0.5 \cdot P_{\text{overhang}} - 2 \cdot N_{\text{thin}} - 1.5 \cdot N_{\text{small}}$$

- **Gesamtbewertung:**
  - $$S_{\text{overall}} = w_p S_p + w_c (100 - S_c) + w_f (100 - S_f) + w_s R_s$$

- **Verbesserungspotenzial:**
  - $$P_{\text{improvement}} = \frac{\sum_{i} (P_i \cdot w_i)}{\sum_{i} w_i}$$

## `core/ai_image_to_3d.py`

- **Bildskalierung:**
  - $$s = \frac{S_{\max}}{\max(w, h)}, \quad w' = w \cdot s, \quad h' = h \cdot s$$

- **Tiefenschätzung:**
  - $$G = \sqrt{G_x^2 + G_y^2}, \quad D' = D + 0.3 \cdot G$$

- **Höhenkartengenerierung:**
  - $$H = \left( \frac{D}{255} \right) \cdot s_h \cdot H_{\max} + H_{\text{base}}$$

- **UV-Koordinaten:**
  - $$u = \frac{x}{w-1}, \quad v = \frac{y}{h-1}$$

- **Dateigrößenberechnung:**
  - $$S_{\text{MB}} = \frac{S_{\text{Bytes}}}{1024^2}$$

## `core/cat_to_3d.py`

- **Skalierungsfaktor:**
  - $$s = \frac{H_{\text{target}}}{H_z}$$

- **Winkelberechnung (Überhang):**
  - $$\\alpha = \arccos(|n_z|)$$

- **Massenberechnung:**
  - $$m = \frac{V_{\text{mm}^3}}{1000} \cdot \rho$$

- **Mindestanforderungen:**
  - $$W_{\min} = 2 \cdot D_{\text{nozzle}}$$
  - $$D_{\min} = 3 \cdot H_{\text{layer}}$$

- **Aushöhlen (Hollowing):**
  - $$p_{\text{voxel}} = \max(0.8, \min(\\frac{W_t}{3}, 2))$$
  - $$r_{\text{erosion}} = \max(1, \text{round}(\\frac{W_t}{p_{\text{voxel}}}))$$
  - $$\\theta_k = 2\pi \frac{k}{n}$$

## `agents/cad_agent.py`

- **Volumenformeln:**
  - Würfel: $$V = lwh$$
  - Zylinder: $$V = \pi r^2 h$$
  - Kugel: $$V = \frac{4}{3} \pi r^3$$
  - Torus: $$V = 2\pi^2 R r^2$$
  - Kegelstumpf: $$V = \frac{1}{3} \pi h (R^2 + Rr + r^2)$$

- **Torus-Parametergleichungen:**
  - $$x(u,v) = (R + r\cos(v))\cos(u)$$
  - $$y(u,v) = (R + r\cos(v))\sin(u)$$
  - $$z(u,v) = r\sin(v)$$

- **Netzqualität:**
  - $$q = \frac{F}{V}$$

- **Voxel-Pitch:**
  - $$p = \frac{\max(B)}{R_{\text{es}}}$$

## `agents/slicer_agent.py`

- **Geschätzte Druckzeit:**
  - $$T_{\text{est}} \approx N_{\text{layer}} \cdot 2$$
  - $$T_{\text{est}} = N_{\text{layer}} \cdot 2 + N_{\text{moves}} \cdot 0.05$$
  - $$T_{\text{est}} \approx S_{\text{MB}} \cdot 10 \cdot k_q$$

- **Geschätzter Materialverbrauch:**
  - $$M_{\text{est}} \approx N_{\text{layer}} \cdot 0.5$$
