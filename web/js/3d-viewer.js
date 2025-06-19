/**
 * Advanced 3D Model Viewer with Three.js
 * AI Agent 3D Print System
 * 
 * Features:
 * - Interactive 3D model viewing
 * - AR preview capabilities
 * - Real-time editing tools
 * - Print analysis visualization
 * - Multi-format support (STL, OBJ, GLB, GLTF)
 */

class Advanced3DViewer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            enableAR: true,
            enableVR: false,
            showGrid: true,
            showAxes: true,
            enableControls: true,
            enableAnimation: true,
            backgroundColor: 0xf0f0f0,
            ...options
        };
        
        // Three.js components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.arButton = null;
        
        // Analysis tools
        this.analysisMode = false;
        this.measurements = [];
        this.printBed = null;
        this.supportStructures = [];
        
        // Animation
        this.animationId = null;
        this.clock = new THREE.Clock();
        
        // Event handlers
        this.eventHandlers = new Map();
        
        this.init();
    }
    
    init() {
        console.log('🎮 Initializing Advanced 3D Viewer...');
        
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createControls();
        this.createLighting();
        this.createEnvironment();
        this.setupEventHandlers();
        this.createUI();
        this.startRenderLoop();
        
        console.log('✅ Advanced 3D Viewer initialized');
    }
    
    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(this.options.backgroundColor);
        
        // Add fog for depth perception
        this.scene.fog = new THREE.Fog(this.options.backgroundColor, 100, 1000);
    }
    
    createCamera() {
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 2000);
        this.camera.position.set(50, 50, 50);
        this.camera.lookAt(0, 0, 0);
    }
    
    createRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            preserveDrawingBuffer: true // For screenshots
        });
        
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1;
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        
        this.container.appendChild(this.renderer.domElement);
        
        // Handle resize
        window.addEventListener('resize', () => this.onWindowResize());
    }
    
    createControls() {
        if (!this.options.enableControls) return;
        
        // Use OrbitControls for mouse/touch interaction
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 10;
        this.controls.maxDistance = 500;
        this.controls.maxPolarAngle = Math.PI;
        
        // Add smooth animation
        this.controls.addEventListener('change', () => {
            if (!this.options.enableAnimation) {
                this.render();
            }
        });
    }
    
    createLighting() {
        // Ambient light for overall illumination
        const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
        this.scene.add(ambientLight);
        
        // Main directional light
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(100, 100, 50);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.1;
        directionalLight.shadow.camera.far = 500;
        directionalLight.shadow.camera.left = -100;
        directionalLight.shadow.camera.right = 100;
        directionalLight.shadow.camera.top = 100;
        directionalLight.shadow.camera.bottom = -100;
        this.scene.add(directionalLight);
        
        // Fill lights
        const fillLight1 = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight1.position.set(-50, 50, 50);
        this.scene.add(fillLight1);
        
        const fillLight2 = new THREE.DirectionalLight(0xffffff, 0.2);
        fillLight2.position.set(50, -50, -50);
        this.scene.add(fillLight2);
    }
    
    createEnvironment() {
        if (this.options.showGrid) {
            // Print bed grid
            const gridHelper = new THREE.GridHelper(200, 20, 0x888888, 0xcccccc);
            gridHelper.name = 'grid';
            this.scene.add(gridHelper);
        }
        
        if (this.options.showAxes) {
            // Coordinate axes
            const axesHelper = new THREE.AxesHelper(30);
            axesHelper.name = 'axes';
            this.scene.add(axesHelper);
        }
        
        // Create print bed representation
        this.createPrintBed();
    }
    
    createPrintBed() {
        const bedGeometry = new THREE.PlaneGeometry(200, 200);
        const bedMaterial = new THREE.MeshPhongMaterial({
            color: 0x333333,
            transparent: true,
            opacity: 0.1,
            side: THREE.DoubleSide
        });
        
        this.printBed = new THREE.Mesh(bedGeometry, bedMaterial);
        this.printBed.rotation.x = -Math.PI / 2;
        this.printBed.position.y = -0.1;
        this.printBed.name = 'printBed';
        this.printBed.receiveShadow = true;
        this.scene.add(this.printBed);
    }
    
    setupEventHandlers() {
        // Mouse events for interaction
        this.renderer.domElement.addEventListener('click', (event) => this.onMouseClick(event));
        this.renderer.domElement.addEventListener('dblclick', (event) => this.onMouseDoubleClick(event));
        
        // Touch events for mobile
        this.renderer.domElement.addEventListener('touchstart', (event) => this.onTouchStart(event));
        this.renderer.domElement.addEventListener('touchend', (event) => this.onTouchEnd(event));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => this.onKeyDown(event));
    }
    
    createUI() {
        // Create viewer UI container
        const uiContainer = document.createElement('div');
        uiContainer.className = 'viewer-ui';
        uiContainer.innerHTML = `
            <div class="viewer-toolbar">
                <div class="toolbar-group">
                    <button id="resetView" class="btn-icon" title="Reset View">🏠</button>
                    <button id="fitToScreen" class="btn-icon" title="Fit to Screen">📐</button>
                    <button id="toggleWireframe" class="btn-icon" title="Toggle Wireframe">🔲</button>
                    <button id="toggleAnalysis" class="btn-icon" title="Analysis Mode">🔍</button>
                </div>
                <div class="toolbar-group">
                    <button id="takeScreenshot" class="btn-icon" title="Screenshot">📸</button>
                    <button id="shareModel" class="btn-icon" title="Share">📤</button>
                    <button id="downloadModel" class="btn-icon" title="Download">💾</button>
                </div>
                <div class="toolbar-group ar-group">
                    <button id="arView" class="btn-icon btn-ar" title="AR View">🥽</button>
                </div>
            </div>
            <div class="viewer-info">
                <div id="modelInfo" class="model-info"></div>
                <div id="analysisInfo" class="analysis-info" style="display: none;"></div>
            </div>
            <div class="viewer-controls">
                <div class="control-group">
                    <label>Opacity</label>
                    <input type="range" id="opacitySlider" min="0" max="100" value="100">
                </div>
                <div class="control-group">
                    <label>Rotation Speed</label>
                    <input type="range" id="rotationSlider" min="0" max="10" value="0">
                </div>
            </div>
        `;
        
        this.container.appendChild(uiContainer);
        this.bindUIEvents();
        
        // Setup AR if supported
        if (this.options.enableAR && 'xr' in navigator) {
            this.setupAR();
        } else {
            document.getElementById('arView').style.display = 'none';
        }
    }
    
    bindUIEvents() {
        // Toolbar buttons
        document.getElementById('resetView').addEventListener('click', () => this.resetView());
        document.getElementById('fitToScreen').addEventListener('click', () => this.fitToScreen());
        document.getElementById('toggleWireframe').addEventListener('click', () => this.toggleWireframe());
        document.getElementById('toggleAnalysis').addEventListener('click', () => this.toggleAnalysis());
        document.getElementById('takeScreenshot').addEventListener('click', () => this.takeScreenshot());
        document.getElementById('shareModel').addEventListener('click', () => this.shareModel());
        document.getElementById('downloadModel').addEventListener('click', () => this.downloadModel());
        document.getElementById('arView').addEventListener('click', () => this.enterAR());
        
        // Control sliders
        document.getElementById('opacitySlider').addEventListener('input', (e) => {
            this.setModelOpacity(e.target.value / 100);
        });
        
        document.getElementById('rotationSlider').addEventListener('input', (e) => {
            this.setAutoRotation(e.target.value / 10);
        });
    }
    
    async loadModel(url, format = 'auto') {
        try {
            console.log(`📦 Loading 3D model: ${url}`);
            this.showLoadingIndicator(true);
            
            // Clear previous model
            if (this.currentModel) {
                this.scene.remove(this.currentModel);
                this.currentModel = null;
            }
            
            let loader;
            const detectedFormat = format === 'auto' ? this.detectFormat(url) : format;
            
            switch (detectedFormat.toLowerCase()) {
                case 'stl':
                    loader = new THREE.STLLoader();
                    break;
                case 'obj':
                    loader = new THREE.OBJLoader();
                    break;
                case 'glb':
                case 'gltf':
                    loader = new THREE.GLTFLoader();
                    break;
                default:
                    throw new Error(`Unsupported format: ${detectedFormat}`);
            }
            
            return new Promise((resolve, reject) => {
                loader.load(
                    url,
                    (object) => {
                        this.onModelLoaded(object, detectedFormat);
                        resolve(object);
                    },
                    (progress) => {
                        this.onLoadProgress(progress);
                    },
                    (error) => {
                        console.error('❌ Model loading failed:', error);
                        this.showLoadingIndicator(false);
                        reject(error);
                    }
                );
            });
            
        } catch (error) {
            console.error('❌ Model loading error:', error);
            this.showLoadingIndicator(false);
            throw error;
        }
    }
    
    onModelLoaded(object, format) {
        console.log(`✅ Model loaded successfully (${format})`);
        
        let model;
        
        if (format === 'gltf' || format === 'glb') {
            model = object.scene;
        } else if (format === 'stl') {
            // STL files need material
            const geometry = object;
            const material = new THREE.MeshPhongMaterial({
                color: 0x00ff88,
                shininess: 100,
                side: THREE.DoubleSide
            });
            model = new THREE.Mesh(geometry, material);
        } else {
            model = object;
        }
        
        // Enable shadows
        model.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
            }
        });
        
        this.currentModel = model;
        this.scene.add(model);
        
        // Analyze and display model info
        this.analyzeModel(model);
        
        // Fit to screen
        this.fitToScreen();
        
        this.showLoadingIndicator(false);
        this.emit('modelLoaded', { model, format });
    }
    
    analyzeModel(model) {
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        
        let vertices = 0;
        let faces = 0;
        
        model.traverse((child) => {
            if (child.isMesh && child.geometry) {
                if (child.geometry.attributes.position) {
                    vertices += child.geometry.attributes.position.count;
                }
                if (child.geometry.index) {
                    faces += child.geometry.index.count / 3;
                } else if (child.geometry.attributes.position) {
                    faces += child.geometry.attributes.position.count / 3;
                }
            }
        });
        
        const info = {
            dimensions: {
                x: size.x.toFixed(2),
                y: size.y.toFixed(2),
                z: size.z.toFixed(2)
            },
            center: {
                x: center.x.toFixed(2),
                y: center.y.toFixed(2),
                z: center.z.toFixed(2)
            },
            vertices: Math.round(vertices),
            faces: Math.round(faces),
            volume: this.calculateVolume(model),
            printable: this.assessPrintability(model)
        };
        
        this.displayModelInfo(info);
        return info;
    }
    
    calculateVolume(model) {
        // Simplified volume calculation
        // In production, this would use proper mesh volume calculation
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        return (size.x * size.y * size.z).toFixed(2);
    }
    
    assessPrintability(model) {
        // Basic printability assessment
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        
        const issues = [];
        
        // Check for overhangs (simplified)
        if (size.z > size.x * 2 || size.z > size.y * 2) {
            issues.push('May need supports (tall/thin object)');
        }
        
        // Check minimum feature size
        const minSize = Math.min(size.x, size.y, size.z);
        if (minSize < 0.4) {
            issues.push('Features may be too small to print reliably');
        }
        
        // Check bed size (assuming 200x200mm bed)
        if (size.x > 200 || size.y > 200) {
            issues.push('Object may not fit on print bed');
        }
        
        return {
            printable: issues.length === 0,
            issues: issues,
            score: Math.max(0, 100 - (issues.length * 25))
        };
    }
    
    displayModelInfo(info) {
        const infoElement = document.getElementById('modelInfo');
        infoElement.innerHTML = `
            <h4>Model Information</h4>
            <div class="info-grid">
                <div class="info-item">
                    <label>Dimensions (mm):</label>
                    <span>${info.dimensions.x} × ${info.dimensions.y} × ${info.dimensions.z}</span>
                </div>
                <div class="info-item">
                    <label>Vertices:</label>
                    <span>${info.vertices.toLocaleString()}</span>
                </div>
                <div class="info-item">
                    <label>Faces:</label>
                    <span>${info.faces.toLocaleString()}</span>
                </div>
                <div class="info-item">
                    <label>Volume:</label>
                    <span>${info.volume} mm³</span>
                </div>
                <div class="info-item">
                    <label>Printability:</label>
                    <span class="printability-score score-${info.printable.score >= 75 ? 'good' : info.printable.score >= 50 ? 'medium' : 'poor'}">
                        ${info.printable.score}%
                    </span>
                </div>
            </div>
            ${info.printable.issues.length > 0 ? `
                <div class="printability-issues">
                    <h5>Potential Issues:</h5>
                    <ul>
                        ${info.printable.issues.map(issue => `<li>${issue}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
    }
    
    // Viewer control methods
    resetView() {
        if (this.controls) {
            this.controls.reset();
        }
        this.camera.position.set(50, 50, 50);
        this.camera.lookAt(0, 0, 0);
    }
    
    fitToScreen() {
        if (!this.currentModel) return;
        
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        
        const maxSize = Math.max(size.x, size.y, size.z);
        const distance = maxSize * 2;
        
        this.camera.position.copy(center);
        this.camera.position.z += distance;
        this.camera.position.y += distance * 0.5;
        this.camera.lookAt(center);
        
        if (this.controls) {
            this.controls.target.copy(center);
            this.controls.update();
        }
    }
    
    toggleWireframe() {
        if (!this.currentModel) return;
        
        this.currentModel.traverse((child) => {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(mat => {
                        mat.wireframe = !mat.wireframe;
                    });
                } else {
                    child.material.wireframe = !child.material.wireframe;
                }
            }
        });
    }
    
    toggleAnalysis() {
        this.analysisMode = !this.analysisMode;
        
        const analysisInfo = document.getElementById('analysisInfo');
        if (this.analysisMode) {
            analysisInfo.style.display = 'block';
            this.showAnalysisInfo();
        } else {
            analysisInfo.style.display = 'none';
        }
        
        // Toggle analysis visualization
        this.toggleAnalysisVisualization();
    }
    
    showAnalysisInfo() {
        if (!this.currentModel) return;
        
        const analysisInfo = document.getElementById('analysisInfo');
        analysisInfo.innerHTML = `
            <h4>Print Analysis</h4>
            <div class="analysis-tools">
                <button id="checkOverhangs" class="btn-analysis">Check Overhangs</button>
                <button id="addSupports" class="btn-analysis">Add Supports</button>
                <button id="slicePreview" class="btn-analysis">Slice Preview</button>
                <button id="measureTool" class="btn-analysis">Measure</button>
            </div>
            <div id="analysisResults" class="analysis-results"></div>
        `;
        
        // Bind analysis tool events
        document.getElementById('checkOverhangs').addEventListener('click', () => this.checkOverhangs());
        document.getElementById('addSupports').addEventListener('click', () => this.addSupports());
        document.getElementById('slicePreview').addEventListener('click', () => this.showSlicePreview());
        document.getElementById('measureTool').addEventListener('click', () => this.enableMeasureTool());
    }
    
    toggleAnalysisVisualization() {
        // Implementation for analysis visualization
        // Would show overhang detection, support structures, etc.
    }
    
    // Analysis tools
    checkOverhangs() {
        console.log('🔍 Checking overhangs...');
        // Implementation for overhang detection
    }
    
    addSupports() {
        console.log('🏗️ Adding support structures...');
        // Implementation for automatic support generation
    }
    
    showSlicePreview() {
        console.log('🍰 Showing slice preview...');
        // Implementation for slice visualization
    }
    
    enableMeasureTool() {
        console.log('📏 Measurement tool enabled');
        // Implementation for measurement tool
    }
    
    // Utility methods
    setModelOpacity(opacity) {
        if (!this.currentModel) return;
        
        this.currentModel.traverse((child) => {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(mat => {
                        mat.transparent = opacity < 1;
                        mat.opacity = opacity;
                    });
                } else {
                    child.material.transparent = opacity < 1;
                    child.material.opacity = opacity;
                }
            }
        });
    }
    
    setAutoRotation(speed) {
        this.autoRotationSpeed = speed;
    }
    
    takeScreenshot() {
        const canvas = this.renderer.domElement;
        const dataURL = canvas.toDataURL('image/png');
        
        // Download screenshot
        const link = document.createElement('a');
        link.download = `3d_model_${Date.now()}.png`;
        link.href = dataURL;
        link.click();
        
        this.emit('screenshot', { dataURL });
    }
    
    shareModel() {
        if (navigator.share) {
            const canvas = this.renderer.domElement;
            canvas.toBlob((blob) => {
                const file = new File([blob], '3d_model.png', { type: 'image/png' });
                navigator.share({
                    title: '3D Model Preview',
                    text: 'Check out this 3D model!',
                    files: [file]
                });
            });
        } else {
            // Fallback: copy link to clipboard
            navigator.clipboard.writeText(window.location.href);
            alert('Link copied to clipboard!');
        }
    }
    
    downloadModel() {
        if (this.currentModel) {
            // Implementation for model download
            console.log('💾 Downloading model...');
            this.emit('downloadRequested');
        }
    }
    
    // AR functionality
    setupAR() {
        // WebXR AR setup
        if (this.renderer.xr) {
            this.renderer.xr.enabled = true;
        }
    }
    
    async enterAR() {
        if ('xr' in navigator) {
            try {
                const session = await navigator.xr.requestSession('immersive-ar');
                this.renderer.xr.setSession(session);
                this.emit('arStarted');
            } catch (error) {
                console.error('❌ AR not supported:', error);
                alert('AR not supported on this device');
            }
        }
    }
    
    // Event handling
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }
    
    // Utility methods
    detectFormat(url) {
        const extension = url.split('.').pop().toLowerCase();
        return extension;
    }
    
    showLoadingIndicator(show) {
        // Implementation for loading indicator
        if (show) {
            console.log('⏳ Loading...');
        } else {
            console.log('✅ Loading complete');
        }
    }
    
    onLoadProgress(progress) {
        if (progress.lengthComputable) {
            const percentage = (progress.loaded / progress.total) * 100;
            console.log(`📈 Loading progress: ${percentage.toFixed(1)}%`);
        }
    }
    
    // Event handlers
    onMouseClick(event) {
        // Handle mouse clicks for interaction
    }
    
    onMouseDoubleClick(event) {
        this.fitToScreen();
    }
    
    onTouchStart(event) {
        // Handle touch interactions
    }
    
    onTouchEnd(event) {
        // Handle touch end
    }
    
    onKeyDown(event) {
        switch (event.code) {
            case 'KeyR':
                this.resetView();
                break;
            case 'KeyF':
                this.fitToScreen();
                break;
            case 'KeyW':
                this.toggleWireframe();
                break;
            case 'KeyA':
                this.toggleAnalysis();
                break;
        }
    }
    
    onWindowResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
    
    // Render loop
    startRenderLoop() {
        const animate = () => {
            this.animationId = requestAnimationFrame(animate);
            
            // Auto rotation
            if (this.autoRotationSpeed > 0 && this.currentModel) {
                this.currentModel.rotation.y += this.autoRotationSpeed * 0.01;
            }
            
            // Update controls
            if (this.controls) {
                this.controls.update();
            }
            
            this.render();
        };
        
        animate();
    }
    
    render() {
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
    
    // Cleanup
    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.renderer) {
            this.renderer.dispose();
        }
        
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
        }
        
        // Clear event handlers
        this.eventHandlers.clear();
        
        console.log('🧹 3D Viewer disposed');
    }
}

// Export for use
window.Advanced3DViewer = Advanced3DViewer;
