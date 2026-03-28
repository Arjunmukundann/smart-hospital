/**
 * Smart Hospital Platform - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all features
    initFlashMessages();
    initFormValidation();
    initLoadingSpinner();
    initTooltips();
    initPasswordToggle();
});

/**
 * Flash Messages - Auto-hide after 5 seconds
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.classList.remove('show');
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });
}

/**
 * Form Validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

/**
 * Loading Spinner for AJAX Requests
 */
function initLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    
    if (spinner) {
        // Show spinner on form submit
        document.querySelectorAll('form').forEach(function(form) {
            form.addEventListener('submit', function() {
                if (form.checkValidity()) {
                    spinner.style.display = 'flex';
                }
            });
        });
    }
}

/**
 * Initialize Bootstrap Tooltips
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Password Visibility Toggle
 */
function initPasswordToggle() {
    document.querySelectorAll('.toggle-password').forEach(function(button) {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

/**
 * Show Loading Spinner
 */
function showLoading() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = 'flex';
    }
}

/**
 * Hide Loading Spinner
 */
function hideLoading() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

/**
 * Show Alert Message
 */
function showAlert(message, type = 'info') {
    const container = document.querySelector('.flash-container') || createFlashContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show flash-message`;
    alert.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alert);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        alert.classList.remove('show');
        setTimeout(function() {
            alert.remove();
        }, 300);
    }, 5000);
}

/**
 * Create Flash Container if not exists
 */
function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
    return container;
}

/**
 * AJAX Helper Function
 */
function ajaxRequest(url, method, data, successCallback, errorCallback) {
    showLoading();
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: data ? JSON.stringify(data) : null
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (successCallback) successCallback(data);
    })
    .catch(error => {
        hideLoading();
        if (errorCallback) {
            errorCallback(error);
        } else {
            showAlert('An error occurred. Please try again.', 'danger');
        }
    });
}

/**
 * Get CSRF Token
 */
function getCSRFToken() {
    const tokenInput = document.querySelector('input[name="csrf_token"]');
    return tokenInput ? tokenInput.value : '';
}

/**
 * Validate Prescription
 */
function validatePrescription(patientId, medicines, callback) {
    ajaxRequest(
        '/api/prescription/validate',
        'POST',
        { patient_id: patientId, medicines: medicines },
        function(data) {
            if (callback) callback(data);
        }
    );
}

/**
 * Check Meal Safety
 */
function checkMealSafety(meal, medicines, callback) {
    ajaxRequest(
        '/api/meal/check',
        'POST',
        { meal: meal, medicines: medicines },
        function(data) {
            if (callback) callback(data);
        }
    );
}

/**
 * Search Patients
 */
function searchPatients(query, callback) {
    if (query.length < 2) {
        if (callback) callback([]);
        return;
    }
    
    fetch(`/api/patient/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (callback) callback(data);
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

/**
 * Search Medicines
 */
function searchMedicines(query, callback) {
    if (query.length < 2) {
        if (callback) callback([]);
        return;
    }
    
    fetch(`/api/medicine/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (callback) callback(data);
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

/**
 * Format Date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Debounce Function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Copy to Clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('Copied to clipboard!', 'success');
    }).catch(function() {
        showAlert('Failed to copy', 'danger');
    });
}

/**
 * Print Element
 */
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>Print</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { padding: 20px; }
                @media print { body { -webkit-print-color-adjust: exact; } }
            </style>
        </head>
        <body>
            ${element.innerHTML}
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.onload = function() {
        printWindow.print();
        printWindow.close();
    };
}

console.log('🏥 Smart Hospital Platform loaded successfully!');