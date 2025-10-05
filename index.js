// index.js - Clean standalone version
class SplineViewer {
    constructor() {
        this.splineRuntime = null;
        this.isInitialized = false;
    }

    async init() {
        try {
            // Load Spline runtime
            const { Application } = await import('https://cdn.jsdelivr.net/npm/@splinetool/runtime@1.3.9/build/runtime.js');
            
            // Initialize Spline application
            this.splineRuntime = new Application();
            await this.splineRuntime.load('https://prod.spline.design/6Wq1Q7YGyM0bVzZz/scene.splinecode');
            
            // Append to DOM
            const canvas = this.splineRuntime.canvas;
            canvas.style.width = '100%';
            canvas.style.height = '100%';
            canvas.style.display = 'block';
            
            const container = document.getElementById('spline-container') || this.createContainer();
            container.appendChild(canvas);
            
            this.isInitialized = true;
            console.log('Spline viewer initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Spline viewer:', error);
        }
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'spline-container';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.zIndex = '0';
        document.body.appendChild(container);
        return container;
    }

    // Add methods to control the Spline scene
    setBackgroundColor(color) {
        if (this.splineRuntime && this.splineRuntime._scene) {
            this.splineRuntime._scene.background = color;
        }
    }

    // Clean up method
    destroy() {
        if (this.splineRuntime) {
            const canvas = this.splineRuntime.canvas;
            if (canvas && canvas.parentNode) {
                canvas.parentNode.removeChild(canvas);
            }
            this.splineRuntime = null;
        }
        this.isInitialized = false;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const splineViewer = new SplineViewer();
    splineViewer.init();
    
    // Make globally available for control
    window.splineViewer = splineViewer;
});

// Alternative initialization for modern browsers
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSpline);
} else {
    initSpline();
}

async function initSpline() {
    try {
        const { Application } = await import('https://cdn.jsdelivr.net/npm/@splinetool/runtime@1.3.9/build/runtime.js');
        const canvas = document.getElementById('canvas3d');
        
        // Start loading the runtime immediately
        const runtimePromise = Application.start(canvas);
        
        // Load the scene
        const runtime = await runtimePromise;
        await runtime.load('https://prod.spline.design/6Wq1Q7YGyM0bVzZz/scene.splinecode');
        
        console.log('Spline scene loaded successfully');
        
    } catch (error) {
        console.error('Error loading Spline scene:', error);
    }
}

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SplineViewer };
}