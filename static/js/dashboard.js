document.addEventListener('DOMContentLoaded', function() {
    // Modal elements
    const modalOverlay = document.getElementById('modalOverlay');
    const openModalBtn = document.getElementById('openModalBtn');
    const openModalBtn2 = document.getElementById('openModalBtn2');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    
    // Main navigation tabs
    const mainTabBtns = document.querySelectorAll('.nav-tabs .tab-btn');
    const mainTabPanes = document.querySelectorAll('.tab-content .tab-pane');
    
    // Modal tabs
    const modalTabBtns = document.querySelectorAll('.modal-tabs .tab-btn');
    const modalTabPanes = document.querySelectorAll('.modal .tab-pane');
    
    // Photo upload elements
    const uploadArea = document.getElementById('uploadArea');
    const photoInput = document.getElementById('photoInput');
    const browseBtn = document.getElementById('browseBtn');
    const uploadedPhotos = document.getElementById('uploadedPhotos');
    const photoGrid = document.getElementById('photoGrid');
    
    // Map elements
    const getCurrentLocationBtn = document.getElementById('getCurrentLocation');
    const refreshReportsBtn = document.getElementById('refreshReports');
    
    // Modal map elements
    const modalGetLocationBtn = document.getElementById('modalGetLocationBtn');
    const modalPinLocationBtn = document.getElementById('modalPinLocationBtn');
    const modalMapContainer = document.getElementById('modalMapContainer');
    
let map, marker, circle, zoomed;
    let modalMap, modalMarker, modalCircle, modalZoomed;
    let pinnedLocations = []; // Store pinned locations
    let lastPinnedLocation = null; // Track last pin for form auto-fill
    let currentLocation = null; // Latest geolocation
    let modalCurrentLocation = null; // Location for modal map
    
    // Store uploaded photos
    let uploadedPhotosList = [];
    
    // Store all reports for client-side filtering
    let allReports = [];
    
    // Modal functionality
    function openModal() {
        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Ensure Details tab is active when modal opens
        modalTabBtns.forEach(b => b.classList.remove('active'));
        modalTabPanes.forEach(p => p.classList.remove('active'));
        const detailsTabBtn = document.querySelector('[data-tab="details"]');
        if (detailsTabBtn) {
            detailsTabBtn.classList.add('active');
        }
        const detailsTabPane = document.getElementById('details-tab');
        if (detailsTabPane) {
            detailsTabPane.classList.add('active');
        }
    }
    
    function closeModal() {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
    
    openModalBtn.addEventListener('click', openModal);
    if (openModalBtn2) {
        openModalBtn2.addEventListener('click', openModal);
    }
    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    // Close modal when clicking outside
    modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
    
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
                    console.log('Map size invalidated on tab switch');
                }, 100);
            } else if (targetTab === 'trash-bin') {
                // Now using client-side filtering, no need for separate API call
                displayReports(allReports);
            } else if (targetTab === 'in-progress' || targetTab === 'completed') {
                // These tabs are handled by displayReports with client-side filtering
                displayReports(allReports);
            }
        });
    });
    
    // Modal tab switching functionality
    modalTabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Auto-fill address from last pinned location if available
            if (targetTab === 'location' && lastPinnedLocation) {
                const addressEl = document.getElementById('address');
                if (addressEl) {
                    addressEl.value = lastPinnedLocation.address;
                    console.log('Auto-filled report address:', lastPinnedLocation.address);
                }
            }
            
            // Initialize modal map when location tab is clicked
            if (targetTab === 'location') {
                setTimeout(initializeModalMap, 100);
            }
            
            // Remove active class from all tabs and panes
            modalTabBtns.forEach(b => b.classList.remove('active'));
            modalTabPanes.forEach(p => p.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            document.getElementById(targetTab + '-tab').classList.add('active');
        });
    });
    
    // Photo upload functionality
    browseBtn.addEventListener('click', function(e) {
        e.stopPropagation(); // Stop event from bubbling to uploadArea
        photoInput.click();
    });
    
    uploadArea.addEventListener('click', function(e) {
        // Only click photoInput if the target is not the browseBtn to avoid double clicks
        if (e.target !== browseBtn) {
            photoInput.click();
        }
    });
    
    photoInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        
        files.forEach(file => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    const photoData = {
                        id: Date.now() + Math.random(),
                        url: e.target.result,
                        name: file.name
                    };
                    
                    uploadedPhotosList.push(photoData);
                    displayUploadedPhotos();
                };
                
                reader.readAsDataURL(file);
            }
        });
        
        // Clear the input
        e.target.value = '';
    });
    
    // Drag and drop functionality
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = '#e67e00';
        this.style.background = '#fff5eb';
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.style.borderColor = '#FF8C00';
        this.style.background = '#fff9f5';
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = '#FF8C00';
        this.style.background = '#fff9f5';
        
        const files = Array.from(e.dataTransfer.files);
        
        files.forEach(file => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    const photoData = {
                        id: Date.now() + Math.random(),
                        url: e.target.result,
                        name: file.name
                    };
                    
                    uploadedPhotosList.push(photoData);
                    displayUploadedPhotos();
                };
                
                reader.readAsDataURL(file);
            }
        });
    });
    
    function displayUploadedPhotos() {
        if (uploadedPhotosList.length > 0) {
            uploadedPhotos.style.display = 'block';
            photoGrid.innerHTML = '';
            
            uploadedPhotosList.forEach(photo => {
                const photoItem = document.createElement('div');
                photoItem.className = 'photo-item';
                photoItem.innerHTML = `
                    <img src="${photo.url}" alt="${photo.name}">
                    <button class="remove-photo" data-id="${photo.id}">&times;</button>
                `;
                photoGrid.appendChild(photoItem);
            });
            
            // Add remove functionality
            document.querySelectorAll('.remove-photo').forEach(btn => {
                btn.addEventListener('click', function() {
                    const photoId = parseFloat(this.getAttribute('data-id'));
                    uploadedPhotosList = uploadedPhotosList.filter(p => p.id !== photoId);
                    displayUploadedPhotos();
                    
                    if (uploadedPhotosList.length === 0) {
                        uploadedPhotos.style.display = 'none';
                    }
                });
            });
        } else {
            uploadedPhotos.style.display = 'none';
        }
    }
    
    // Map functionality - copied exactly from working rescuer dashboard
    function initializeMap() {
        const mapContainer = document.getElementById('map');
        
        // Check if map already initialized (either by variable or container property)
        if (map || (mapContainer && mapContainer._leaflet_id)) {
            console.log('Map already initialized, skipping');
            if (map && mapContainer && mapContainer._leaflet_id) {
                // Just invalidate size
                setTimeout(() => {
                    map.invalidateSize();
                }, 100);
            }
            return;
        }
        
        console.log('Initializing map...');
        
        // Check if Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            showCustomAlert('Map library not loaded. Please refresh the page.', 'Error');
            return;
        }
        
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

            console.log('Map initialized successfully');
            
            // Force map to render properly first
            setTimeout(() => {
                map.invalidateSize();
                console.log('Map size invalidated');
                
                // Additional delay to ensure map container is properly sized
                setTimeout(() => {
                    // Load reports on map
                    loadReports();
                    
                    // Start geolocation after map is fully ready
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
        currentLocation = { lat, lng, accuracy };

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
                showCustomAlert("Geolocation is not supported by your browser", "Error");
            }
        });
    }
    
    // Refresh reports button
    if (refreshReportsBtn) {
        refreshReportsBtn.addEventListener('click', async function() {
            await loadReports();
            // Show reports on map as markers
            displayReportsOnMap();
            const statusEl = document.getElementById('geolocationStatus');
            if (statusEl) {
                statusEl.textContent = 'Reports refreshed';
                statusEl.style.color = '#28a745';
                setTimeout(() => {
                    statusEl.textContent = '';
                }, 2000);
            }
        });
    }
    
    // Reverse geocoding for locations
    async function reverseGeocode(lat, lng) {
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`
            );
            const data = await response.json();
            return data.display_name || `Lat ${lat.toFixed(4)}, Lng ${lng.toFixed(4)}`;
        } catch (error) {
            console.error("Reverse geocoding error:", error);
            return `Lat ${lat.toFixed(4)}, Lng ${lng.toFixed(4)}`;
        }
    }
    
    // Display reports on map
    let reportMarkers = [];
    
    function displayReportsOnMap() {
        if (!map) return;
        
        // Clear existing report markers
        reportMarkers.forEach(marker => map.removeLayer(marker));
        reportMarkers = [];
        
        // Fetch reports from API
        fetch('/api/reports/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(result => {
            if (result.success && result.reports) {
                // Get user context for filtering
                const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : window.currentUserContext;
                const myId = userCtx?.id;

                result.reports.forEach(report => {
                    // FILTER: Don't show reports on map if:
                    // 1. It is trashed (is_deleted_by_user)
                    // 2. It is permanently hidden (user is in hidden_completed_from_users)
                    if (report.is_deleted_by_user === true) return;
                    
                    const hiddenUsers = report.hidden_completed_from_users || [];
                    if (myId && hiddenUsers.includes(myId)) return;

                    if (report.latitude && report.longitude) {
                        const reportMarker = L.marker([report.latitude, report.longitude], {
                            icon: L.divIcon({
                                className: 'report-marker',
                                html: `<div style="background: #dc3545; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">!</div>`,
                                iconSize: [24, 24]
                            })
                        }).addTo(map);
                        
                        let safeReport = JSON.stringify(report).replace(/'/g, "&#39;").replace(/"/g, "&quot;");
                        reportMarker.bindPopup(`
                            <b>Animal Report</b><br>
                            Type: ${report.animal_type}<br>
                            Condition: ${report.animal_condition}<br>
                            Location: ${report.address}<br>
                            Status: ${report.status}<br>
                            <button class="custom-modal-btn primary" onclick="if(typeof openReportDetailModal === 'function') openReportDetailModal(JSON.parse('${safeReport}'))" style="margin-top: 10px; padding: 5px 10px; font-size: 12px; border-radius: 5px; cursor: pointer;">View Details</button>
                        `);
                        
                        reportMarkers.push(reportMarker);
                    }
                });
                
                console.log(`Displayed ${reportMarkers.length} reports on map`);
            }
        })
        .catch(error => console.error('Error loading reports for map:', error));
    }
    
    // Modal Map functionality
    function initializeModalMap() {
        if (modalMap) {
            // Map already initialized, just invalidate size
            setTimeout(() => {
                modalMap.invalidateSize();
            }, 100);
            return;
        }
        
        console.log('Initializing modal map...');
        
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            return;
        }
        
        if (!modalMapContainer) {
            console.error('Modal map container not found');
            return;
        }
        
        try {
            modalMap = L.map('modalMapContainer');
            
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }).addTo(modalMap);
            
            // Start with world view
            modalMap.setView([0, 0], 2);
            
            // Try to get current location
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    modalSuccess(position);
                }, function(err) {
                    console.warn('Modal geolocation init warning:', err);
                }, {
                    enableHighAccuracy: false,
                    timeout: 12000,
                    maximumAge: 30000
                });
            }
            
            console.log('Modal map initialized successfully');
            
            // Force map to render properly
            setTimeout(() => {
                modalMap.invalidateSize();
            }, 300);
            
        } catch (error) {
            console.error('Error initializing modal map:', error);
        }
    }
    
    function modalSuccess(pos) {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const accuracy = pos.coords.accuracy;
        modalCurrentLocation = { lat, lng, accuracy };
        
        if (!modalMap) return;
        
        if (modalMarker) {
            modalMap.removeLayer(modalMarker);
            modalMap.removeLayer(modalCircle);
        }
        
        modalMarker = L.marker([lat, lng]).addTo(modalMap);
        modalCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#FF8C00',
            fillColor: '#FF8C00',
            fillOpacity: 0.1
        }).addTo(modalMap);
        
        if (!modalZoomed) {
            modalZoomed = modalMap.fitBounds(modalCircle.getBounds());
        }
        
        modalMap.setView([lat, lng], 15);
        
        const statusEl = document.getElementById('modalGeolocationStatus');
        if (statusEl) {
            statusEl.textContent = `Current location ready (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
            statusEl.style.color = '#28a745';
        }
    }
    
    function modalError(err) {
        let msg;
        switch (err.code) {
            case 1:
                msg = 'Location access denied. Please allow location permission in your browser settings.';
                break;
            case 2:
                msg = 'Could not get location. Try:\n1. Check browser location permissions\n2. Use a mobile device with GPS\n3. Try in a different browser';
                break;
            case 3:
                msg = 'Location request timed out. GPS signal may be weak.';
                break;
            default:
                msg = 'Cannot get current location: ' + (err.message || 'Unknown error.');
        }
        showCustomAlert(msg, "Location Error");
    }
    
    // Modal Get Location button
    if (modalGetLocationBtn) {
        modalGetLocationBtn.addEventListener('click', function() {
            if (!modalMap) {
                initializeModalMap();
            }
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    if (!modalMap) {
                        initializeModalMap();
                    }
                    modalSuccess(position);
                }, modalError, {
                    enableHighAccuracy: false,
                    timeout: 30000,
                    maximumAge: 60000
                });
            } else {
                showCustomAlert('Geolocation is not supported by your browser', 'Error');
            }
        });
    }
    
    // Modal Pin Location button
    if (modalPinLocationBtn) {
        modalPinLocationBtn.addEventListener('click', async function() {
            let latLng = null;
            if (modalCurrentLocation) {
                latLng = { lat: modalCurrentLocation.lat, lng: modalCurrentLocation.lng };
            }
            
            if (!latLng && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(async function(position) {
                    latLng = { lat: position.coords.latitude, lng: position.coords.longitude };
                    await pinModalLocation(latLng.lat, latLng.lng);
                }, modalError, {
                    enableHighAccuracy: false,
                    timeout: 30000,
                    maximumAge: 60000
                });
            } else if (latLng) {
                await pinModalLocation(latLng.lat, latLng.lng);
            } else {
                showCustomAlert('Unable to get current location for pinning. Please ensure location services are enabled.', 'Error');
            }
        });
    }
    
    async function pinModalLocation(lat, lng) {
        const address = await reverseGeocode(lat, lng);
        console.log('Modal pinned address:', address);
        
        // Create marker on modal map
        const pinMarker = L.marker([lat, lng], {
            icon: L.divIcon({
                className: 'pinned-location-marker',
                html: `<div style="background: #007bff; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 10px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">P</div>`,
                iconSize: [20, 20]
            })
        }).addTo(modalMap);
        
        const timestamp = new Date().toLocaleString();
        pinMarker.bindPopup(`<b>Pinned Location</b><br>Address: ${address}<br>Time: ${timestamp}`);
        
        // Update the address field
        const addressEl = document.getElementById('address');
        if (addressEl) {
            addressEl.value = address;
        }
        
        // Also update lastPinnedLocation for the main map
        lastPinnedLocation = { lat, lng, address };
        
        // Show success message
        const statusEl = document.getElementById('modalGeolocationStatus');
        if (statusEl) {
            statusEl.textContent = `Location pinned! Address auto-filled: ${address.substring(0, 50)}${address.length > 50 ? '...' : ''}`;
            statusEl.style.color = '#28a745';
        }
        
        // Save to database
        try {
            const response = await fetch('/api/pinned-locations/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lng,
                    description: address
                })
            });
            
            const result = await response.json();
            if (result.success) {
                console.log('Pinned location saved to database:', result.location);
                lastPinnedLocation.id = result.location.id; // Store ID for potential deletion
            } else {
                console.error('Failed to save pinned location:', result.error);
            }
        } catch (error) {
            console.error('Error saving pinned location:', error);
        }
        
        console.log('Modal location pinned:', { lat, lng, address });
    }
    
    // Delete pinned location function
    async function deletePinnedLocation(locationId) {
        if (!locationId) {
            console.error('No location ID provided for deletion');
            return;
        }
        
        try {
            const response = await fetch(`/api/pinned-locations/delete/${locationId}/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const result = await response.json();
            if (result.success) {
                console.log('Pinned location deleted:', result.message);
                return true;
            } else {
                console.error('Failed to delete pinned location:', result.error);
                return false;
            }
        } catch (error) {
            console.error('Error deleting pinned location:', error);
            return false;
        }
    }
    
    // Submit form functionality - AGGRESSIVE duplicate prevention
    let isSubmitting = false;
    let lastSubmitTime = 0;
    const SUBMIT_COOLDOWN = 5000; // 5 seconds minimum between submissions
    
    const submitBtn = document.getElementById('submitBtn');
    
    // Remove any existing listeners by cloning and replacing the button
    const newSubmitBtn = submitBtn.cloneNode(true);
    submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);
    
    newSubmitBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const now = Date.now();
        
        // Check if already submitting
        if (isSubmitting) {
            console.log('BLOCKED: Already submitting');
            showCustomAlert('Please wait, submission in progress...', 'Wait');
            return;
        }
        
        // Check cooldown period
        if (now - lastSubmitTime < SUBMIT_COOLDOWN) {
            console.log(`BLOCKED: Cooldown period. ${Math.ceil((SUBMIT_COOLDOWN - (now - lastSubmitTime))/1000)}s remaining`);
            showCustomAlert('Please wait a few seconds before submitting another report', 'Wait');
            return;
        }
        
        // Set flags
        isSubmitting = true;
        lastSubmitTime = now;
        newSubmitBtn.disabled = true;
        newSubmitBtn.textContent = 'Submitting...';
        newSubmitBtn.style.opacity = '0.7';
        
        console.log('Starting report submission...');
        
        try {
            // Collect form data from all tabs
            const formData = {
                animal_type: document.getElementById('animal-type').value,
                animal_condition: document.getElementById('animal-condition').value,
                description: document.getElementById('description').value,
                latitude: lastPinnedLocation?.lat || null,
                longitude: lastPinnedLocation?.lng || null,
                address: document.getElementById('address').value,
                landmark: document.getElementById('landmark').value,
                additional_info: document.getElementById('additional-info').value
            };
            
            // Validation
            if (!formData.animal_type || !formData.animal_condition || !formData.description) {
                showCustomAlert('Please fill in all required fields in Details tab.', 'Missing Fields');
                isSubmitting = false;
                newSubmitBtn.disabled = false;
                newSubmitBtn.textContent = 'Submit Report';
                newSubmitBtn.style.opacity = '1';
                return;
            }
            
            if (!formData.address) {
                showCustomAlert('Please provide location address.', 'Missing Location');
                isSubmitting = false;
                newSubmitBtn.disabled = false;
                newSubmitBtn.textContent = 'Submit Report';
                newSubmitBtn.style.opacity = '1';
                return;
            }

            // Enforce image requirement
            if (uploadedPhotosList.length === 0) {
                showCustomAlert('Please provide at least one photo of the animal condition.', 'Photo Required');
                isSubmitting = false;
                newSubmitBtn.disabled = false;
                newSubmitBtn.textContent = 'Submit Report';
                newSubmitBtn.style.opacity = '1';
                return;
            }
            
            // Upload images
            const imageUrls = [];
            
            if (uploadedPhotosList.length > 0) {
                console.log(`Uploading ${uploadedPhotosList.length} images...`);
                console.log('Photos to upload:', uploadedPhotosList);
                
                for (const photo of uploadedPhotosList) {
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
                        console.log('Upload result:', uploadResult);
                        
                        if (uploadResult.success) {
                            imageUrls.push(uploadResult.url);
                            console.log('Image uploaded successfully:', uploadResult.url);
                        } else {
                            console.error('Upload failed:', uploadResult.error);
                            showCustomAlert('Failed to upload image: ' + (uploadResult.error || 'Unknown error'), 'Upload Error');
                            isSubmitting = false;
                            newSubmitBtn.disabled = false;
                            newSubmitBtn.textContent = 'Submit Report';
                            newSubmitBtn.style.opacity = '1';
                            return; // HALT submission if image upload fails
                        }
                    } catch (uploadError) {
                        console.error('Error uploading image:', uploadError);
                        showCustomAlert('Error uploading image. Please try again.', 'Upload Error');
                        isSubmitting = false;
                        newSubmitBtn.disabled = false;
                        newSubmitBtn.textContent = 'Submit Report';
                        newSubmitBtn.style.opacity = '1';
                        return; // HALT submission on network error
                    }
                }
            }
            
            formData.photos = imageUrls;
            
            console.log('Submitting report with photos:', imageUrls.length, 'photos');
            console.log('Report data:', formData);
            
            // Submit to backend
            const response = await fetch('/api/reports/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('Report submitted successfully:', result.report);
                
                // Show success
                const successMessage = document.createElement('div');
                successMessage.className = 'alert alert-success';
                successMessage.textContent = 'Animal report submitted successfully!';
                successMessage.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #d4edda;
                    color: #155724;
                    padding: 15px 20px;
                    border-radius: 8px;
                    z-index: 2000;
                `;
                document.body.appendChild(successMessage);
                
                // Refresh and cleanup
                await loadReports();
                closeModal();
                resetForm();
                
                setTimeout(() => {
                    if (successMessage.parentNode) {
                        successMessage.parentNode.removeChild(successMessage);
                    }
                }, 3000);
            } else {
                showCustomAlert('Error submitting report: ' + (result.error || 'Unknown error'), 'Submission Error');
            }
        } catch (error) {
            console.error('Error submitting report:', error);
            showCustomAlert('Error submitting report. Please try again.', 'Error');
        } finally {
            console.log('Submission complete, resetting flags');
            isSubmitting = false;
            newSubmitBtn.disabled = false;
            newSubmitBtn.textContent = 'Submit Report';
            newSubmitBtn.style.opacity = '1';
        }
    });
    
    function resetForm() {
        // Reset details form
        document.getElementById('animal-type').value = '';
        document.getElementById('animal-condition').value = '';
        document.getElementById('description').value = '';
        
        // Reset location form
        document.getElementById('address').value = '';
        document.getElementById('landmark').value = '';
        document.getElementById('additional-info').value = '';
        lastPinnedLocation = null;
        
        // Reset photos
        uploadedPhotosList = [];
        displayUploadedPhotos();
        
        // Reset to first tab
        modalTabBtns.forEach(btn => btn.classList.remove('active'));
        modalTabPanes.forEach(pane => pane.classList.remove('active'));
        document.querySelector('[data-tab="details"]').classList.add('active');
        document.getElementById('details-tab').classList.add('active');
    }
    
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
    
    // Load reports from API
    async function loadReports() {
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
                displayReports(allReports);
                
                // Also update map markers if map exists
                if (map) {
                    displayReportsOnMap();
                }
            } else {
                console.error('Error loading reports:', result.error);
            }
        } catch (error) {
            console.error('Error loading reports:', error);
        }
    }
    
    // Display reports in the appropriate tabs
    function displayReports(reports) {
        console.log("DEBUG: displayReports called with", reports.length, "reports");
        console.log("DEBUG: Raw reports data:", reports);
        const myReportsTab = document.getElementById('my-reports');
        const allReportsTab = document.getElementById('all-reports');
        const inProgressTab = document.getElementById('in-progress');
        const completedTab = document.getElementById('completed');
        const trashList = document.getElementById('trashReportsList');
        const emptyTrashMsg = document.getElementById('emptyTrashMsg');
        
        // Filter My Reports (active ones I reported)
        // Priority: currentProfile (from loadUserProfile) > window.currentUserContext
        const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : window.currentUserContext;
        console.log("DEBUG: currentUserContext:", window.currentUserContext);
        console.log("DEBUG: currentProfile:", typeof currentProfile !== 'undefined' ? currentProfile : 'undefined');
        console.log("DEBUG: final userCtx used for filtering:", userCtx);

        // Filter for specific tab counts
        const myReports = reports.filter(r => r.user_id === userCtx?.id && !r.is_deleted_by_user);
        const activeReports = reports.filter(r => !r.is_deleted_by_user); // Renamed from allPendingReports to match existing logic
        
        // Filter for In Progress tab (my reports that are in_progress or pending_completion)
        const userInProgressReports = reports.filter(r => {
            return r.user_id === userCtx?.id && 
                   !r.is_deleted_by_user && 
                   ['in_progress', 'pending_completion', 'waiting_for_user_approval'].includes(r.status);
        });
        
        // Filter for Completed tab (my reports that are completed)
        const userCompletedReports = reports.filter(r => {
            return r.user_id === userCtx?.id && 
                   !r.is_deleted_by_user && 
                   r.status === 'completed';
        });
        
        // Filter Trash Bin (ones I trashed, but NOT permanently deleted/hidden)
        let trashedReports = [];
        if (userCtx && userCtx.id) {
            console.log("DEBUG: Filtering trash for user ID:", userCtx.id);
            trashedReports = reports.filter(r => {
                const isTrashed = r.user_id === userCtx.id && r.is_deleted_by_user === true;
                
                // If it's trashed, also check if it's been "permanently deleted" (hidden)
                if (isTrashed) {
                    const hiddenUsers = r.hidden_completed_from_users || [];
                    if (hiddenUsers.includes(userCtx.id)) {
                        console.log("DEBUG: Report is permanently hidden (permanently deleted), skipping tray:", r.id);
                        return false;
                    }
                }
                
                return isTrashed;
            });
        }
        console.log("DEBUG: Trashed reports found:", trashedReports.length);
        
        // Update tab counts
        const myReportsCount = document.querySelector('[data-tab="my-reports"] .count');
        const allReportsCount = document.querySelector('[data-tab="all-reports"] .count');
        const inProgressCount = document.querySelector('[data-tab="in-progress"] .count');
        const completedCount = document.querySelector('[data-tab="completed"] .count');
        const trashCount = document.getElementById('trashCount');
        
        if (myReportsCount) myReportsCount.textContent = `(${myReports.length})`;
        if (allReportsCount) allReportsCount.textContent = `(${activeReports.length})`;
        if (inProgressCount) inProgressCount.textContent = `(${userInProgressReports.length})`;
        if (completedCount) completedCount.textContent = `(${userCompletedReports.length})`;
        if (trashCount) trashCount.textContent = `(${trashedReports.length})`;
        
        // Helper template for empty states
        const noReportsTemplate = (title, subtitle, includeBtn = false) => `
            <div class="no-reports">
                <div class="no-reports-icon">
                    <svg width="80" height="80" viewBox="0 0 24 24" fill="none">
                        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke="#FF8C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <h3>${title}</h3>
                <p>${subtitle}</p>
                ${includeBtn ? '<button class="create-first-report-btn" id="openModalBtn3">Create First Report</button>' : ''}
            </div>
        `;
        
        // Render My Reports
        if (myReportsTab) {
            if (myReports.length === 0) {
                myReportsTab.innerHTML = noReportsTemplate('No reports yet', "Start by reporting a stray animal you've spotted", true);
                const modalBtn = document.getElementById('openModalBtn3');
                if (modalBtn) modalBtn.addEventListener('click', openModal);
            } else {
                myReportsTab.innerHTML = createReportsHtml(myReports, true);
            }
        }
        
        // Render All Reports
        if (allReportsTab) {
            if (activeReports.length === 0) {
                allReportsTab.innerHTML = noReportsTemplate('No reports yet', 'No stray animals have been reported in your area', false);
            } else {
                allReportsTab.innerHTML = createReportsHtml(activeReports, false);
            }
        }
        
        // Render In Progress Tab
        if (inProgressTab) {
            if (userInProgressReports.length === 0) {
                inProgressTab.innerHTML = `
                    <div class="no-reports">
                        <div class="no-reports-icon">
                            <svg width="80" height="80" viewBox="0 0 24 24" fill="none">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" stroke="#17a2b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <h3>No rescues in progress</h3>
                        <p>Your active rescue requests will appear here</p>
                    </div>
                `;
            } else {
                inProgressTab.innerHTML = createReportsHtml(userInProgressReports, true);
            }
        }
        
        // Render Completed Tab
        if (completedTab) {
            if (userCompletedReports.length === 0) {
                completedTab.innerHTML = `
                    <div class="no-reports">
                        <div class="no-reports-icon">
                            <svg width="80" height="80" viewBox="0 0 24 24" fill="none">
                                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <h3>No completed rescues yet</h3>
                        <p>Successfully rescued animals will appear here</p>
                    </div>
                `;
            } else {
                completedTab.innerHTML = createReportsHtml(userCompletedReports, true);
            }
        }
        
        if (trashList && emptyTrashMsg) {
            if (trashedReports.length === 0) {
                emptyTrashMsg.style.display = 'block';
                trashList.style.display = 'none';
            } else {
                emptyTrashMsg.style.display = 'none';
                trashList.style.display = 'block';
                trashList.innerHTML = createReportsHtml(trashedReports, false, true);
            }
        }
        
        // Attach delete listeners
        attachDeleteListeners();
        
        // Fetch rescuer names for in-progress reports
        const inProgressReports = myReports.filter(r => (r.status === 'in_progress' || r.status === 'pending_completion') && r.assigned_rescuer_id);
        inProgressReports.forEach(async (report) => {
            try {
                const res = await fetch(`/api/profile/public/?user_id=${report.assigned_rescuer_id}`, {
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                const el = document.getElementById(`rescuerName-${report.id}`);
                if (el && data.success) {
                    const name = data.profile.full_name || data.profile.username || 'Unknown';
                    el.innerHTML = `<a href="javascript:void(0)" onclick="event.stopPropagation(); openPublicProfileModal({'user_id': '${report.assigned_rescuer_id}'})" style="color: #0c5460; font-weight: bold; text-decoration: underline; cursor: pointer;">${name}</a> is handling the rescue`;
                }
            } catch(e) { console.error('Failed to fetch rescuer name:', e); }
        });
    }
    
    // Create HTML for reports display
    function createReportsHtml(reports, isMyReports = false, isTrash = false) {
        let html = '<div class="reports-list">';
        
        reports.forEach(report => {
            const reportDate = new Date(report.created_at).toLocaleString();
            
            // Check if this is the current user's report
            const userCtx = (typeof currentProfile !== 'undefined' && currentProfile) ? currentProfile : (window.currentUserContext || { id: null });
            const isMyReport = userCtx.id && report.user_id === userCtx.id;
            
            // For users, show rescuer_declined as "pending" (still waiting for rescue)
            let displayStatus = report.status === 'rescuer_declined' ? 'pending' : report.status;
            if (report.status === 'pending_completion') displayStatus = isMyReport ? 'Awaiting Your Review' : 'Pending Review';
            if (isTrash) displayStatus = 'TRASHED';
            
            const statusColor = isTrash ? '#6c757d' : getStatusColor(report.status === 'pending_completion' ? 'pending_completion' : displayStatus);
            const imgUrl = (report.images && report.images.length > 0) ? report.images[0] : report.image_url;
            const hasPhoto = !!imgUrl;
            
            html += `
                <div class="report-card" data-report-id="${report.id}" style="cursor: pointer; border-left: 4px solid ${statusColor};" onclick="if(typeof openReportDetailModal === 'function') openReportDetailModal(JSON.parse(this.dataset.report))" data-report='${JSON.stringify(report).replace(/'/g, "&#39;")}'>
                    <div class="report-header">
                        <div class="report-animal">
                            <span class="animal-type">${report.animal_type}</span>
                            <span class="animal-condition">${report.animal_condition}</span>
                            ${hasPhoto ? '<span class="photo-indicator">📷</span>' : ''}
                        </div>
                        <div class="report-status">
                            <span class="status-badge" style="background-color: ${statusColor}">${displayStatus}</span>
                        </div>
                    </div>
                    <div class="report-body">
                        <p class="report-description">${report.description}</p>
                        ${(report.status === 'in_progress' || report.status === 'pending_completion') && !isTrash && report.assigned_rescuer_id ? `
                        <div class="rescue-in-progress-banner" style="background: linear-gradient(135deg, ${report.status === 'pending_completion' ? '#fff8e1, #ffecb3' : '#e8f4fd, #d1ecf1'}); border-left: 4px solid ${report.status === 'pending_completion' ? '#FF8C00' : '#17a2b8'}; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">${report.status === 'pending_completion' ? '📋' : '🐾'}</span>
                            <div>
                                <div style="font-size: 13px; font-weight: 600; color: ${report.status === 'pending_completion' ? '#856404' : '#0c5460'};">${report.status === 'pending_completion' ? 'Proof Submitted — Review Required' : 'Rescue In Progress'}</div>
                                <div style="font-size: 12px; color: ${report.status === 'pending_completion' ? '#856404' : '#17a2b8'};" id="rescuerName-${report.id}">Loading rescuer info...</div>
                            </div>
                        </div>
                        ` : ''}
                        <div class="report-location">
                            <strong>Location:</strong> ${report.address}
                            ${report.landmark ? `<br><strong>Landmark:</strong> ${report.landmark}` : ''}
                        </div>
                        <div class="report-meta">
                            <span class="report-date">${reportDate}</span>
                            <span class="report-reporter" style="margin-left: 15px; font-size: 13px; color: #666;">
                                <i class="fas fa-user" style="margin-right: 5px;"></i>${report.reporter_name || 'Anonymous'}
                            </span>
                        </div>
                        <div class="report-actions" onclick="event.stopPropagation()">
                            ${isTrash ? `
                                <button onclick="recoverReport('${report.id}')" class="custom-modal-btn primary" style="background: #28a745; margin-right: 10px;">Recover</button>
                                <button onclick="permanentlyDeleteReport('${report.id}')" class="custom-modal-btn danger">Delete Permanently</button>
                            ` : (isMyReports ? `
                                ${!['in_progress', 'pending_completion'].includes(report.status) ? `<button class="delete-report-btn" data-report-id="${report.id}">Delete</button>` : `<span style="font-size: 13px; color: #17a2b8; font-weight: bold; margin-right: 15px;"><i class="fas fa-lock" style="margin-right: 5px;"></i> ${report.status === 'pending_completion' ? 'Pending Review' : 'Active Rescue'}</span>`}
                            ` : '')}
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }
    
    function attachDeleteListeners() {
        const deleteButtons = document.querySelectorAll('.delete-report-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent opening modal
                const reportId = this.getAttribute('data-report-id');
                trashReport(reportId);
            });
        });
    }
    
    
    // Get status color
    function getStatusColor(status) {
        switch(status) {
            case 'pending': return '#ffc107';
            case 'in_progress': return '#17a2b8';
            case 'completed': return '#28a745';
            case 'declined': return '#dc3545';
            case 'pending_completion': return '#e67e22';
            default: return '#6c757d';
        }
    }

    // Modal Delete Button
    const reportDetailDeleteBtn = document.getElementById('reportDetailDeleteBtn');
    if (reportDetailDeleteBtn) {
        reportDetailDeleteBtn.addEventListener('click', function() {
            const reportId = this.getAttribute('data-report-id');
            if (reportId) {
                closeReportDetailModal();
                trashReport(reportId);
            }
        });
    }
    

    
    // Initialize reports on page load - call directly since we're already in DOMContentLoaded
    loadReports();
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
            closeModal();
        }
    });
    
    // Initialize map immediately if map-view tab is already active
    if (document.getElementById('map-view') && document.getElementById('map-view').classList.contains('active')) {
        console.log('Map view is active on load, initializing map...');
        // Increased delay for initial load
        setTimeout(initializeMap, 800);
    }
    
    // Global Trash Bin Functions (attached to window for HTML access)
    window.trashReport = async function(reportId) {
        showCustomConfirm('Are you sure you want to move this report to the trash?', 'Move to Trash', async (confirmed) => {
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
                    showCustomAlert('Report moved to trash bin.', 'Success');
                    await loadReports();
                } else {
                    showCustomAlert('Failed to move to trash: ' + (result.error || 'Unknown error'), 'Error');
                }
            } catch (e) {
                console.error('Error trashing report:', e);
                showCustomAlert('An error occurred while moving the report to trash.', 'Error');
            }
        });
    };

    window.recoverReport = async function(reportId) {
        try {
            const response = await fetch(`/api/reports/${reportId}/recover/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const result = await response.json();
            if (result.success) {
                showCustomAlert('Report recovered successfully.', 'Success');
                await loadReports();
            } else {
                showCustomAlert('Failed to recover report: ' + (result.error || 'Unknown error'), 'Error');
            }
        } catch (e) {
            console.error('Error recovering report:', e);
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
                    await loadReports();
                } else {
                    showCustomAlert('Failed to delete report: ' + (result.error || 'Unknown error'), 'Error');
                }
            } catch (e) {
                console.error('Error deleting report:', e);
                showCustomAlert('An error occurred during permanent deletion.', 'Error');
            }
        });
    };
});
