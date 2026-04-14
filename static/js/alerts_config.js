/**
 * alerts_config.js
 * Automatically dismisses flash messages and alerts after a specified timeout.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Select all alert and message elements
    const alerts = document.querySelectorAll('.alert, .message');
    
    // Function to dismiss an element
    const dismissElement = (el) => {
        if (!el) return;
        
        // Add fade-out effect
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-10px)';
        
        // Remove from DOM after transition
        setTimeout(() => {
            if (el.parentNode) {
                el.remove();
            }
        }, 500);
    };

    // Auto-dismiss existing alerts after 5 seconds
    alerts.forEach(alert => {
        setTimeout(() => {
            dismissElement(alert);
        }, 5000);
    });

    // Provide a global function to handle dynamically added alerts
    window.autoDismissAlert = (el, timeout = 5000) => {
        setTimeout(() => {
            dismissElement(el);
        }, timeout);
    };

    // MutationObserver to catch alerts added dynamically (e.g., via AJAX/Success Modals)
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    if (node.classList.contains('alert') || node.classList.contains('message')) {
                        window.autoDismissAlert(node);
                    } else {
                        // Also check children
                        const subAlerts = node.querySelectorAll('.alert, .message');
                        subAlerts.forEach(sub => window.autoDismissAlert(sub));
                    }
                }
            });
        });
    });

    // Start observing the body for new alerts
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    }
});

// Global Custom Modal Functions
let confirmCallback = null;
let alertCallback = null;

window.showCustomAlert = function(message, title = 'Notification', onOk = null) {
    const modal = document.getElementById('customAlertModal');
    if (!modal) return;
    
    document.getElementById('customAlertTitle').textContent = title;
    document.getElementById('customAlertMessage').textContent = message;
    
    alertCallback = onOk;
    modal.style.display = 'flex';
    modal.classList.add('active');
};

window.closeCustomAlert = function() {
    const modal = document.getElementById('customAlertModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
    if (alertCallback) {
        alertCallback();
        alertCallback = null;
    }
};

window.showCustomConfirm = function(message, title = 'Confirm', onConfirm, isDanger = false) {
    const modal = document.getElementById('customConfirmModal');
    if (!modal) return;
    
    document.getElementById('customConfirmTitle').textContent = title;
    document.getElementById('customConfirmMessage').textContent = message;
    
    const okBtn = document.getElementById('customConfirmOkBtn');
    okBtn.textContent = title.includes('Delete') ? 'Delete' : (title.includes('Hide') ? 'Hide' : 'Confirm');
    
    if (isDanger) {
        okBtn.classList.add('danger');
        okBtn.classList.remove('primary');
    } else {
        okBtn.classList.remove('danger');
        okBtn.classList.add('primary');
    }
    
    confirmCallback = onConfirm;
    modal.style.display = 'flex';
    modal.classList.add('active');
};

window.closeCustomConfirm = function(result) {
    const modal = document.getElementById('customConfirmModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
    if (confirmCallback) {
        confirmCallback(result);
        confirmCallback = null;
    }
};
