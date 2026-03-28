/**
 * Pharmacy Module JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initPharmacy();
});

function initPharmacy() {
    // Initialize components based on current page
    initInventorySearch();
    initStockModals();
    initDispenseForm();
    initBillCalculation();
    initBarcodeScanner();
}

// ==================== Inventory Search ====================

function initInventorySearch() {
    const searchInput = document.getElementById('medicineSearch');
    if (!searchInput) return;
    
    let debounceTimer;
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            searchMedicines(this.value);
        }, 300);
    });
}

async function searchMedicines(query) {
    if (query.length < 2) return;
    
    try {
        const response = await fetch(`/pharmacy/api/medicines/search?q=${encodeURIComponent(query)}`);
        const medicines = await response.json();
        
        displaySearchResults(medicines);
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(medicines) {
    const resultsContainer = document.getElementById('searchResults');
    if (!resultsContainer) return;
    
    if (medicines.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted p-3">No medicines found</p>';
        return;
    }
    
    resultsContainer.innerHTML = medicines.map(med => `
        <div class="search-result-item p-2 border-bottom" onclick="selectMedicine(${med.id})">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${med.name}</strong>
                    ${med.generic_name ? `<br><small class="text-muted">${med.generic_name}</small>` : ''}
                </div>
                <div class="text-end">
                    <span class="badge ${med.is_low_stock ? 'bg-warning' : 'bg-success'}">
                        ${med.stock} ${med.unit}
                    </span>
                    <br>
                    <small>₹${med.price}</small>
                </div>
            </div>
        </div>
    `).join('');
    
    resultsContainer.style.display = 'block';
}

// ==================== Stock Management ====================

function initStockModals() {
    // Add stock modal handler
    const addStockForm = document.getElementById('addStockForm');
    if (addStockForm) {
        addStockForm.addEventListener('submit', handleStockUpdate);
    }
}

function showAddStockModal(medicineId, medicineName) {
    document.getElementById('stockMedicineId').value = medicineId;
    document.getElementById('stockMedicineName').textContent = medicineName;
    document.getElementById('stockAction').value = 'add';
    document.getElementById('addStockModalLabel').textContent = 'Add Stock - ' + medicineName;
    
    const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
    modal.show();
}

function showRemoveStockModal(medicineId, medicineName, currentStock) {
    document.getElementById('stockMedicineId').value = medicineId;
    document.getElementById('stockMedicineName').textContent = medicineName;
    document.getElementById('stockAction').value = 'remove';
    document.getElementById('stockQuantity').max = currentStock;
    document.getElementById('addStockModalLabel').textContent = 'Remove Stock - ' + medicineName;
    
    const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
    modal.show();
}

async function handleStockUpdate(e) {
    e.preventDefault();
    
    const form = e.target;
    const medicineId = form.querySelector('#stockMedicineId').value;
    const formData = new FormData(form);
    
    try {
        const response = await fetch(`/pharmacy/medicine/${medicineId}/stock`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('success', result.message);
            
            // Update UI
            updateStockDisplay(medicineId, result.new_stock, result.is_low_stock);
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('addStockModal')).hide();
            form.reset();
        } else {
            showToast('error', result.error || 'Error updating stock');
        }
    } catch (error) {
        console.error('Stock update error:', error);
        showToast('error', 'Error updating stock');
    }
}

function updateStockDisplay(medicineId, newStock, isLowStock) {
    const stockCell = document.querySelector(`[data-medicine-id="${medicineId}"] .stock-value`);
    if (stockCell) {
        stockCell.textContent = newStock;
        
        const badge = stockCell.closest('td').querySelector('.stock-badge');
        if (badge) {
            badge.className = `stock-badge ${isLowStock ? 'low-stock' : 'in-stock'}`;
            badge.textContent = isLowStock ? 'Low Stock' : 'In Stock';
        }
    }
}

// ==================== Dispense Form ====================

function initDispenseForm() {
    const dispenseForm = document.getElementById('dispenseForm');
    if (!dispenseForm) return;
    
    // Quantity change handlers
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            updateDispenseItemTotal(this);
            updateDispenseTotals();
        });
    });
    
    // Discount handler
    const discountInput = document.getElementById('discountAmount');
    if (discountInput) {
        discountInput.addEventListener('input', updateDispenseTotals);
    }
    
    // Insurance checkbox
    const insuranceCheckbox = document.getElementById('useInsurance');
    if (insuranceCheckbox) {
        insuranceCheckbox.addEventListener('change', function() {
            document.getElementById('insuranceDetails').style.display = 
                this.checked ? 'block' : 'none';
            updateDispenseTotals();
        });
    }
}

function updateDispenseItemTotal(input) {
    const row = input.closest('.dispense-item');
    const quantity = parseInt(input.value) || 0;
    const unitPrice = parseFloat(row.dataset.unitPrice) || 0;
    const total = quantity * unitPrice;
    
    row.querySelector('.item-total').textContent = '₹' + total.toFixed(2);
    
    // Check stock availability
    const availableStock = parseInt(row.dataset.availableStock) || 0;
    const stockInfo = row.querySelector('.stock-info');
    
    if (quantity > availableStock) {
        stockInfo.classList.remove('sufficient');
        stockInfo.classList.add('insufficient');
        stockInfo.textContent = `Insufficient! Only ${availableStock} available`;
        input.classList.add('is-invalid');
    } else {
        stockInfo.classList.remove('insufficient');
        stockInfo.classList.add('sufficient');
        stockInfo.textContent = `${availableStock} available`;
        input.classList.remove('is-invalid');
    }
}

function updateDispenseTotals() {
    let subtotal = 0;
    
    document.querySelectorAll('.dispense-item').forEach(item => {
        const quantity = parseInt(item.querySelector('.quantity-input').value) || 0;
        const unitPrice = parseFloat(item.dataset.unitPrice) || 0;
        subtotal += quantity * unitPrice;
    });
    
    const discount = parseFloat(document.getElementById('discountAmount')?.value) || 0;
    const taxRate = 0.05; // 5% tax
    const tax = subtotal * taxRate;
    
    let insuranceCoverage = 0;
    if (document.getElementById('useInsurance')?.checked) {
        const coveragePercent = parseFloat(document.getElementById('insuranceCoverage')?.value) || 0;
        insuranceCoverage = (subtotal - discount + tax) * (coveragePercent / 100);
    }
    
    const total = subtotal - discount + tax - insuranceCoverage;
    
    // Update display
    document.getElementById('subtotalDisplay').textContent = '₹' + subtotal.toFixed(2);
    document.getElementById('discountDisplay').textContent = '₹' + discount.toFixed(2);
    document.getElementById('taxDisplay').textContent = '₹' + tax.toFixed(2);
    
    if (document.getElementById('insuranceDisplay')) {
        document.getElementById('insuranceDisplay').textContent = '₹' + insuranceCoverage.toFixed(2);
    }
    
    document.getElementById('totalDisplay').textContent = '₹' + total.toFixed(2);
    
    // Store values in hidden fields
    document.getElementById('calculatedSubtotal').value = subtotal;
    document.getElementById('calculatedTax').value = tax;
    document.getElementById('calculatedTotal').value = total;
}

// ==================== Bill Calculation ====================

function initBillCalculation() {
    const paymentForm = document.getElementById('paymentForm');
    if (!paymentForm) return;
    
    const amountInput = document.getElementById('amountReceived');
    if (amountInput) {
        amountInput.addEventListener('input', calculateChange);
    }
}

function calculateChange() {
    const totalDue = parseFloat(document.getElementById('totalDue').value) || 0;
    const amountReceived = parseFloat(document.getElementById('amountReceived').value) || 0;
    const change = amountReceived - totalDue;
    
    const changeDisplay = document.getElementById('changeDisplay');
    if (changeDisplay) {
        if (change >= 0) {
            changeDisplay.textContent = '₹' + change.toFixed(2);
            changeDisplay.className = 'text-success';
        } else {
            changeDisplay.textContent = '₹' + Math.abs(change).toFixed(2) + ' due';
            changeDisplay.className = 'text-danger';
        }
    }
}

async function processPayment(billId) {
    const form = document.getElementById('paymentForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch(`/pharmacy/bill/${billId}/payment`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('success', 'Payment processed successfully');
            
            // Update UI
            document.getElementById('paymentStatus').textContent = result.payment_status;
            document.getElementById('paymentStatus').className = 
                `payment-status ${result.payment_status}`;
            
            if (result.change > 0) {
                showToast('info', `Change to return: ₹${result.change.toFixed(2)}`);
            }
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('paymentModal')).hide();
            
            // Refresh page or update UI
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('error', result.error || 'Payment failed');
        }
    } catch (error) {
        console.error('Payment error:', error);
        showToast('error', 'Error processing payment');
    }
}

// ==================== Barcode Scanner ====================

function initBarcodeScanner() {
    const scannerInput = document.getElementById('barcodeInput');
    if (!scannerInput) return;
    
    scannerInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            lookupByBarcode(this.value);
            this.value = '';
        }
    });
}

async function lookupByBarcode(barcode) {
    try {
        const response = await fetch(`/pharmacy/api/barcode/${barcode}`);
        const result = await response.json();
        
        if (result.medicine) {
            addToDispenseList(result.medicine);
        } else {
            showToast('warning', 'Medicine not found');
        }
    } catch (error) {
        console.error('Barcode lookup error:', error);
    }
}

function addToDispenseList(medicine) {
    // Add medicine to dispense form
    const list = document.getElementById('dispenseList');
    if (!list) return;
    
    // Check if already added
    if (document.querySelector(`[data-medicine-id="${medicine.id}"]`)) {
        const input = document.querySelector(`[data-medicine-id="${medicine.id}"] .quantity-input`);
        input.value = parseInt(input.value) + 1;
        updateDispenseItemTotal(input);
        updateDispenseTotals();
        return;
    }
    
    const item = document.createElement('div');
    item.className = 'dispense-item';
    item.dataset.medicineId = medicine.id;
    item.dataset.unitPrice = medicine.price;
    item.dataset.availableStock = medicine.stock;
    
    item.innerHTML = `
        <div class="medicine-info">
            <strong>${medicine.name}</strong>
            <span class="stock-info sufficient">${medicine.stock} available</span>
        </div>
        <div class="quantity-input">
            <input type="number" name="quantity_${medicine.id}" class="form-control quantity-input" 
                   value="1" min="1" max="${medicine.stock}">
            <span>× ₹${medicine.price}</span>
            <span class="item-total">₹${medicine.price.toFixed(2)}</span>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeDispenseItem(this)">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    list.appendChild(item);
    
    // Bind event
    item.querySelector('.quantity-input').addEventListener('change', function() {
        updateDispenseItemTotal(this);
        updateDispenseTotals();
    });
    
    updateDispenseTotals();
}

function removeDispenseItem(button) {
    button.closest('.dispense-item').remove();
    updateDispenseTotals();
}

// ==================== Utility Functions ====================

function showToast(type, message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add to container
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove after hidden
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function printBill(billId) {
    window.open(`/pharmacy/bill/${billId}/print`, '_blank', 'width=400,height=600');
}

function downloadBillPDF(billId) {
    window.location.href = `/pharmacy/bill/${billId}/pdf`;
}

// Export functions for global use
window.showAddStockModal = showAddStockModal;
window.showRemoveStockModal = showRemoveStockModal;
window.processPayment = processPayment;
window.printBill = printBill;
window.downloadBillPDF = downloadBillPDF;
window.removeDispenseItem = removeDispenseItem;