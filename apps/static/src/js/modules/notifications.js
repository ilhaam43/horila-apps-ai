/**
 * Notification System with Persistent State Management
 * Handles navbar notifications with localStorage persistence
 */

class NotificationManager {
    constructor() {
        this.storageKey = 'oh_notifications_state';
        this.init();
    }

    init() {
        // Initialize Alpine.js data for notifications
        document.addEventListener('alpine:init', () => {
            Alpine.data('notificationManager', () => ({
                openNotification: false,
                markRead: this.getStoredState('markRead', false),
                visible: this.getStoredState('visible', true),
                
                init() {
                    // Restore state from localStorage
                    this.markRead = this.getStoredState('markRead', false);
                    this.visible = this.getStoredState('visible', true);
                },

                toggleNotification() {
                    this.openNotification = !this.openNotification;
                },

                markAsRead() {
                    this.markRead = true;
                    this.saveState('markRead', true);
                },

                clearNotifications() {
                    this.visible = false;
                    this.saveState('visible', false);
                    // Also close the notification panel
                    this.openNotification = false;
                },

                resetNotifications() {
                    this.markRead = false;
                    this.visible = true;
                    this.saveState('markRead', false);
                    this.saveState('visible', true);
                },

                getStoredState(key, defaultValue) {
                    try {
                        const stored = localStorage.getItem(`${this.storageKey}_${key}`);
                        return stored !== null ? JSON.parse(stored) : defaultValue;
                    } catch (e) {
                        console.warn('Error reading notification state:', e);
                        return defaultValue;
                    }
                },

                saveState(key, value) {
                    try {
                        localStorage.setItem(`${this.storageKey}_${key}`, JSON.stringify(value));
                    } catch (e) {
                        console.warn('Error saving notification state:', e);
                    }
                }
            }));
        });

        // Add global methods for external access
        window.NotificationManager = {
            reset: () => this.resetAllNotifications(),
            clear: () => this.clearAllNotifications(),
            getState: () => this.getAllStates()
        };
    }

    getStoredState(key, defaultValue) {
        try {
            const stored = localStorage.getItem(`${this.storageKey}_${key}`);
            return stored !== null ? JSON.parse(stored) : defaultValue;
        } catch (e) {
            console.warn('Error reading notification state:', e);
            return defaultValue;
        }
    }

    saveState(key, value) {
        try {
            localStorage.setItem(`${this.storageKey}_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('Error saving notification state:', e);
        }
    }

    resetAllNotifications() {
        localStorage.removeItem(`${this.storageKey}_markRead`);
        localStorage.removeItem(`${this.storageKey}_visible`);
        // Trigger page reload to reset Alpine.js state
        window.location.reload();
    }

    clearAllNotifications() {
        this.saveState('visible', false);
        this.saveState('markRead', true);
    }

    getAllStates() {
        return {
            markRead: this.getStoredState('markRead', false),
            visible: this.getStoredState('visible', true)
        };
    }
}

// Initialize the notification manager
const notificationManager = new NotificationManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
}