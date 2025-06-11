/**
 * 3D Print Preview Web Interface
 * 
 * This module provides web-based 3D visualization components for the AI Agent 3D Print System.
 * Features include interactive STL viewing, G-code layer preview, and print simulation.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

class Print3DViewer {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            background: options.background || 0xf0f0f0,
            showGrid: options.showGrid !== false,
            showAxes: options.showAxes !== false,
            gridSize: options.gridSize || 200,
            ...options
        };
        
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.layerData = null;
        this.animationFrame = null;
        
        this.init();
    }
    
    init() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(this.options.background);
        
        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75, 
            this.container.clientWidth / this.container.clientHeight, 
            0.1, 
            1000
        );
        this.camera.position.set(50, 50, 50);
        
        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);
        
        // Create controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        
        // Add lights
        this.setupLighting();
        
        // Add grid and axes
        if (this.options.showGrid) {
            this.addGrid();
        }
        
        if (this.options.showAxes) {
            this.addAxes();
        }
        
        // Add build volume
        this.addBuildVolume();
        
        // Start render loop
        this.animate();
        
        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }
    
    setupLighting() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
        this.scene.add(ambientLight);
        
        // Directional light
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(50, 50, 50);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);
        
        // Point lights for better visibility
        const pointLight1 = new THREE.PointLight(0xffffff, 0.3);
        pointLight1.position.set(-50, 50, 50);
        this.scene.add(pointLight1);
        
        const pointLight2 = new THREE.PointLight(0xffffff, 0.3);
        pointLight2.position.set(50, -50, 50);
        this.scene.add(pointLight2);
    }
    
    addGrid() {
        const gridSize = this.options.gridSize;
        const divisions = 20;
        
        const gridHelper = new THREE.GridHelper(gridSize, divisions);
        gridHelper.rotateX(Math.PI / 2);
        gridHelper.material.opacity = 0.3;
        gridHelper.material.transparent = true;
        this.scene.add(gridHelper);
    }
    
    addAxes() {
        const axesHelper = new THREE.AxesHelper(50);
        this.scene.add(axesHelper);
    }
    
    addBuildVolume() {
        const geometry = new THREE.BoxGeometry(200, 200, 200);
        const edges = new THREE.EdgesGeometry(geometry);
        const material = new THREE.LineBasicMaterial({ 
            color: 0x888888, 
            opacity: 0.3, 
            transparent: true 
        });
        const buildVolume = new THREE.LineSegments(edges, material);
        buildVolume.position.set(0, 0, 100);
        this.scene.add(buildVolume);
    }
    
    loadSTLPreview(previewData) {
        try {
            // Remove existing model
            if (this.currentModel) {
                this.scene.remove(this.currentModel);
            }
            
            const geometry = new THREE.BufferGeometry();
            
            // Set vertices
            const vertices = new Float32Array(previewData.geometry.vertices);
            geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
            
            // Set normals
            const normals = new Float32Array(previewData.geometry.normals);
            geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
            
            // Set faces
            const indices = new Uint32Array(previewData.geometry.faces);
            geometry.setIndex(new THREE.BufferAttribute(indices, 1));
            
            // Create material
            const material = new THREE.MeshLambertMaterial({
                color: 0x00aaff,
                side: THREE.DoubleSide
            });
            
            // Create mesh
            this.currentModel = new THREE.Mesh(geometry, material);
            this.currentModel.castShadow = true;
            this.currentModel.receiveShadow = true;
            
            // Center the model
            const bounds = previewData.geometry.bounds;
            const center = previewData.geometry.center;
            this.currentModel.position.set(-center[0], -center[1], -center[2]);
            
            this.scene.add(this.currentModel);
            
            // Update camera position
            if (previewData.camera) {
                this.camera.position.set(...previewData.camera.position);
                this.controls.target.set(...previewData.camera.target);
                this.controls.update();
            }
            
            console.log('STL preview loaded successfully');
            
        } catch (error) {
            console.error('Error loading STL preview:', error);
        }
    }
    
    loadLayerPreview(layerData) {
        try {
            this.layerData = layerData;
            this.currentLayer = 0;
            
            // Remove existing layer visualization
            this.clearLayerVisualization();
            
            // Create layer visualization
            this.createLayerVisualization();
            
            console.log(`Layer preview loaded: ${layerData.layers.length} layers`);
            
        } catch (error) {
            console.error('Error loading layer preview:', error);
        }
    }
    
    clearLayerVisualization() {
        // Remove all layer objects
        const layerObjects = this.scene.children.filter(child => 
            child.userData && child.userData.type === 'layer'
        );
        
        layerObjects.forEach(obj => this.scene.remove(obj));
    }
    
    createLayerVisualization() {
        if (!this.layerData) return;
        
        const layers = this.layerData.layers;
        
        layers.forEach((layer, index) => {
            const layerGroup = new THREE.Group();
            layerGroup.userData = { type: 'layer', layerNumber: layer.layer_number };
            layerGroup.visible = index === this.currentLayer;
            
            // Create paths for this layer
            layer.paths.forEach(path => {
                if (path.type === 'extrusion') {
                    const line = this.createExtrusionPath(path);
                    layerGroup.add(line);
                } else if (path.type === 'travel') {
                    const line = this.createTravelPath(path);
                    layerGroup.add(line);
                }
            });
            
            this.scene.add(layerGroup);
        });
    }
    
    createExtrusionPath(path) {
        const points = path.points.map(p => new THREE.Vector3(p[0], p[1], p[2]));
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        
        // Color based on speed
        const speed = path.speed || 1200;
        const color = this.getSpeedColor(speed);
        
        const material = new THREE.LineBasicMaterial({ 
            color: color,
            linewidth: 2
        });
        
        return new THREE.Line(geometry, material);
    }
    
    createTravelPath(path) {
        const points = path.points.map(p => new THREE.Vector3(p[0], p[1], p[2]));
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        
        const material = new THREE.LineDashedMaterial({ 
            color: 0x888888,
            linewidth: 1,
            dashSize: 2,
            gapSize: 2
        });
        
        const line = new THREE.Line(geometry, material);
        line.computeLineDistances();
        return line;
    }
    
    getSpeedColor(speed) {
        // Map speed to color (slow = red, fast = green)
        const normalizedSpeed = Math.min(speed / 3000, 1);
        const hue = normalizedSpeed * 0.3; // 0 (red) to 0.3 (green)
        return new THREE.Color().setHSL(hue, 1, 0.5);
    }
    
    showLayer(layerNumber) {
        if (!this.layerData) return;
        
        this.currentLayer = layerNumber;
        
        // Hide all layers
        this.scene.children.forEach(child => {
            if (child.userData && child.userData.type === 'layer') {
                child.visible = false;
            }
        });
        
        // Show layers up to current layer
        this.scene.children.forEach(child => {
            if (child.userData && child.userData.type === 'layer' && 
                child.userData.layerNumber <= layerNumber) {
                child.visible = true;
            }
        });
    }
    
    animateLayerPreview(speed = 1) {
        if (!this.layerData || this.layerData.layers.length === 0) return;
        
        let currentLayer = 0;
        const totalLayers = this.layerData.layers.length;
        
        const animate = () => {
            if (currentLayer < totalLayers) {
                this.showLayer(currentLayer);
                currentLayer++;
                
                setTimeout(() => {
                    requestAnimationFrame(animate);
                }, 100 / speed);
            }
        };
        
        animate();
    }
    
    setViewMode(mode) {
        switch (mode) {
            case 'wireframe':
                if (this.currentModel) {
                    this.currentModel.material.wireframe = true;
                }
                break;
                
            case 'solid':
                if (this.currentModel) {
                    this.currentModel.material.wireframe = false;
                }
                break;
                
            case 'layers':
                if (this.currentModel) {
                    this.currentModel.visible = false;
                }
                break;
                
            case 'combined':
                if (this.currentModel) {
                    this.currentModel.visible = true;
                    this.currentModel.material.opacity = 0.3;
                    this.currentModel.material.transparent = true;
                }
                break;
        }
    }
    
    exportPreview(format = 'png') {
        switch (format) {
            case 'png':
                const dataURL = this.renderer.domElement.toDataURL('image/png');
                const link = document.createElement('a');
                link.download = 'print_preview.png';
                link.href = dataURL;
                link.click();
                break;
                
            case 'json':
                const sceneData = {
                    camera: {
                        position: this.camera.position.toArray(),
                        target: this.controls.target.toArray()
                    },
                    timestamp: Date.now()
                };
                
                const blob = new Blob([JSON.stringify(sceneData, null, 2)], 
                    { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.download = 'preview_settings.json';
                a.href = url;
                a.click();
                URL.revokeObjectURL(url);
                break;
        }
    }
    
    animate() {
        this.animationFrame = requestAnimationFrame(() => this.animate());
        
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
    
    onWindowResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
    
    dispose() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        this.renderer.dispose();
        this.container.removeChild(this.renderer.domElement);
        
        window.removeEventListener('resize', () => this.onWindowResize());
    }
}

class PreviewControls {
    constructor(viewer, container) {
        this.viewer = viewer;
        this.container = container;
        this.createControls();
    }
    
    createControls() {
        const controlsHTML = `
            <div class="preview-controls">
                <div class="control-section">
                    <h4>View Mode</h4>
                    <select id="viewMode">
                        <option value="solid">Solid</option>
                        <option value="wireframe">Wireframe</option>
                        <option value="layers">Layers Only</option>
                        <option value="combined">Combined</option>
                    </select>
                </div>
                
                <div class="control-section">
                    <h4>Layer Controls</h4>
                    <div class="layer-controls">
                        <input type="range" id="layerSlider" min="0" max="100" value="0">
                        <div class="layer-info">
                            <span>Layer: <span id="currentLayer">0</span>/<span id="totalLayers">0</span></span>
                        </div>
                        <div class="layer-buttons">
                            <button id="playAnimation">Play</button>
                            <button id="pauseAnimation">Pause</button>
                            <button id="resetAnimation">Reset</button>
                        </div>
                    </div>
                </div>
                
                <div class="control-section">
                    <h4>Display Options</h4>
                    <label><input type="checkbox" id="showGrid" checked> Show Grid</label>
                    <label><input type="checkbox" id="showAxes" checked> Show Axes</label>
                    <label><input type="checkbox" id="showBuildVolume" checked> Build Volume</label>
                </div>
                
                <div class="control-section">
                    <h4>Export</h4>
                    <button id="exportPNG">Export PNG</button>
                    <button id="exportJSON">Export Settings</button>
                </div>
            </div>
        `;
        
        this.container.innerHTML = controlsHTML;
        this.bindEvents();
    }
    
    bindEvents() {
        // View mode
        document.getElementById('viewMode').addEventListener('change', (e) => {
            this.viewer.setViewMode(e.target.value);
        });
        
        // Layer controls
        const layerSlider = document.getElementById('layerSlider');
        layerSlider.addEventListener('input', (e) => {
            const layer = parseInt(e.target.value);
            this.viewer.showLayer(layer);
            document.getElementById('currentLayer').textContent = layer;
        });
        
        // Animation controls
        document.getElementById('playAnimation').addEventListener('click', () => {
            this.viewer.animateLayerPreview(1);
        });
        
        document.getElementById('pauseAnimation').addEventListener('click', () => {
            // Implementation for pause
        });
        
        document.getElementById('resetAnimation').addEventListener('click', () => {
            this.viewer.showLayer(0);
            layerSlider.value = 0;
            document.getElementById('currentLayer').textContent = '0';
        });
        
        // Export controls
        document.getElementById('exportPNG').addEventListener('click', () => {
            this.viewer.exportPreview('png');
        });
        
        document.getElementById('exportJSON').addEventListener('click', () => {
            this.viewer.exportPreview('json');
        });
    }
    
    updateLayerInfo(totalLayers) {
        const slider = document.getElementById('layerSlider');
        slider.max = totalLayers - 1;
        document.getElementById('totalLayers').textContent = totalLayers;
    }
}

// CSS Styles for preview interface
const previewStyles = `
    .preview-container {
        display: flex;
        height: 100vh;
    }
    
    .preview-viewport {
        flex: 1;
        position: relative;
        background: #f0f0f0;
    }
    
    .preview-controls {
        width: 300px;
        background: #fff;
        border-left: 1px solid #ddd;
        padding: 20px;
        overflow-y: auto;
    }
    
    .control-section {
        margin-bottom: 30px;
        padding-bottom: 20px;
        border-bottom: 1px solid #eee;
    }
    
    .control-section:last-child {
        border-bottom: none;
    }
    
    .control-section h4 {
        margin: 0 0 15px 0;
        color: #333;
        font-size: 16px;
    }
    
    .control-section select,
    .control-section input[type="range"] {
        width: 100%;
        margin-bottom: 10px;
    }
    
    .layer-controls {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .layer-info {
        text-align: center;
        font-size: 14px;
        color: #666;
    }
    
    .layer-buttons {
        display: flex;
        gap: 5px;
    }
    
    .layer-buttons button {
        flex: 1;
        padding: 8px;
        border: 1px solid #ddd;
        background: #f9f9f9;
        cursor: pointer;
        border-radius: 4px;
    }
    
    .layer-buttons button:hover {
        background: #e9e9e9;
    }
    
    .control-section label {
        display: block;
        margin-bottom: 8px;
        cursor: pointer;
    }
    
    .control-section button {
        width: 100%;
        padding: 10px;
        margin-bottom: 8px;
        border: 1px solid #ddd;
        background: #f9f9f9;
        cursor: pointer;
        border-radius: 4px;
    }
    
    .control-section button:hover {
        background: #e9e9e9;
    }
    
    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    }
    
    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;

// Export for use in other modules
export { Print3DViewer, PreviewControls, previewStyles };
