/**
 * Lazy Loading System untuk Optimasi Performa
 * Memuat library besar hanya saat dibutuhkan
 */

class LazyLoader {
    constructor() {
        this.loadedLibraries = new Set();
        this.loadingPromises = new Map();
    }

    /**
     * Load PivotTable libraries on demand
     */
    async loadPivotTable() {
        if (this.loadedLibraries.has('pivottable')) {
            return Promise.resolve();
        }

        if (this.loadingPromises.has('pivottable')) {
            return this.loadingPromises.get('pivottable');
        }

        const loadPromise = this.loadScripts([
            '/static/build/js/pivottable.min.js',
            '/static/build/js/pivottable_plot.min.js',
            '/static/build/js/pivottable_ploty.min.js',
            '/static/build/js/pivottable_excel.min.js'
        ]).then(() => {
            this.loadedLibraries.add('pivottable');
            console.log('PivotTable libraries loaded successfully');
        });

        this.loadingPromises.set('pivottable', loadPromise);
        return loadPromise;
    }

    /**
     * Load Ionicons on demand
     */
    async loadIonicons() {
        if (this.loadedLibraries.has('ionicons')) {
            return Promise.resolve();
        }

        if (this.loadingPromises.has('ionicons')) {
            return this.loadingPromises.get('ionicons');
        }

        const loadPromise = this.loadScript('/static/images/ionicons/ui_icons/ionicons/ionicons.esm.js', 'module')
            .then(() => {
                this.loadedLibraries.add('ionicons');
                console.log('Ionicons loaded successfully');
            });

        this.loadingPromises.set('ionicons', loadPromise);
        return loadPromise;
    }

    /**
     * Load Chart.js libraries on demand
     */
    async loadCharts() {
        if (this.loadedLibraries.has('charts')) {
            return Promise.resolve();
        }

        if (this.loadingPromises.has('charts')) {
            return this.loadingPromises.get('charts');
        }

        const loadPromise = this.loadScripts([
            '/static/build/js/chart.min.js',
            '/static/build/js/chartjs-adapter-date-fns.bundle.min.js'
        ]).then(() => {
            this.loadedLibraries.add('charts');
            console.log('Chart libraries loaded successfully');
        });

        this.loadingPromises.set('charts', loadPromise);
        return loadPromise;
    }

    /**
     * Load single script
     */
    loadScript(src, type = 'text/javascript') {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.type = type;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Load multiple scripts sequentially
     */
    async loadScripts(sources) {
        for (const src of sources) {
            await this.loadScript(src);
        }
    }

    /**
     * Preload critical resources with low priority
     */
    preloadCritical() {
        const criticalResources = [
            '/static/build/js/web.frontend.min.js',
            '/static/htmx/htmx.min.js',
            '/static/build/js/summernote-lite.min.js'
        ];

        criticalResources.forEach(src => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'script';
            link.href = src;
            document.head.appendChild(link);
        });
    }
}

// Global instance
window.lazyLoader = new LazyLoader();

// Auto-preload critical resources
document.addEventListener('DOMContentLoaded', () => {
    window.lazyLoader.preloadCritical();
});

// Intersection Observer untuk lazy loading berdasarkan visibility
class VisibilityLazyLoader {
    constructor() {
        this.observer = new IntersectionObserver(this.handleIntersection.bind(this), {
            threshold: 0.1,
            rootMargin: '50px'
        });
    }

    observe(element, libraryName) {
        element.dataset.lazyLibrary = libraryName;
        this.observer.observe(element);
    }

    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const libraryName = entry.target.dataset.lazyLibrary;
                this.loadLibrary(libraryName);
                this.observer.unobserve(entry.target);
            }
        });
    }

    loadLibrary(libraryName) {
        switch (libraryName) {
            case 'pivottable':
                window.lazyLoader.loadPivotTable();
                break;
            case 'charts':
                window.lazyLoader.loadCharts();
                break;
            case 'ionicons':
                window.lazyLoader.loadIonicons();
                break;
        }
    }
}

// Global visibility loader
window.visibilityLoader = new VisibilityLazyLoader();