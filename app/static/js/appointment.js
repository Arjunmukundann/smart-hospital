/**
 * Appointment Booking JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initAppointmentBooking();
});

function initAppointmentBooking() {
    const doctorSelect = document.getElementById('doctorSelect');
    const dateInput = document.getElementById('appointmentDate');
    const timeSlotContainer = document.getElementById('timeSlots');
    const appointmentTypeInputs = document.querySelectorAll('input[name="appointment_type"]');
    
    if (!doctorSelect || !dateInput) return;
    
    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);
    
    // Event listeners
    doctorSelect.addEventListener('change', handleDoctorChange);
    dateInput.addEventListener('change', loadAvailableSlots);
    appointmentTypeInputs.forEach(input => {
        input.addEventListener('change', loadAvailableSlots);
    });
    
    // Specialty filter
    const specialtyFilter = document.getElementById('specialtyFilter');
    if (specialtyFilter) {
        specialtyFilter.addEventListener('change', filterDoctors);
    }
}

function handleDoctorChange() {
    const doctorId = document.getElementById('doctorSelect').value;
    if (!doctorId) return;
    
    // Load doctor info
    loadDoctorInfo(doctorId);
    
    // Clear and reload slots if date is selected
    const dateInput = document.getElementById('appointmentDate');
    if (dateInput.value) {
        loadAvailableSlots();
    }
}

async function loadDoctorInfo(doctorId) {
    const infoContainer = document.getElementById('doctorInfo');
    if (!infoContainer) return;
    
    try {
        const response = await fetch(`/appointment/api/doctor-schedule/${doctorId}`);
        const data = await response.json();
        
        if (data.doctor) {
            infoContainer.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <img src="${data.doctor.profile_picture || '/static/images/default_avatar.png'}" 
                                 class="rounded-circle me-3" width="60" height="60" alt="">
                            <div>
                                <h5 class="mb-1">Dr. ${data.doctor.name}</h5>
                                <p class="mb-0 text-muted">${data.doctor.specialization}</p>
                            </div>
                        </div>
                        <div class="row text-center">
                            <div class="col-6">
                                <div class="border rounded p-2">
                                    <i class="fas fa-user-md text-primary"></i>
                                    <div class="small">In-Person</div>
                                    <strong>₹${data.doctor.consultation_fee || 0}</strong>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="border rounded p-2">
                                    <i class="fas fa-video text-success"></i>
                                    <div class="small">Video</div>
                                    <strong>₹${data.doctor.video_consultation_fee || 0}</strong>
                                </div>
                            </div>
                        </div>
                        ${data.doctor.is_available_online ? 
                            '<div class="mt-2 text-center"><span class="badge bg-success">Video Consultation Available</span></div>' : 
                            '<div class="mt-2 text-center"><span class="badge bg-secondary">In-Person Only</span></div>'
                        }
                    </div>
                </div>
            `;
            infoContainer.style.display = 'block';
            
            // Update video option availability
            const videoOption = document.getElementById('typeVideo');
            if (videoOption) {
                videoOption.disabled = !data.doctor.is_available_online;
                if (!data.doctor.is_available_online && videoOption.checked) {
                    document.getElementById('typeInPerson').checked = true;
                }
            }
        }
    } catch (error) {
        console.error('Error loading doctor info:', error);
    }
}

async function loadAvailableSlots() {
    const doctorId = document.getElementById('doctorSelect').value;
    const date = document.getElementById('appointmentDate').value;
    const appointmentType = document.querySelector('input[name="appointment_type"]:checked')?.value || 'in_person';
    
    const slotsContainer = document.getElementById('timeSlots');
    if (!slotsContainer) return;
    
    if (!doctorId || !date) {
        slotsContainer.innerHTML = '<p class="text-muted">Please select a doctor and date</p>';
        return;
    }
    
    slotsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 mb-0">Loading available slots...</p>
        </div>
    `;
    
    try {
        const response = await fetch(
            `/appointment/api/available-slots?doctor_id=${doctorId}&date=${date}&type=${appointmentType}`
        );
        const data = await response.json();
        
        if (data.error) {
            slotsContainer.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
            return;
        }
        
        if (!data.slots || data.slots.length === 0) {
            slotsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No available slots for this date. Please try another date.
                </div>
            `;
            return;
        }
        
        // Group slots by morning, afternoon, evening
        const morning = data.slots.filter(s => {
            const hour = parseInt(s.time.split(':')[0]);
            return hour < 12;
        });
        const afternoon = data.slots.filter(s => {
            const hour = parseInt(s.time.split(':')[0]);
            return hour >= 12 && hour < 17;
        });
        const evening = data.slots.filter(s => {
            const hour = parseInt(s.time.split(':')[0]);
            return hour >= 17;
        });
        
        let html = '';
        
        if (morning.length > 0) {
            html += renderSlotGroup('Morning', morning, 'sun');
        }
        if (afternoon.length > 0) {
            html += renderSlotGroup('Afternoon', afternoon, 'cloud-sun');
        }
        if (evening.length > 0) {
            html += renderSlotGroup('Evening', evening, 'moon');
        }
        
        slotsContainer.innerHTML = html;
        
        // Add click handlers to slots
        document.querySelectorAll('.time-slot-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.time-slot-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                document.getElementById('appointmentTime').value = this.dataset.time;
                updateBookingSummary();
            });
        });
        
    } catch (error) {
        console.error('Error loading slots:', error);
        slotsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>
                Error loading available slots. Please try again.
            </div>
        `;
    }
}

function renderSlotGroup(title, slots, icon) {
    return `
        <div class="slot-group mb-3">
            <h6 class="text-muted mb-2">
                <i class="fas fa-${icon} me-2"></i>${title}
            </h6>
            <div class="d-flex flex-wrap gap-2">
                ${slots.map(slot => `
                    <button type="button" 
                            class="btn btn-outline-primary time-slot-btn" 
                            data-time="${slot.time}">
                        ${slot.display}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
}

function filterDoctors() {
    const specialty = document.getElementById('specialtyFilter').value;
    const doctorSelect = document.getElementById('doctorSelect');
    const options = doctorSelect.querySelectorAll('option');
    
    options.forEach(option => {
        if (!option.value) return; // Skip placeholder
        
        const optionSpecialty = option.dataset.specialty || '';
        if (!specialty || optionSpecialty.toLowerCase().includes(specialty.toLowerCase())) {
            option.style.display = '';
        } else {
            option.style.display = 'none';
        }
    });
    
    // Reset selection if current is hidden
    if (doctorSelect.selectedOptions[0]?.style.display === 'none') {
        doctorSelect.value = '';
    }
}

function updateBookingSummary() {
    const summary = document.getElementById('bookingSummary');
    if (!summary) return;
    
    const doctorSelect = document.getElementById('doctorSelect');
    const date = document.getElementById('appointmentDate').value;
    const time = document.getElementById('appointmentTime').value;
    const type = document.querySelector('input[name="appointment_type"]:checked')?.value;
    
    if (doctorSelect.value && date && time) {
        const doctorName = doctorSelect.options[doctorSelect.selectedIndex].text;
        const formattedDate = new Date(date).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        summary.innerHTML = `
            <div class="card bg-light">
                <div class="card-body">
                    <h6 class="card-title">
                        <i class="fas fa-calendar-check text-success me-2"></i>
                        Booking Summary
                    </h6>
                    <table class="table table-sm table-borderless mb-0">
                        <tr>
                            <td class="text-muted">Doctor:</td>
                            <td><strong>${doctorName}</strong></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Date:</td>
                            <td><strong>${formattedDate}</strong></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Time:</td>
                            <td><strong>${formatTime(time)}</strong></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Type:</td>
                            <td>
                                <strong>
                                    ${type === 'video' ? 
                                        '<i class="fas fa-video text-success"></i> Video Consultation' : 
                                        '<i class="fas fa-user-md text-primary"></i> In-Person Visit'
                                    }
                                </strong>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
        `;
        summary.style.display = 'block';
        
        // Enable submit button
        const submitBtn = document.getElementById('submitBooking');
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
}

function formatTime(time24) {
    const [hours, minutes] = time24.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
}

// Calendar view functions
function initCalendarView() {
    const calendar = document.getElementById('appointmentCalendar');
    if (!calendar) return;
    
    // Initialize calendar (using a library like FullCalendar or custom implementation)
    renderCalendar(new Date());
}

function renderCalendar(date) {
    // Basic calendar rendering
    const calendar = document.getElementById('appointmentCalendar');
    const year = date.getFullYear();
    const month = date.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDay = firstDay.getDay();
    
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    
    let html = `
        <div class="calendar-header d-flex justify-content-between align-items-center mb-3">
            <button class="btn btn-sm btn-outline-secondary" onclick="changeMonth(-1)">
                <i class="fas fa-chevron-left"></i>
            </button>
            <h5 class="mb-0">${monthNames[month]} ${year}</h5>
            <button class="btn btn-sm btn-outline-secondary" onclick="changeMonth(1)">
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
        <table class="table table-bordered calendar-table">
            <thead>
                <tr>
                    <th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    let day = 1;
    const today = new Date();
    
    for (let i = 0; i < 6; i++) {
        html += '<tr>';
        for (let j = 0; j < 7; j++) {
            if (i === 0 && j < startingDay) {
                html += '<td class="empty"></td>';
            } else if (day > daysInMonth) {
                html += '<td class="empty"></td>';
            } else {
                const cellDate = new Date(year, month, day);
                const isToday = cellDate.toDateString() === today.toDateString();
                const isPast = cellDate < today && !isToday;
                
                html += `
                    <td class="${isToday ? 'today' : ''} ${isPast ? 'past' : 'selectable'}"
                        ${!isPast ? `onclick="selectDate('${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}')"` : ''}>
                        ${day}
                    </td>
                `;
                day++;
            }
        }
        html += '</tr>';
        if (day > daysInMonth) break;
    }
    
    html += '</tbody></table>';
    calendar.innerHTML = html;
}

let currentCalendarDate = new Date();

function changeMonth(delta) {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() + delta);
    renderCalendar(currentCalendarDate);
}

function selectDate(dateString) {
    document.getElementById('appointmentDate').value = dateString;
    
    // Highlight selected date
    document.querySelectorAll('.calendar-table td').forEach(td => {
        td.classList.remove('selected');
    });
    event.target.classList.add('selected');
    
    // Load slots
    loadAvailableSlots();
}