/**
 * Responsive UI Enhancement JavaScript for Horilla HR System
 * Handles mobile navigation, responsive behaviors, and touch interactions
 */

(function() {
    'use strict';

    // ===== CONFIGURATION =====
    const CONFIG = {
        breakpoints: {
            mobile: 576,
            tablet: 768,
            desktop: 992,
            largeDesktop: 1200
        },
        selectors: {
            sidebar: '.oh-sidebar',
            sidebarToggle: '.oh-navbar__toggle-link',
            sidebarOverlay: '.sidebar-overlay',
            navbar: '.oh-navbar',
            modal: '.oh-modal',
            table: '.table-responsive-custom',
            form: '.form-responsive',
            dashboard: '.oh-dashboard'
        },
        classes: {
            show: 'show',
            active: 'active',
            loading: 'loading-skeleton',
            mobileView: 'mobile-view',
            tabletView: 'tablet-view',
            desktopView: 'desktop-view'
        }
    };

    // ===== UTILITY FUNCTIONS =====
    const Utils = {
        // Get current viewport width
        getViewportWidth: () => window.innerWidth || document.documentElement.clientWidth,
        
        // Get current breakpoint
        getCurrentBreakpoint: function() {
            const width = this.getViewportWidth();
            if (width < CONFIG.breakpoints.mobile) return 'xs';
            if (width < CONFIG.breakpoints.tablet) return 'sm';
            if (width < CONFIG.breakpoints.desktop) return 'md';
            if (width < CONFIG.breakpoints.largeDesktop) return 'lg';
            return 'xl';
        },
        
        // Check if mobile view
        isMobile: function() {
            return this.getViewportWidth() < CONFIG.breakpoints.desktop;
        },
        
        // Debounce function
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // Throttle function
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },
        
        // Add/remove class helper
        toggleClass: function(element, className, condition) {
            if (condition) {
                element.classList.add(className);
            } else {
                element.classList.remove(className);
            }
        }
    };

    // ===== MOBILE NAVIGATION =====
    class MobileNavigation {
        constructor() {
            this.sidebar = document.querySelector(CONFIG.selectors.sidebar);
            this.sidebarToggle = document.querySelector(CONFIG.selectors.sidebarToggle);
            this.overlay = null;
            this.isOpen = false;
            
            this.init();
        }
        
        init() {
            if (!this.sidebar || !this.sidebarToggle) return;
            
            this.createOverlay();
            this.bindEvents();
            this.handleResize();
        }
        
        createOverlay() {
            this.overlay = document.createElement('div');
            this.overlay.className = 'sidebar-overlay';
            document.body.appendChild(this.overlay);
        }
        
        bindEvents() {
            // Toggle sidebar
            this.sidebarToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggle();
            });
            
            // Close on overlay click
            this.overlay.addEventListener('click', () => {
                this.close();
            });
            
            // Close on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                }
            });
            
            // Handle window resize
            window.addEventListener('resize', Utils.debounce(() => {
                this.handleResize();
            }, 250));
        }
        
        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        }
        
        open() {
            this.isOpen = true;
            this.sidebar.classList.add(CONFIG.classes.show);
            this.overlay.classList.add(CONFIG.classes.show);
            document.body.style.overflow = 'hidden';
            
            // Focus management
            this.sidebar.setAttribute('aria-hidden', 'false');
            const firstFocusable = this.sidebar.querySelector('a, button, input, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        }
        
        close() {
            this.isOpen = false;
            this.sidebar.classList.remove(CONFIG.classes.show);
            this.overlay.classList.remove(CONFIG.classes.show);
            document.body.style.overflow = '';
            
            // Focus management
            this.sidebar.setAttribute('aria-hidden', 'true');
            this.sidebarToggle.focus();
        }
        
        handleResize() {
            if (!Utils.isMobile() && this.isOpen) {
                this.close();
            }
        }
    }

    // ===== RESPONSIVE TABLES =====
    class ResponsiveTables {
        constructor() {
            this.tables = document.querySelectorAll(CONFIG.selectors.table + ' table');
            this.init();
        }
        
        init() {
            this.tables.forEach(table => {
                this.enhanceTable(table);
            });
            
            window.addEventListener('resize', Utils.debounce(() => {
                this.handleResize();
            }, 250));
        }
        
        enhanceTable(table) {
            // Add data labels for mobile stacking
            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index].textContent.trim());
                    }
                });
            });
            
            // Add responsive wrapper if not exists
            if (!table.closest('.table-responsive-custom')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive-custom';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        }
        
        handleResize() {
            this.tables.forEach(table => {
                const isMobile = Utils.isMobile();
                Utils.toggleClass(table, 'table-stack', isMobile);
            });
        }
    }

    // ===== RESPONSIVE FORMS =====
    class ResponsiveForms {
        constructor() {
            this.forms = document.querySelectorAll(CONFIG.selectors.form);
            this.init();
        }
        
        init() {
            this.forms.forEach(form => {
                this.enhanceForm(form);
            });
        }
        
        enhanceForm(form) {
            // Add responsive classes to form groups
            const formGroups = form.querySelectorAll('.form-group');
            formGroups.forEach(group => {
                // Check if form group should span full width
                const input = group.querySelector('input, select, textarea');
                if (input && (input.type === 'email' || input.type === 'url' || input.tagName === 'TEXTAREA')) {
                    group.classList.add('full-width');
                }
            });
            
            // Enhance file inputs
            const fileInputs = form.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                this.enhanceFileInput(input);
            });
        }
        
        enhanceFileInput(input) {
            const wrapper = document.createElement('div');
            wrapper.className = 'file-upload-area';
            wrapper.innerHTML = `
                <div class="file-upload-content">
                    <i class="fas fa-cloud-upload-alt"></i>
                    <p>Click to select files or drag and drop</p>
                </div>
            `;
            
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
            
            // Handle drag and drop
            wrapper.addEventListener('dragover', (e) => {
                e.preventDefault();
                wrapper.classList.add('dragover');
            });
            
            wrapper.addEventListener('dragleave', () => {
                wrapper.classList.remove('dragover');
            });
            
            wrapper.addEventListener('drop', (e) => {
                e.preventDefault();
                wrapper.classList.remove('dragover');
                input.files = e.dataTransfer.files;
            });
        }
    }

    // ===== RESPONSIVE MODALS =====
    class ResponsiveModals {
        constructor() {
            this.modals = document.querySelectorAll(CONFIG.selectors.modal);
            this.init();
        }
        
        init() {
            this.modals.forEach(modal => {
                this.enhanceModal(modal);
            });
        }
        
        enhanceModal(modal) {
            const dialog = modal.querySelector('.oh-modal__dialog');
            if (!dialog) return;
            
            // Add touch support for mobile
            if ('ontouchstart' in window) {
                let startY = 0;
                let currentY = 0;
                let isDragging = false;
                
                dialog.addEventListener('touchstart', (e) => {
                    startY = e.touches[0].clientY;
                    isDragging = true;
                });
                
                dialog.addEventListener('touchmove', (e) => {
                    if (!isDragging) return;
                    currentY = e.touches[0].clientY;
                    const deltaY = currentY - startY;
                    
                    if (deltaY > 0) {
                        dialog.style.transform = `translateY(${deltaY}px)`;
                    }
                });
                
                dialog.addEventListener('touchend', () => {
                    if (!isDragging) return;
                    isDragging = false;
                    
                    const deltaY = currentY - startY;
                    if (deltaY > 100) {
                        // Close modal if dragged down significantly
                        modal.classList.remove('oh-modal--show');
                    }
                    
                    dialog.style.transform = '';
                });
            }
        }
    }

    // ===== RESPONSIVE DASHBOARD =====
    class ResponsiveDashboard {
        constructor() {
            this.dashboard = document.querySelector(CONFIG.selectors.dashboard);
            this.init();
        }
        
        init() {
            if (!this.dashboard) return;
            
            this.handleResize();
            window.addEventListener('resize', Utils.debounce(() => {
                this.handleResize();
            }, 250));
        }
        
        handleResize() {
            const breakpoint = Utils.getCurrentBreakpoint();
            
            // Update dashboard layout based on breakpoint
            this.dashboard.className = this.dashboard.className.replace(
                /\b(xs|sm|md|lg|xl)-view\b/g, ''
            );
            this.dashboard.classList.add(`${breakpoint}-view`);
            
            // Handle card arrangements
            const cards = this.dashboard.querySelectorAll('.oh-card-dashboard');
            cards.forEach(card => {
                if (Utils.isMobile()) {
                    card.classList.add('mobile-card');
                } else {
                    card.classList.remove('mobile-card');
                }
            });
        }
    }

    // ===== TOUCH ENHANCEMENTS =====
    class TouchEnhancements {
        constructor() {
            this.init();
        }
        
        init() {
            // Add touch class to body if touch device
            if ('ontouchstart' in window) {
                document.body.classList.add('touch-device');
            }
            
            // Enhance button interactions
            this.enhanceButtons();
            
            // Add swipe gestures
            this.addSwipeGestures();
        }
        
        enhanceButtons() {
            const buttons = document.querySelectorAll('.btn, .oh-btn, button');
            buttons.forEach(button => {
                button.addEventListener('touchstart', () => {
                    button.classList.add('touch-active');
                });
                
                button.addEventListener('touchend', () => {
                    setTimeout(() => {
                        button.classList.remove('touch-active');
                    }, 150);
                });
            });
        }
        
        addSwipeGestures() {
            let startX = 0;
            let startY = 0;
            
            document.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            });
            
            document.addEventListener('touchend', (e) => {
                if (!startX || !startY) return;
                
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                
                const deltaX = endX - startX;
                const deltaY = endY - startY;
                
                // Horizontal swipe
                if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                    if (deltaX > 0) {
                        // Swipe right - open sidebar
                        if (Utils.isMobile() && window.mobileNav) {
                            window.mobileNav.open();
                        }
                    } else {
                        // Swipe left - close sidebar
                        if (Utils.isMobile() && window.mobileNav) {
                            window.mobileNav.close();
                        }
                    }
                }
                
                startX = 0;
                startY = 0;
            });
        }
    }

    // ===== LOADING STATES =====
    class LoadingStates {
        constructor() {
            this.init();
        }
        
        init() {
            // Handle HTMX loading states
            document.addEventListener('htmx:beforeRequest', (e) => {
                const target = e.target;
                target.classList.add(CONFIG.classes.loading);
            });
            
            document.addEventListener('htmx:afterRequest', (e) => {
                const target = e.target;
                target.classList.remove(CONFIG.classes.loading);
            });
        }
    }

    // ===== ACCESSIBILITY ENHANCEMENTS =====
    class AccessibilityEnhancements {
        constructor() {
            this.init();
        }
        
        init() {
            // Add focus visible polyfill
            this.addFocusVisible();
            
            // Enhance keyboard navigation
            this.enhanceKeyboardNavigation();
            
            // Add ARIA labels where missing
            this.addAriaLabels();
        }
        
        addFocusVisible() {
            let hadKeyboardEvent = true;
            
            const keyboardThrottledUpdateActiveElement = Utils.throttle(() => {
                hadKeyboardEvent = true;
            }, 100);
            
            document.addEventListener('keydown', keyboardThrottledUpdateActiveElement);
            document.addEventListener('mousedown', () => {
                hadKeyboardEvent = false;
            });
            
            document.addEventListener('focusin', (e) => {
                if (hadKeyboardEvent) {
                    e.target.classList.add('focus-visible');
                }
            });
            
            document.addEventListener('focusout', (e) => {
                e.target.classList.remove('focus-visible');
            });
        }
        
        enhanceKeyboardNavigation() {
            // Add skip links
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = 'Skip to main content';
            skipLink.style.cssText = `
                position: absolute;
                top: -40px;
                left: 6px;
                background: #000;
                color: #fff;
                padding: 8px;
                text-decoration: none;
                z-index: 1000;
            `;
            
            skipLink.addEventListener('focus', () => {
                skipLink.style.top = '6px';
            });
            
            skipLink.addEventListener('blur', () => {
                skipLink.style.top = '-40px';
            });
            
            document.body.insertBefore(skipLink, document.body.firstChild);
        }
        
        addAriaLabels() {
            // Add labels to buttons without text
            const iconButtons = document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])');
            iconButtons.forEach(button => {
                const icon = button.querySelector('ion-icon, i');
                if (icon && !button.textContent.trim()) {
                    const iconName = icon.getAttribute('name') || icon.className;
                    button.setAttribute('aria-label', `Button: ${iconName}`);
                }
            });
        }
    }

    // ===== INITIALIZATION =====
    class ResponsiveUI {
        constructor() {
            this.components = {};
            this.init();
        }
        
        init() {
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    this.initializeComponents();
                });
            } else {
                this.initializeComponents();
            }
        }
        
        initializeComponents() {
            try {
                // Initialize all components
                this.components.mobileNav = new MobileNavigation();
                this.components.responsiveTables = new ResponsiveTables();
                this.components.responsiveForms = new ResponsiveForms();
                this.components.responsiveModals = new ResponsiveModals();
                this.components.responsiveDashboard = new ResponsiveDashboard();
                this.components.touchEnhancements = new TouchEnhancements();
                this.components.loadingStates = new LoadingStates();
                this.components.accessibilityEnhancements = new AccessibilityEnhancements();
                
                // Make mobile nav globally available
                window.mobileNav = this.components.mobileNav;
                
                console.log('Responsive UI initialized successfully');
            } catch (error) {
                console.error('Error initializing Responsive UI:', error);
            }
        }
    }

    // ===== GLOBAL FUNCTIONS =====
    window.handleSidebarToggle = function() {
        if (window.mobileNav) {
            window.mobileNav.toggle();
        }
    };

    // Initialize the responsive UI system
    new ResponsiveUI();

})();