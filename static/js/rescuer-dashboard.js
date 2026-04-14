document.addEventListener('DOMContentLoaded', function() {
    // Main navigation tabs
    const mainTabBtns = document.querySelectorAll('.nav-tabs .tab-btn');
    const mainTabPanes = document.querySelectorAll('.tab-content .tab-pane');
    
    // Map elements
    const getCurrentLocationBtn = document.getElementById('getCurrentLocation');
    const refreshReportsBtn = document.getElementById('refreshReports');
    let map, marker, circle, zoomed;
    let userPinnedLocations = []; // Store user pinned locations
    let allReports = []; // Store all reports
    
    // Search functionality
    const searchInput = document.querySelector('.search-input');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const statusFilter = document.getElementById('statusFilter');
    const animalFilter = document.getElementById('animalFilter');
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Load all reports from API
    async function loadAllReports() {
        try {
            const response = await fetch('/api/reports/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                allReports = result.reports;
                displayReportsInTabs();
                updateReportCounts();
                addReportMarkersToMap();
            } else {
                console.error('Error loading reports:', result.error);
            }
        } catch (error) {
            console.error('Error loading reports:', error);
        }
    }
    
    // Display reports in appropriate tabs
    function displayReportsInTabs() {
        // Priority: currentProfile (from loadUserProfile) > window.currentRescuerContext
        const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : (window.currentRescuerContext || {});
        const myId = userCtx.id;
        
        // Filter out hidden, and trashed reports from normal views
        const visibleReports = allReports.filter(r => {
            // Hide reports that this rescuer has trashed (assigned/completed ones deleted)
            if (r.is_deleted_by_rescuer === true) return false;
            // Hide reports that this rescuer has hidden (pending ones "trashed")
            const hiddenBy = r.hidden_by_rescuers || [];
            if (hiddenBy.includes(myId)) return false;
            
            // Hide reports that are permanently hidden for this rescuer
            const hiddenCompleted = r.hidden_completed_from_rescuers || [];
            if (hiddenCompleted.includes(myId)) return false;

            return true;
        });
        
        const pendingReports = visibleReports.filter(r => r.status === 'pending');
        const inProgressReports = visibleReports.filter(r => r.status === 'in_progress' || r.status === 'waiting_for_user_approval');
        const completedReports = visibleReports.filter(r => r.status === 'completed');
        
        // Trash bin: Hidden pending reports OR reports soft-deleted by this rescuer 
        // (BUT NOT those permanently hidden/deleted)
        const trashedReports = allReports.filter(r => {
            const isTrashedFlag = r.is_deleted_by_rescuer === true;
            const hiddenBy = r.hidden_by_rescuers || [];
            const isHiddenByMe = hiddenBy.includes(myId);
            
            if (isTrashedFlag || isHiddenByMe) {
                // If it's trashed/hidden, check if it's permanently deleted
                const hiddenCompleted = r.hidden_completed_from_rescuers || [];
                if (hiddenCompleted.includes(myId)) {
                    return false; // Skip permanently deleted
                }
                return true;
            }
            return false;
        });
        
        displayReportList('pending', pendingReports);
        displayReportList('in-progress', inProgressReports);
        displayReportList('completed', completedReports);
        displayReportList('trash-bin', trashedReports);
        displayReportList('all-reports', visibleReports);
    }
    
    // Display report list in a specific tab
    function displayReportList(tabId, reports) {
        const tabElement = document.getElementById(tabId);
        
        if (reports.length === 0) {
            tabElement.innerHTML = `
                <div class="all-caught-up">
                    <h3>All caught up!</h3>
                    <p>${tabId === 'all-reports' ? 'No reports available' : `No ${tabId.replace('-', ' ')} reports`}</p>
                </div>
            `;
        } else {
            let html = '<div class="reports-list">';
            
            reports.forEach(report => {
                const reportDate = new Date(report.created_at).toLocaleString();
                const statusColor = getStatusColor(report.status);
                
                html += `
                    <div class="report-card" data-report-id="${report.id}" style="cursor: pointer;" onclick="if(typeof openReportDetailModal === 'function') openReportDetailModal(JSON.parse(this.dataset.report))" data-report='${JSON.stringify(report).replace(/'/g, "&#39;")}'>
                        <div class="report-header">
                            <div class="report-animal">
                                <span class="animal-type">${report.animal_type}</span>
                                <span class="animal-condition">${report.animal_condition}</span>
                            </div>
                            <div class="report-status">
                                <span class="status-badge" style="background-color: ${statusColor}">${report.status === 'waiting_for_user_approval' ? 'Requested' : (report.status === 'pending_completion' ? 'Awaiting Approval' : report.status)}</span>
                            </div>
                        </div>
                        <div class="report-body">
                            <p class="report-description">${report.description}</p>
                            <div class="report-location">
                                <strong>Location:</strong> ${report.address}
                                ${report.landmark ? `<br><strong>Landmark:</strong> ${report.landmark}` : ''}
                            </div>
                            <div class="report-meta">
                                <span class="report-date">${reportDate}</span>
                                <span class="report-reporter" style="margin-left: 15px; font-size: 13px; color: #666;">
                                    <i class="fas fa-user" style="margin-right: 5px;"></i>${report.reporter_name || 'Anonymous'}
                                </span>
                                ${tabId === 'pending' ? `
                                    <div class="report-actions" onclick="event.stopPropagation()">
                                        <button class="action-btn accept-btn" onclick="updateReportStatus('${report.id}', 'waiting_for_user_approval')">Request to Rescue</button>
                                        <button class="action-btn decline-btn" onclick="declineReport('${report.id}')">Decline</button>
                                    </div>
                                ` : ''}
                                ${tabId === 'completed' ? `
                                    <div class="report-actions" onclick="event.stopPropagation()">
                                        <button class="action-btn decline-btn" style="background-color: #6c757d;" onclick="trashReport('${report.id}')">Move to Trash</button>
                                    </div>
                                ` : ''}
                                ${tabId === 'in-progress' ? `
                                    <div class="report-actions" onclick="event.stopPropagation()">
                                        ${report.status === 'waiting_for_user_approval' ? '<span style="font-size: 13px; color: #FF8C00; font-weight: bold; margin-right: 15px;">Pending Approval...</span>' : (report.status === 'pending_completion' ? '<span style="font-size: 13px; color: #e67e22; font-weight: bold; margin-right: 15px;"><i class="fas fa-clock" style="margin-right: 5px;"></i>Awaiting Reporter Approval</span>' : `<button class="action-btn accept-btn" style="background-color: #28a745; margin-right: 10px;" onclick="openProofOfRescueModal('${report.id}')">Complete Rescue</button>`)}
                                        ${report.status !== 'in_progress' && report.status !== 'pending_completion' && report.status !== 'waiting_for_user_approval' ? `<button class="action-btn decline-btn" onclick="declineReport('${report.id}')">Cancel</button>` : ''}
                                    </div>
                                ` : ''}
                                ${tabId === 'trash-bin' ? `
                                    <div class="report-actions" onclick="event.stopPropagation()">
                                        <button class="action-btn recover-btn" onclick="recoverReport('${report.id}')">Recover</button>
                                        <button class="action-btn delete-btn" style="background-color: #dc3545;" onclick="permanentlyDeleteReport('${report.id}')">Delete Permanently</button>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            tabElement.innerHTML = html;
        }
    }
    
    // Get status color
    function getStatusColor(status) {
        switch(status) {
            case 'pending': return '#ffc107';
            case 'waiting_for_user_approval': return '#FF8C00';
            case 'in_progress': return '#17a2b8';
            case 'pending_completion': return '#e67e22';
            case 'completed': return '#28a745';
            case 'declined': return '#dc3545';
            case 'rescuer_declined': return '#6c757d';
            default: return '#6c757d';
        }
    }
    
    // Decline report (moves to trash bin for rescuer only)
    window.declineReport = async function(reportId) {
        showCustomConfirm(
            'Are you sure you want to decline this report? It will be moved to your trash bin and hidden from your view, but the user will still see it as pending.',
            'Decline Report',
            async function(confirmed) {
                if (!confirmed) return;
                try {
                    const response = await fetch(`/api/reports/${reportId}/trash/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showCustomAlert('Report declined and moved to trash bin.', 'Success');
                        await loadAllReports();
                    } else {
                        showCustomAlert('Error declining report: ' + (result.error || 'Unknown error'), 'Error');
                    }
                } catch (error) {
                    console.error('Error declining report:', error);
                    showCustomAlert('Error declining report. Please try again.', 'Error');
                }
            },
            true // isDanger
        );
    };
    

    
    // Update report status
    window.updateReportStatus = async function(reportId, newStatus) {
        try {
            const response = await fetch(`/api/reports/${reportId}/update/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showCustomAlert(`Report status updated to ${newStatus.replace('_', ' ')}!`, 'Success');
                await loadAllReports();
            } else {
                showCustomAlert('Error updating report: ' + (result.error || 'Unknown error'), 'Error');
            }
        } catch (error) {
            console.error('Error updating report:', error);
            showCustomAlert('Error updating report. Please try again.', 'Error');
        }
    };
    
    // Update report counts
    function updateReportCounts() {
        // Priority: currentProfile (from loadUserProfile) > window.currentRescuerId
        const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : { id: window.currentRescuerId };
        const myId = userCtx.id;
        
        const visibleReports = allReports.filter(r => {
            if (r.status === 'rescuer_declined') return false;
            if (r.is_deleted_by_rescuer === true) return false;
            const hiddenBy = r.hidden_by_rescuers || [];
            if (hiddenBy.includes(myId)) return false;
            
            const hiddenCompleted = r.hidden_completed_from_rescuers || [];
            if (hiddenCompleted.includes(myId)) return false;
            
            return true;
        });
        
        const pendingCount = visibleReports.filter(r => r.status === 'pending').length;
        const inProgressCount = visibleReports.filter(r => r.status === 'in_progress' || r.status === 'waiting_for_user_approval').length;
        const completedCount = visibleReports.filter(r => r.status === 'completed').length;
        const trashCountValue = allReports.filter(r => {
            const isDeclined = r.status === 'rescuer_declined';
            const isTrashed = r.is_deleted_by_rescuer === true;
            const hiddenBy = r.hidden_by_rescuers || [];
            const isHiddenByMe = hiddenBy.includes(myId);
            
            if (!isDeclined && !isTrashed && !isHiddenByMe) return false;
            
            // Check if it's permanently deleted
            const hiddenCompleted = r.hidden_completed_from_rescuers || [];
            return !hiddenCompleted.includes(myId);
        }).length;
        const allCount = visibleReports.length;
        
        updateTabCount('pending', pendingCount);
        updateTabCount('in-progress', inProgressCount);
        updateTabCount('completed', completedCount);
        updateTabCount('trash-bin', trashCountValue);
        updateTabCount('all-reports', allCount);
    }
    
    // Update individual tab count
    function updateTabCount(tabId, count) {
        const tabButton = document.querySelector(`[data-tab="${tabId}"] .count`);
        if (tabButton) {
            tabButton.textContent = `(${count})`;
        }
    }
    
    // Add report markers to map
    function addReportMarkersToMap() {
        if (!map) return;
        
        const currentRescuerId = window.currentRescuerId || '';
        
        // Don't show rescuer_declined, trashed, or hidden reports on map
        const visibleReports = allReports.filter(r => {
            if (r.status === 'rescuer_declined') return false;
            if (r.is_deleted_by_rescuer === true) return false;
            
            const hiddenBy = r.hidden_by_rescuers || [];
            if (hiddenBy.includes(currentRescuerId)) return false;
            
            const hiddenCompleted = r.hidden_completed_from_rescuers || [];
            if (hiddenCompleted.includes(currentRescuerId)) return false;
            
            return true;
        });
        
        visibleReports.forEach(report => {
            if (report.latitude && report.longitude) {
                const markerColor = report.type === 'dog' ? '#FF8C00' : '#4CAF50';
                const markerIcon = L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background: ${markerColor}; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">${report.animal_type[0].toUpperCase()}</div>`,
                    iconSize: [30, 30]
                });
                
                const reportMarker = L.marker([report.latitude, report.longitude], { icon: markerIcon });
                reportMarker.addTo(map);
                let safeReport = JSON.stringify(report).replace(/'/g, "&#39;").replace(/"/g, "&quot;");
                reportMarker.bindPopup(`
                    <b>${report.animal_type}</b><br>
                    ${report.description}<br>
                    <small>Status: ${report.status}</small><br>
                    <strong>Location:</strong> ${report.address}<br>
                    <button class="custom-modal-btn primary" onclick="if(typeof openReportDetailModal === 'function') openReportDetailModal(JSON.parse('${safeReport}'))" style="margin-top: 10px; padding: 5px 10px; font-size: 12px; border-radius: 5px; cursor: pointer;">View Details</button>
                `);
            }
        });
    }
    
    // Main navigation tab switching functionality
    mainTabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and panes
            mainTabBtns.forEach(b => b.classList.remove('active'));
            mainTabPanes.forEach(p => p.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
            
            // Initialize map when Map View tab is clicked
            if (targetTab === 'map-view' && !map) {
                console.log('Map View tab clicked, initializing map...');
                // Increased delay to ensure tab is fully visible and container is ready
                setTimeout(initializeMap, 500);
            } else if (targetTab === 'map-view' && map) {
                // Map already exists, just invalidate size to fix dragging
                setTimeout(() => {
                    map.invalidateSize();
                    console.log('Rescuer map size invalidated on tab switch');
                }, 100);
            }
        });
    });
    
    // Map functionality
    function initializeMap() {
        if (map) return; // Prevent re-initialization
        
        console.log('Initializing rescuer map...');
        
        // Check if Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            showCustomAlert('Map library not loaded. Please refresh the page.', 'Error');
            return;
        }
        
        // Check if map container exists
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.error('Map container not found');
            return;
        }
        
        console.log('Map container found:', mapContainer);
        
        try {
            // Use your exact working code
            map = L.map('map'); 
            // Initializes map
            
            // Start with a world view before geolocation resolves
            map.setView([0, 0], 2);
            
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }).addTo(map); 
            // Sets map data source and associates with map
            
            // Try to automatically center on the user's location
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    success(position);
                }, function(getErr) {
                    console.warn('Geolocation init warning:', getErr);
                }, {
                    enableHighAccuracy: false,
                    timeout: 12000,
                    maximumAge: 30000
                });
            }

            console.log('Rescuer map initialized successfully');
            
            // Force map to render properly first
            setTimeout(() => {
                map.invalidateSize();
                console.log('Rescuer map size invalidated');
                
                // Additional delay to ensure map container is properly sized
                setTimeout(() => {
                    // Load all reports from API
                    loadAllReports();
                    
                    // Start geolocation for rescuer's own position
                    navigator.geolocation.watchPosition(success, error, {
                        enableHighAccuracy: false,
                        timeout: 30000,
                        maximumAge: 60000
                    });
                }, 200);
            }, 300);
            
        } catch (error) {
            console.error('Error initializing map:', error);
            showCustomAlert('Error initializing map: ' + error.message, 'Error');
        }
    }
    
    function success(pos) {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const accuracy = pos.coords.accuracy;

        // Check if map is available
        if (!map) {
            console.error('Map not initialized yet, cannot add marker');
            return;
        }

        if (marker) {
            map.removeLayer(marker);
            map.removeLayer(circle);
        }

        marker = L.marker([lat, lng]).addTo(map);
        circle = L.circle([lat, lng], { 
            radius: accuracy,
            color: '#FF8C00',
            fillColor: '#FF8C00',
            fillOpacity: 0.1
        }).addTo(map);

        if (!zoomed) {
            zoomed = map.fitBounds(circle.getBounds()); 
        }

        map.setView([lat, lng], 15);

        const statusEl = document.getElementById('geolocationStatus');
        if (statusEl) {
            statusEl.textContent = `Current location ready (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
            statusEl.style.color = '#28a745';
        }
    }

    function error(err) {
        let msg;
        switch (err.code) {
            case 1:
                msg = 'Location access denied. Please allow location permission in your browser settings.';
                break;
            case 2:
                msg = 'Could not get location. Try:\n1. Check browser location permissions\n2. Use a mobile device with GPS\n3. Disable WiFi location blocking\n4. Try in a different browser';
                break;
            case 3:
                msg = 'Location request timed out. GPS signal may be weak.\nTry moving near a window or outside.';
                break;
            default:
                msg = 'Cannot get current location: ' + (err.message || 'Unknown error. Try a different browser or device with GPS.');
        }
        showCustomAlert(msg, 'Location Error');
    }
    
    // Get current location button
    if (getCurrentLocationBtn) {
        getCurrentLocationBtn.addEventListener('click', function() {
            if (!map) {
                initializeMap();
            }

            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    if (!map) {
                        initializeMap();
                    }
                    success(position);
                }, error, {
                    enableHighAccuracy: false,
                    timeout: 30000,
                    maximumAge: 60000
                });
            } else {
                showCustomAlert('Geolocation is not supported by your browser', 'Error');
            }
        });
    }

    // Refresh reports button
    if (refreshReportsBtn) {
        refreshReportsBtn.addEventListener('click', async function() {
            console.log('Refreshing reports...');
            
            // Reload reports from API
            await loadAllReports();
            
            // Show refresh confirmation
            const refreshMessage = document.createElement('div');
            refreshMessage.className = 'alert alert-success';
            refreshMessage.textContent = 'Reports refreshed!';
            refreshMessage.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #d4edda;
                color: #155724;
                padding: 15px 20px;
                border-radius: 8px;
                border: 1px solid #c3e6cb;
                z-index: 2000;
                animation: slideIn 0.3s ease;
            `;
            
            document.body.appendChild(refreshMessage);
            
            // Remove message after 2 seconds
            setTimeout(() => {
                if (refreshMessage.parentNode) {
                    refreshMessage.parentNode.removeChild(refreshMessage);
                }
            }, 2000);
        });
    }
    
    // Search functionality
    function performSearch() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const status = statusFilter ? statusFilter.value : 'All Status';
        const animalType = animalFilter ? animalFilter.value : 'All Animals';
        
        console.log('Search performed:', {
            term: searchTerm,
            status: status,
            animalType: animalType
        });
        
        // Filter reports based on search criteria
        const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : (window.currentRescuerContext || {});
        const myId = userCtx.id;
        
        // Start with visible reports (same filtering as displayReportsInTabs)
        let filteredReports = allReports.filter(r => {
            if (r.is_deleted_by_rescuer === true) return false;
            const hiddenBy = r.hidden_by_rescuers || [];
            if (hiddenBy.includes(myId)) return false;
            const hiddenCompleted = r.hidden_completed_from_rescuers || [];
            if (hiddenCompleted.includes(myId)) return false;
            return true;
        });
        
        // Apply search term filter
        if (searchTerm) {
            filteredReports = filteredReports.filter(r => {
                const searchableText = [
                    r.animal_type,
                    r.animal_condition,
                    r.description,
                    r.address,
                    r.landmark,
                    r.reporter_name,
                    r.status
                ].join(' ').toLowerCase();
                return searchableText.includes(searchTerm);
            });
        }
        
        // Apply status filter
        if (status && status !== 'All Status') {
            filteredReports = filteredReports.filter(r => {
                if (status === 'pending') return r.status === 'pending';
                if (status === 'waiting_for_user_approval') return r.status === 'waiting_for_user_approval';
                if (status === 'in_progress') return r.status === 'in_progress';
                if (status === 'completed') return r.status === 'completed';
                return true;
            });
        }
        
        // Apply animal type filter
        if (animalType && animalType !== 'All Animals') {
            if (animalType === 'Other') {
                // Show animals that are NOT Dog or Cat
                filteredReports = filteredReports.filter(r => {
                    const type = r.animal_type ? r.animal_type.toLowerCase() : '';
                    return type !== 'dog' && type !== 'cat';
                });
            } else {
                filteredReports = filteredReports.filter(r => {
                    return r.animal_type && r.animal_type.toLowerCase() === animalType.toLowerCase();
                });
            }
        }
        
        // Update the display with filtered reports
        updateDisplayWithFilteredReports(filteredReports);
    }
    
    // Update display with filtered reports
    function updateDisplayWithFilteredReports(filteredReports) {
        const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : (window.currentRescuerContext || {});
        const myId = userCtx.id;
        
        // Get currently active tab
        const activeTabBtn = document.querySelector('.nav-tabs .tab-btn.active');
        const activeTabId = activeTabBtn ? activeTabBtn.getAttribute('data-tab') : 'pending';
        
        // Filter by status for each tab
        const pendingReports = filteredReports.filter(r => r.status === 'pending');
        const inProgressReports = filteredReports.filter(r => r.status === 'in_progress' || r.status === 'waiting_for_user_approval');
        const completedReports = filteredReports.filter(r => r.status === 'completed');
        
        // Trash bin - include hidden/trashed reports that match search
        const trashedReports = allReports.filter(r => {
            const isTrashedFlag = r.is_deleted_by_rescuer === true;
            const hiddenBy = r.hidden_by_rescuers || [];
            const isHiddenByMe = hiddenBy.includes(myId);
            
            if (isTrashedFlag || isHiddenByMe) {
                const hiddenCompleted = r.hidden_completed_from_rescuers || [];
                if (hiddenCompleted.includes(myId)) return false;
                
                // Apply search filters to trash as well
                if (searchInput && searchInput.value.trim()) {
                    const searchTerm = searchInput.value.toLowerCase().trim();
                    const searchableText = [
                        r.animal_type,
                        r.animal_condition,
                        r.description,
                        r.address,
                        r.landmark,
                        r.reporter_name,
                        r.status
                    ].join(' ').toLowerCase();
                    return searchableText.includes(searchTerm);
                }
                return true;
            }
            return false;
        });
        
        // Update display for all tabs
        displayReportList('pending', pendingReports);
        displayReportList('in-progress', inProgressReports);
        displayReportList('completed', completedReports);
        displayReportList('trash-bin', trashedReports);
        displayReportList('all-reports', filteredReports);
        
        // Update counts
        updateTabCount('pending', pendingReports.length);
        updateTabCount('in-progress', inProgressReports.length);
        updateTabCount('completed', completedReports.length);
        updateTabCount('trash-bin', trashedReports.length);
        updateTabCount('all-reports', filteredReports.length);
    }
    
    // Add event listeners for search
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            // Show/hide clear button
            if (clearSearchBtn) {
                clearSearchBtn.style.display = searchInput.value ? 'block' : 'none';
            }
            performSearch();
        });
    }
    
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            searchInput.value = '';
            clearSearchBtn.style.display = 'none';
            performSearch();
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', performSearch);
    }
    
    if (animalFilter) {
        animalFilter.addEventListener('change', performSearch);
    }
    
    // Add keyboard navigation
    document.addEventListener('keydown', function(e) {
        // Ctrl+K or Cmd+K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) searchInput.focus();
        }
    });
    
    // Add search on Enter key
    if (searchInput) {
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    // Load reports on page load
    loadAllReports();
    
    // Proof of Rescue Implementation
    let proofMap, proofMarker;
    let proofLat, proofLng;
    let proofCurrentLocation = null; // Store for one-click pinning
    let uploadedProofPhotos = []; // Store multiple proof photos

    window.openProofOfRescueModal = function(reportId) {
        window.currentProofReportId = reportId;
        document.getElementById('proofAddress').value = '';
        document.getElementById('proofPhotoInput').value = '';
        uploadedProofPhotos = []; // Reset photos array
        displayProofPhotos(); // Clear photo grid display
        
        // Reset rating
        if (document.getElementById('rescuerToUserRating')) {
            document.getElementById('rescuerToUserRating').value = "0";
            document.getElementById('rescuerToUserFeedback').value = "";
            const stars = document.getElementById('rescuerRatingStars').children;
            for (let i = 0; i < stars.length; i++) {
                stars[i].style.color = '#ddd';
            }
        }
        
        proofLat = null;
        proofLng = null;
        
        const modal = document.getElementById('proofOfRescueModal');
        modal.style.display = 'flex';
        modal.classList.add('active');
        
        // Initialize map if not done
        setTimeout(() => {
            if (!proofMap) {
                // Use dashboard location if available, otherwise Manila
                const initialLat = window.currentLocation ? window.currentLocation.lat : 14.5995;
                const initialLng = window.currentLocation ? window.currentLocation.lng : 120.9842;
                
                proofMap = L.map('proofMapContainer').setView([initialLat, initialLng], 13);
                L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }).addTo(proofMap);
                
                // No click listener - user should only use the button
            }
            proofMap.invalidateSize();
            
            // Proactive fetching (same as user dashboard initializeModalMap)
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    proofCurrentLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    console.log('Proactive proof location found:', proofCurrentLocation);
                }, function(err) {
                    console.warn('Proactive proof location warning:', err);
                }, {
                    enableHighAccuracy: false,
                    timeout: 20000,
                    maximumAge: 60000
                });
            }
        }, 250); // Increased delay for smoother modal animation
    };

    window.closeProofOfRescueModal = function() {
        const modal = document.getElementById('proofOfRescueModal');
        modal.classList.remove('active');
        modal.style.display = 'none';
    };

    window.setRescuerRating = function(rating) {
        document.getElementById('rescuerToUserRating').value = rating;
        const stars = document.getElementById('rescuerRatingStars').children;
        for (let i = 0; i < stars.length; i++) {
            if (i < rating) {
                stars[i].style.color = '#FF8C00';
            } else {
                stars[i].style.color = '#ddd';
            }
        }
    };

    window.previewProofPhoto = function(input) {
        if (input.files && input.files.length > 0) {
            const files = Array.from(input.files);
            
            files.forEach(file => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const photoData = {
                            id: Date.now() + Math.random(),
                            url: e.target.result,
                            name: file.name,
                            file: file
                        };
                        uploadedProofPhotos.push(photoData);
                        displayProofPhotos();
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            // Clear the input so same files can be selected again if removed
            input.value = '';
        }
    };
    
    function displayProofPhotos() {
        const photoGrid = document.getElementById('proofPhotoGrid');
        const photoGridContainer = document.getElementById('proofPhotoGridContainer');
        const previewText = document.getElementById('proofPhotoPreviewText');
        
        if (uploadedProofPhotos.length > 0) {
            photoGrid.style.display = 'block';
            previewText.textContent = `${uploadedProofPhotos.length} photo${uploadedProofPhotos.length > 1 ? 's' : ''} selected (click area to add more)`;
            photoGridContainer.innerHTML = '';
            
            uploadedProofPhotos.forEach(photo => {
                const photoItem = document.createElement('div');
                photoItem.style.cssText = 'position: relative; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';
                photoItem.innerHTML = `
                    <img src="${photo.url}" alt="${photo.name}" style="width: 100%; height: 100px; object-fit: cover;">
                    <button type="button" onclick="removeProofPhoto(${photo.id})" style="position: absolute; top: 5px; right: 5px; background: #dc3545; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">&times;</button>
                `;
                photoGridContainer.appendChild(photoItem);
            });
        } else {
            photoGrid.style.display = 'none';
            previewText.textContent = 'Click to browse and upload proof photos (multiple allowed)';
        }
    }
    
    window.removeProofPhoto = function(photoId) {
        uploadedProofPhotos = uploadedProofPhotos.filter(p => p.id !== photoId);
        displayProofPhotos();
    };

    let geocodeTimer = null;
    
    window.setProofLocation = function(lat, lng, moveMap = true) {
        if (!proofMap) return;

        proofLat = lat;
        proofLng = lng;
        
        if (proofMarker) {
            proofMarker.setLatLng([lat, lng]);
        } else {
            proofMarker = L.marker([lat, lng]).addTo(proofMap);
        }

        if (moveMap) {
            proofMap.setView([lat, lng], 15);
        }
        
        // Debounce: only geocode after 500ms of no new pins
        if (geocodeTimer) clearTimeout(geocodeTimer);
        
        const statusEl = document.getElementById('proofGeocodeStatus');
        if (statusEl) {
            statusEl.textContent = "Fetching precise address...";
            statusEl.style.color = "#FF8C00";
        }

        geocodeTimer = setTimeout(() => {
            fetch(`/api/reverse-geocode/?lat=${lat}&lon=${lng}`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('proofAddress').value = data.display_name; // Changed from 'rescued_address' to 'proofAddress' to match existing HTML
                        if (statusEl) {
                            statusEl.textContent = "Address found!";
                            statusEl.style.color = "#28a745";
                            setTimeout(() => { statusEl.textContent = ""; }, 2000);
                        }
                    } else {
                        if (statusEl) {
                            statusEl.textContent = "Could not get address automatically.";
                            statusEl.style.color = "#dc3545";
                        }
                    }
                })
                .catch(err => {
                    console.error('Geocoding error:', err);
                    if (statusEl) {
                        statusEl.textContent = "Connection error. Please enter address manually.";
                        statusEl.style.color = "#dc3545";
                    }
                });
        }, 500);
    };
    
    window.getProofCurrentLocation = function() {
        const statusEl = document.getElementById('proofGeocodeStatus');
        
        // 1. Check if we already found the location proactively
        if (proofCurrentLocation) {
            console.log('Using proactive location for proof');
            setProofLocation(proofCurrentLocation.lat, proofCurrentLocation.lng, true);
            return;
        }

        if (statusEl) {
            statusEl.textContent = "Accessing GPS...";
            statusEl.style.color = "#FF8C00";
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                proofCurrentLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                setProofLocation(proofCurrentLocation.lat, proofCurrentLocation.lng, true);
            }, function(err) {
                console.warn('Geolocation error:', err);
                let errorMsg = 'Unable to retrieve location. GPS signals may be weak.';
                if (err.code === 1) errorMsg = 'Location permission denied. Please allow GPS access.';
                
                if (statusEl) {
                    statusEl.textContent = errorMsg;
                    statusEl.style.color = "#dc3545";
                }
                showCustomAlert(errorMsg, 'Error');
            }, {
                enableHighAccuracy: false,
                timeout: 30000,
                maximumAge: 60000
            });
        } else {
            showCustomAlert('Geolocation is not supported by your browser.', 'Error');
        }
    };

    // pinProofLocation is now redundant but kept for safety if button naming changes
    window.pinProofLocation = window.getProofCurrentLocation;

    window.submitRescueProof = async function() {
        const reportId = window.currentProofReportId;
        const address = document.getElementById('proofAddress').value.trim();
        
        const rescuerToUserRating = parseInt(document.getElementById('rescuerToUserRating').value) || 0;
        const rescuerToUserFeedback = document.getElementById('rescuerToUserFeedback').value.trim();
        
        // --- Validations ---
        if (!address) {
            showCustomAlert('Please provide the placement address.', 'Validation Error');
            return;
        }
        if (uploadedProofPhotos.length === 0) {
            showCustomAlert('Please upload at least one proof of rescue photo.', 'Validation Error');
            return;
        }
        // Rating is REQUIRED
        const ratingErrorEl = document.getElementById('rescuerRatingError');
        if (rescuerToUserRating < 1 || rescuerToUserRating > 5) {
            if (ratingErrorEl) ratingErrorEl.style.display = 'block';
            document.getElementById('rescuerRatingStars').scrollIntoView({ behavior: 'smooth', block: 'center' });
            showCustomAlert('Please rate the reporter before submitting.', 'Rating Required');
            return;
        }
        if (ratingErrorEl) ratingErrorEl.style.display = 'none';
        // --- End Validations ---

        const submitBtn = document.getElementById('submitProofBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading Proof...';
        
        try {
            // Upload all images
            const imageUrls = [];
            console.log(`Uploading ${uploadedProofPhotos.length} proof images...`);
            
            for (const photo of uploadedProofPhotos) {
                console.log('Uploading photo:', photo.name);
                try {
                    const uploadResponse = await fetch('/api/upload-image/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            image_data: photo.url,
                            file_name: photo.name
                        })
                    });
                    
                    const uploadResult = await uploadResponse.json();
                    
                    if (uploadResult.success) {
                        imageUrls.push(uploadResult.url);
                        console.log('Image uploaded successfully:', uploadResult.url);
                    } else {
                        console.error('Upload failed:', uploadResult.error);
                        showCustomAlert('Failed to upload image: ' + (uploadResult.error || 'Unknown error'), 'Upload Error');
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Upload Proof & Complete';
                        return;
                    }
                } catch (uploadError) {
                    console.error('Error uploading image:', uploadError);
                    showCustomAlert('Error uploading image. Please try again.', 'Upload Error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Upload Proof & Complete';
                    return;
                }
            }
            
            const updatePayload = {
                status: 'pending_completion',
                proof_image_url: imageUrls[0], // First image for backward compatibility
                proof_image_urls: imageUrls, // All images as array
                rescued_address: address,
                rescued_latitude: proofLat,
                rescued_longitude: proofLng
            };
            
            if (rescuerToUserRating > 0) {
                updatePayload.rescuer_to_user_rating = rescuerToUserRating;
                updatePayload.rescuer_to_user_feedback = rescuerToUserFeedback;
            }
            
            const updateResponse = await fetch(`/api/reports/${reportId}/update/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(updatePayload)
            });
            
            const updateResult = await updateResponse.json();
            
            if (updateResult.success) {
                showCustomAlert('Proof submitted! Waiting for the reporter to verify and approve completion.', 'Success');
                closeProofOfRescueModal();
                await loadAllReports();
            } else {
                throw new Error(updateResult.error || 'Failed to update report database');
            }
        } catch (error) {
            console.error('Error submitting proof:', error);
            showCustomAlert(error.message || 'An error occurred while submitting proof.', 'Error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Upload Proof & Complete';
        }
    };

    // Trash Bin logic
    window.trashReport = async function(reportId) {
        showCustomConfirm('Move this record to trash?', 'Move to Trash', async (confirmed) => {
            if (!confirmed) return;
            try {
                const response = await fetch(`/api/reports/${reportId}/trash/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
                });
                const result = await response.json();
                if (result.success) {
                    showCustomAlert('Report moved to trash.', 'Success');
                    loadAllReports(); // Reload everything
                } else {
                    showCustomAlert('Error: ' + result.error, 'Error');
                }
            } catch (e) {
                console.error('Error trashing:', e);
                showCustomAlert('An error occurred while trashing the report.', 'Error');
            }
        });
    };

    window.recoverReport = async function(reportId) {
        try {
            const response = await fetch(`/api/reports/${reportId}/recover/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            });
            const result = await response.json();
            if (result.success) {
                showCustomAlert('Report recovered successfully.', 'Success');
                loadAllReports();
            } else {
                showCustomAlert('Error: ' + result.error, 'Error');
            }
        } catch (e) {
            console.error('Error recovering:', e);
            showCustomAlert('An error occurred while recovering the report.', 'Error');
        }
    };

    window.permanentlyDeleteReport = async function(reportId) {
        showCustomConfirm('WARNING: This will permanently delete this report. This action cannot be undone!', 'Delete Permanently', async (confirmed) => {
            if (!confirmed) return;
            try {
                const response = await fetch(`/api/reports/${reportId}/delete/`, {
                    method: 'DELETE',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') 
                    }
                });
                const result = await response.json();
                if (result.success) {
                    showCustomAlert('Report permanently deleted.', 'Success');
                    loadAllReports();
                } else {
                    showCustomAlert('Error: ' + result.error, 'Error');
                }
            } catch (e) {
                console.error('Error deleting:', e);
                showCustomAlert('An error occurred during permanent deletion.', 'Error');
            }
        });
    };

});
