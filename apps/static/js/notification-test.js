// Notification Test Helper
// Add this script to test notification functionality

// Function to reset all notifications (for testing)
function resetNotifications() {
    if (window.NotificationManager) {
        window.NotificationManager.reset();
    } else {
        // Fallback if NotificationManager is not available
        localStorage.removeItem('oh_notifications_state_markRead');
        localStorage.removeItem('oh_notifications_state_visible');
        window.location.reload();
    }
}

// Function to clear notifications (for testing)
function clearNotifications() {
    if (window.NotificationManager) {
        window.NotificationManager.clear();
    } else {
        // Fallback
        localStorage.setItem('oh_notifications_state_visible', 'false');
        localStorage.setItem('oh_notifications_state_markRead', 'true');
    }
}

// Function to check notification state (for debugging)
function checkNotificationState() {
    const state = {
        markRead: localStorage.getItem('oh_notifications_state_markRead'),
        visible: localStorage.getItem('oh_notifications_state_visible')
    };
    console.log('Notification State:', state);
    return state;
}

// Add global functions for easy testing
window.resetNotifications = resetNotifications;
window.clearNotifications = clearNotifications;
window.checkNotificationState = checkNotificationState;

// Add console message for testing
console.log('Notification Test Helper loaded. Available functions:');
console.log('- resetNotifications(): Reset all notification states');
console.log('- clearNotifications(): Clear/hide all notifications');
console.log('- checkNotificationState(): Check current notification state');