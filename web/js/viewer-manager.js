/**
 * 3D Viewer Manager
 * Simple integration wrapper for the Advanced3DViewer
 */

class Viewer3DManager {
    constructor() {
        this.viewer = null;
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;

        try {
            // Initialize the 3D viewer when the tab is first accessed
            const viewerCanvas = document.getElementById('viewerCanvas');
            if (viewerCanvas && window.Advanced3DViewer) {
                this.viewer = new Advanced3DViewer('viewerCanvas', {
                    enableAR: false, // Simplified for now
                    enableVR: false,
                    showGrid: true,
                    showAxes: true,
                    backgroundColor: 0x2c3e50
                });
                
                this.setupControls();
                this.initialized = true;
                this.updateStatus('3D Viewer initialized');
            } else {
                // Fallback to basic Three.js setup
                this.initBasicViewer();
            }
        } catch (error) {
            console.error('Failed to initialize 3D viewer:', error);
            this.initBasicViewer();
        }
    }

    initBasicViewer() {
        const canvas = document.getElementById('viewerCanvas');
        if (!canvas) return;

        // Basic Three.js setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x2c3e50);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75, 
            canvas.clientWidth / canvas.clientHeight, 
            0.1, 
            1000
        );
        this.camera.position.set(0, 0, 5);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        // Clear and append
        canvas.innerHTML = '';
        canvas.appendChild(this.renderer.domElement);

        // Controls
        if (window.THREE.OrbitControls) {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
        }

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(1, 1, 1);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);

        // Grid
        const gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(gridHelper);

        // Start render loop
        this.animate();
        this.setupControls();
        this.initialized = true;
        this.updateStatus('Basic 3D Viewer ready');
    }

    setupControls() {
        // Load Model button
        const loadModelBtn = document.getElementById('loadModelBtn');
        if (loadModelBtn) {
            loadModelBtn.addEventListener('click', () => {
                this.showModelFileDialog();
            });
        }

        // Reset View button
        const resetViewBtn = document.getElementById('resetViewBtn');
        if (resetViewBtn) {
            resetViewBtn.addEventListener('click', () => {
                this.resetView();
            });
        }

        // Wireframe toggle
        const wireframeBtn = document.getElementById('wireframeBtn');
        if (wireframeBtn) {
            wireframeBtn.addEventListener('click', () => {
                this.toggleWireframe();
            });
        }

        // Handle window resize
        window.addEventListener('resize', () => {
            this.onWindowResize();
        });
    }

    animate() {
        if (!this.renderer) return;

        this.animationId = requestAnimationFrame(() => this.animate());

        if (this.controls) {
            this.controls.update();
        }

        this.renderer.render(this.scene, this.camera);
    }

    async loadModel(modelPath) {
        if (!this.initialized) {
            this.init();
        }

        try {
            this.updateStatus('Loading model...');
            
            // Determine file type and use appropriate loader
            const extension = modelPath.split('.').pop().toLowerCase();
            let loader;

            switch (extension) {
                case 'stl':
                    if (window.THREE.STLLoader) {
                        loader = new THREE.STLLoader();
                    }
                    break;
                case 'obj':
                    if (window.THREE.OBJLoader) {
                        loader = new THREE.OBJLoader();
                    }
                    break;
                case 'ply':
                    if (window.THREE.PLYLoader) {
                        loader = new THREE.PLYLoader();
                    }
                    break;
                default:
                    throw new Error(`Unsupported file format: ${extension}`);
            }

            if (!loader) {
                throw new Error(`Loader not available for ${extension} files`);
            }

            // Clear existing model
            if (this.currentModel) {
                this.scene.remove(this.currentModel);
            }

            // Load the model
            loader.load(
                modelPath,
                (geometry) => {
                    // Handle different geometry types
                    if (geometry.isBufferGeometry) {
                        this.addGeometryToScene(geometry);
                    } else if (geometry.isGroup || geometry.isObject3D) {
                        this.addObjectToScene(geometry);
                    } else {
                        console.warn('Unknown geometry type:', geometry);
                    }

                    this.updateStatus('Model loaded successfully');
                    this.updateModelInfo(modelPath);
                },
                (progress) => {
                    const percent = (progress.loaded / progress.total * 100) || 0;
                    this.updateStatus(`Loading... ${percent.toFixed(1)}%`);
                },
                (error) => {
                    console.error('Error loading model:', error);
                    this.updateStatus('Failed to load model');
                }
            );

        } catch (error) {
            console.error('Model loading error:', error);
            this.updateStatus(`Error: ${error.message}`);
        }
    }

    addGeometryToScene(geometry) {
        // Create material
        const material = new THREE.MeshPhongMaterial({
            color: 0x00ff88,
            shininess: 100,
            side: THREE.DoubleSide
        });

        // Create mesh
        const mesh = new THREE.Mesh(geometry, material);
        mesh.castShadow = true;
        mesh.receiveShadow = true;

        // Center the model
        geometry.computeBoundingBox();
        const box = geometry.boundingBox;
        const center = box.getCenter(new THREE.Vector3());
        geometry.translate(-center.x, -center.y, -center.z);

        // Scale to fit viewport
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 2 / maxDim;
        mesh.scale.multiplyScalar(scale);

        this.scene.add(mesh);
        this.currentModel = mesh;

        // Adjust camera
        this.resetView();
    }

    addObjectToScene(object) {
        // Handle group/object3D
        this.scene.add(object);
        this.currentModel = object;

        // Center and scale
        const box = new THREE.Box3().setFromObject(object);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        object.position.sub(center);
        
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 2 / maxDim;
        object.scale.multiplyScalar(scale);

        this.resetView();
    }

    showModelFileDialog() {
        // Create file input
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.stl,.obj,.ply';
        
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                this.loadModel(url);
            }
        });

        input.click();
    }

    resetView() {
        if (!this.camera || !this.controls) return;

        this.camera.position.set(3, 3, 3);
        this.camera.lookAt(0, 0, 0);
        
        if (this.controls) {
            this.controls.reset();
        }
    }

    toggleWireframe() {
        if (!this.currentModel) return;

        this.currentModel.traverse((child) => {
            if (child.isMesh && child.material) {
                child.material.wireframe = !child.material.wireframe;
            }
        });
    }

    onWindowResize() {
        if (!this.camera || !this.renderer) return;

        const canvas = document.getElementById('viewerCanvas');
        if (!canvas) return;

        this.camera.aspect = canvas.clientWidth / canvas.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    }

    updateStatus(message) {
        const statusElement = document.getElementById('viewerStatus');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateModelInfo(modelPath) {
        const infoElement = document.getElementById('viewerInfo');
        if (infoElement) {
            const filename = modelPath.split('/').pop();
            infoElement.textContent = `Loaded: ${filename}`;
        }
    }

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
    }
}

// Initialize the 3D viewer manager
document.addEventListener('DOMContentLoaded', () => {
    window.Viewer3DManager = new Viewer3DManager();
});
