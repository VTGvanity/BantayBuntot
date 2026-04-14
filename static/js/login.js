document.addEventListener('DOMContentLoaded', function() {
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const formTitle = document.getElementById('form-title');
    const formDescription = document.getElementById('form-description');
    const loginBtn = document.getElementById('login-btn');
    const emailInput = document.getElementById('id_username');
    const userRoleInput = document.getElementById('id_user_role');
    const forgotPasswordLink = document.getElementById('forgot-password-link');
    const resetPasswordModal = document.getElementById('resetPasswordModal');
    const closeResetModal = document.getElementById('closeResetModal');
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    
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
                formTitle.textContent = 'Rescuer Login';
                formDescription.textContent = 'Help rescue and care for stray animals';
                loginBtn.textContent = 'Login as Rescuer';
                emailInput.placeholder = 'rescuer@example.com';
            } else {
                formTitle.textContent = 'User Login';
                formDescription.textContent = 'Report and track stray animals in your community';
                loginBtn.textContent = 'Login as User';
                emailInput.placeholder = 'user@example.com';
            }
            
            // Update hidden role input
            if (userRoleInput) {
                userRoleInput.value = role;
            }

            // Update Google login link to include role
            const googleBtn = document.querySelector('.google-login-btn');
            if (googleBtn) {
                const baseUrl = googleBtn.getAttribute('href').split('?')[0];
                googleBtn.setAttribute('href', `${baseUrl}?role=${role}`);
            }
        });
    });

    // Initialize Google link on load
    const googleBtn = document.querySelector('.google-login-btn');
    if (googleBtn && userRoleInput) {
        const baseUrl = googleBtn.getAttribute('href').split('?')[0];
        googleBtn.setAttribute('href', `${baseUrl}?role=${userRoleInput.value}`);
    }
});
