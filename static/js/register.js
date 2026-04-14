document.addEventListener('DOMContentLoaded', function() {
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const formTitle = document.getElementById('form-title');
    const formDescription = document.getElementById('form-description');
    const registerBtn = document.getElementById('register-btn');
    const userTypeInput = document.getElementById('id_user_type');
    const emailInput = document.getElementById('id_email');
    const registerForm = document.querySelector('form');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const successModal = document.getElementById('successModal');
    const errorModal = document.getElementById('errorModal');
    const errorMessage = document.getElementById('errorMessage');
    
    // Role toggle functionality
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            toggleBtns.forEach(b => b.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the role
            const role = this.getAttribute('data-role');
            
            // Update form content based on role
            if (role === 'rescuer') {
                formTitle.textContent = 'Rescuer Registration';
                formDescription.textContent = 'Join our team of animal rescuers';
                registerBtn.textContent = 'Register as Rescuer';
                emailInput.placeholder = 'rescuer@example.com';
                userTypeInput.value = 'rescuer';
            } else {
                formTitle.textContent = 'User Registration';
                formDescription.textContent = 'Join us in helping stray animals in your community';
                registerBtn.textContent = 'Register as User';
                emailInput.placeholder = 'user@example.com';
                userTypeInput.value = 'user';
            }
        });
    });
    
    // Password toggle functionality
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const eyeIcon = this.querySelector('.eye-icon');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                eyeIcon.textContent = '👁️';
            }
        });
    });
    
    // Form submission with validation
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = password1Input ? password1Input.value : '';
            const strength = checkPasswordStrength(password);
            
            if (strength.score < 5) {
                e.preventDefault();
                errorMessage.textContent = 'Please follow all password requirements: ' + strength.feedback.join(', ');
                errorModal.style.display = 'flex';
                return;
            }

            // Show loading overlay
            loadingOverlay.style.display = 'flex';
            registerBtn.disabled = true;
            registerBtn.textContent = 'Creating Account...';
        });
    }
    
    // Modal functionality
    const successModalBtn = document.getElementById('successModalBtn');
    const errorModalBtn = document.getElementById('errorModalBtn');
    const closeErrorModal = document.getElementById('closeErrorModal');
    
    if (successModalBtn) {
        successModalBtn.addEventListener('click', function() {
            window.location.href = '/';
        });
    }
    
    if (errorModalBtn) {
        errorModalBtn.addEventListener('click', function() {
            errorModal.style.display = 'none';
            registerBtn.disabled = false;
            registerBtn.textContent = userTypeInput.value === 'rescuer' ? 'Register as Rescuer' : 'Register as User';
        });
    }
    
    if (closeErrorModal) {
        closeErrorModal.addEventListener('click', function() {
            errorModal.style.display = 'none';
        });
    }
    
    // Close modals when clicking outside
    [successModal, errorModal].forEach(modal => {
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }
    });
    
    // Check for Django messages and show appropriate modal
    const messages = document.querySelectorAll('.messages .message');
    messages.forEach(message => {
        if (message.classList.contains('success')) {
            successModal.style.display = 'flex';
        } else if (message.classList.contains('error')) {
            errorMessage.textContent = message.textContent;
            errorModal.style.display = 'flex';
        }
    });
    
    // Password strength indicator
    const password1Input = document.getElementById('id_password1');
    const passwordRequirements = document.querySelector('.password-requirements');
    
    if (password1Input && passwordRequirements) {
        password1Input.addEventListener('input', function() {
            const password = this.value;
            const strength = checkPasswordStrength(password);
            
            // Update requirements display based on strength
            if (strength.score >= 3) {
                passwordRequirements.style.color = '#28a745';
            } else if (strength.score >= 2) {
                passwordRequirements.style.color = '#ffc107';
            } else {
                passwordRequirements.style.color = '#dc3545';
            }
        });
    }
    
    // Password confirmation check
    const password2Input = document.getElementById('id_password2');
    if (password1Input && password2Input) {
        password2Input.addEventListener('input', function() {
            const password1 = password1Input.value;
            const password2 = this.value;
            
            if (password2 && password1 !== password2) {
                this.setCustomValidity('Passwords do not match');
            } else {
                this.setCustomValidity('');
            }
        });
    }

    // Field uniqueness validation
    const usernameInput = document.getElementById('id_username');
    const phoneInput = document.getElementById('id_phone');
    const emailError = document.getElementById('email-error');
    const usernameError = document.getElementById('username-error');
    const phoneError = document.getElementById('phone-error');
    
    // Track validity of unique fields
    const fieldValidity = {
        email: true,
        username: true,
        phone: true
    };
    
    function updateRegisterButton() {
        const isAnyFieldInvalid = !fieldValidity.email || !fieldValidity.username || !fieldValidity.phone;
        const registerBtn = document.getElementById('register-btn');
        if (registerBtn) {
            registerBtn.disabled = isAnyFieldInvalid;
            if (isAnyFieldInvalid) {
                registerBtn.style.opacity = '0.7';
                registerBtn.style.cursor = 'not-allowed';
            } else {
                registerBtn.style.opacity = '1';
                registerBtn.style.cursor = 'pointer';
            }
        }
    }
    
    async function checkFieldUniqueness(field, value, errorElement) {
        if (!value) {
            errorElement.style.display = 'none';
            fieldValidity[field] = true;
            updateRegisterButton();
            return;
        }
        
        // Basic format checks
        if (field === 'phone' && value.length !== 10) {
            // Already handled by HTML5 validation, but let's be safe
            fieldValidity[field] = true; // Let browser catch the bad format
            updateRegisterButton();
            return;
        }

        try {
            const response = await fetch(`/check-field-uniqueness/?field=${field}&value=${encodeURIComponent(value)}`);
            const data = await response.json();
            
            if (!data.available) {
                errorElement.textContent = `This ${field} is already taken.`;
                errorElement.style.display = 'block';
                fieldValidity[field] = false;
            } else {
                errorElement.style.display = 'none';
                fieldValidity[field] = true;
            }
            updateRegisterButton();
        } catch (error) {
            console.error('Error checking uniqueness:', error);
        }
    }
    
    // Add listeners for uniqueness checks
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            checkFieldUniqueness('email', this.value, emailError);
        });
    }
    
    if (usernameInput) {
        usernameInput.addEventListener('blur', function() {
            checkFieldUniqueness('username', this.value, usernameError);
        });
    }
    
    if (phoneInput) {
        phoneInput.addEventListener('blur', function() {
            checkFieldUniqueness('phone', this.value, phoneError);
        });
    }
});

// End of register.js
