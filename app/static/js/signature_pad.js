/**
 * Digital Signature Pad JavaScript
 */

class SignaturePad {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;
        this.isEmpty = true;
        
        this.options = {
            lineWidth: 2,
            lineColor: '#000000',
            backgroundColor: '#ffffff',
            ...options
        };
        
        this.init();
    }
    
    init() {
        this.resizeCanvas();
        this.setupEventListeners();
        this.clear();
        
        // Handle window resize
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        // Store current content
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        // Set display size
        this.canvas.style.width = '100%';
        this.canvas.style.height = '200px';
        
        // Set actual size in memory
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = 200 * dpr;
        
        // Scale context
        this.ctx.scale(dpr, dpr);
        
        // Restore content
        this.ctx.putImageData(imageData, 0, 0);
        
        // Reset styles
        this.ctx.strokeStyle = this.options.lineColor;
        this.ctx.lineWidth = this.options.lineWidth;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
    }
    
    setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
        this.canvas.addEventListener('mousemove', (e) => this.draw(e));
        this.canvas.addEventListener('mouseup', () => this.stopDrawing());
        this.canvas.addEventListener('mouseout', () => this.stopDrawing());
        
        // Touch events
        this.canvas.addEventListener('touchstart', (e) => this.handleTouch(e, 'start'));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouch(e, 'move'));
        this.canvas.addEventListener('touchend', () => this.stopDrawing());
    }
    
    handleTouch(e, action) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent(action === 'start' ? 'mousedown' : 'mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        
        if (action === 'start') {
            this.startDrawing(mouseEvent);
        } else {
            this.draw(mouseEvent);
        }
    }
    
    getPosition(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    startDrawing(e) {
        this.isDrawing = true;
        const pos = this.getPosition(e);
        this.lastX = pos.x;
        this.lastY = pos.y;
        
        // Start a new path
        this.ctx.beginPath();
        this.ctx.moveTo(pos.x, pos.y);
    }
    
    draw(e) {
        if (!this.isDrawing) return;
        
        const pos = this.getPosition(e);
        
        this.ctx.lineTo(pos.x, pos.y);
        this.ctx.stroke();
        
        this.lastX = pos.x;
        this.lastY = pos.y;
        this.isEmpty = false;
    }
    
    stopDrawing() {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.ctx.closePath();
        }
    }
    
    clear() {
        this.ctx.fillStyle = this.options.backgroundColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.isEmpty = true;
    }
    
    toDataURL(type = 'image/png') {
        return this.canvas.toDataURL(type);
    }
    
    toBlob(callback, type = 'image/png') {
        this.canvas.toBlob(callback, type);
    }
    
    isEmptySignature() {
        return this.isEmpty;
    }
    
    setColor(color) {
        this.options.lineColor = color;
        this.ctx.strokeStyle = color;
    }
    
    setLineWidth(width) {
        this.options.lineWidth = width;
        this.ctx.lineWidth = width;
    }
}

// Signature Modal Controller
class SignatureModalController {
    constructor(modalId, canvasId, options = {}) {
        this.modal = document.getElementById(modalId);
        this.canvas = document.getElementById(canvasId);
        this.signaturePad = null;
        this.options = options;
        
        if (this.canvas) {
            this.init();
        }
    }
    
    init() {
        // Initialize signature pad when modal opens
        if (this.modal) {
            this.modal.addEventListener('shown.bs.modal', () => {
                if (!this.signaturePad) {
                    this.signaturePad = new SignaturePad(this.canvas, this.options);
                }
            });
        } else {
            // Direct initialization without modal
            this.signaturePad = new SignaturePad(this.canvas, this.options);
        }
        
        // Clear button
        const clearBtn = document.getElementById('clearSignature');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }
        
        // Save button
        const saveBtn = document.getElementById('saveSignature');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.save());
        }
        
        // Color picker
        const colorPicker = document.getElementById('signatureColor');
        if (colorPicker) {
            colorPicker.addEventListener('change', (e) => {
                if (this.signaturePad) {
                    this.signaturePad.setColor(e.target.value);
                }
            });
        }
        
        // Line width
        const lineWidth = document.getElementById('signatureLineWidth');
        if (lineWidth) {
            lineWidth.addEventListener('input', (e) => {
                if (this.signaturePad) {
                    this.signaturePad.setLineWidth(parseInt(e.target.value));
                }
            });
        }
    }
    
    clear() {
        if (this.signaturePad) {
            this.signaturePad.clear();
        }
    }
    
    save() {
        if (!this.signaturePad) return;
        
        if (this.signaturePad.isEmptySignature()) {
            alert('Please draw your signature first');
            return;
        }
        
        const dataURL = this.signaturePad.toDataURL();
        
        // Set to hidden input
        const hiddenInput = document.getElementById('signatureData');
        if (hiddenInput) {
            hiddenInput.value = dataURL;
        }
        
        // Show preview
        const preview = document.getElementById('signaturePreview');
        if (preview) {
            preview.src = dataURL;
            preview.style.display = 'block';
        }
        
        // Close modal if exists
        if (this.modal) {
            bootstrap.Modal.getInstance(this.modal).hide();
        }
        
        // Trigger callback if defined
        if (this.options.onSave) {
            this.options.onSave(dataURL);
        }
        
        return dataURL;
    }
    
    getDataURL() {
        return this.signaturePad ? this.signaturePad.toDataURL() : null;
    }
    
    isEmpty() {
        return this.signaturePad ? this.signaturePad.isEmptySignature() : true;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize for prescription signing page
    const signatureCanvas = document.getElementById('signatureCanvas');
    if (signatureCanvas) {
        window.signatureController = new SignatureModalController(
            'signatureModal',
            'signatureCanvas',
            {
                lineWidth: 2,
                lineColor: '#000080',
                onSave: function(dataURL) {
                    console.log('Signature saved');
                }
            }
        );
    }
    
    // Direct signature pad (no modal)
    const directSignatureCanvas = document.getElementById('directSignatureCanvas');
    if (directSignatureCanvas) {
        window.directSignaturePad = new SignaturePad(directSignatureCanvas, {
            lineWidth: 2,
            lineColor: '#000080'
        });
        
        // Clear button for direct pad
        const clearBtn = document.getElementById('clearDirectSignature');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => window.directSignaturePad.clear());
        }
    }
});

// Form submission handler for prescription signing
function handlePrescriptionSign(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        const signatureData = document.getElementById('signatureData')?.value;
        
        if (!signatureData) {
            e.preventDefault();
            alert('Please add your digital signature before submitting');
            return false;
        }
        
        return true;
    });
}

// Export for global use
window.SignaturePad = SignaturePad;
window.SignatureModalController = SignatureModalController;
window.handlePrescriptionSign = handlePrescriptionSign;