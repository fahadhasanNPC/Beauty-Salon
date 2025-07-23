document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle - Create toggle button if it doesn't exist
    let menuToggle = document.querySelector('.menu-toggle');
    
    if (!menuToggle) {
        menuToggle = document.createElement('div');
        menuToggle.className = 'menu-toggle';
        menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        
        const navbarContainer = document.querySelector('.navbar .container');
        const navbarMenu = document.querySelector('.navbar-menu');
        
        if (navbarContainer && navbarMenu) {
            navbarContainer.insertBefore(menuToggle, navbarMenu);
        }
    }
    
    const navbarMenu = document.querySelector('.navbar-menu');
    
    // Add click event to toggle button
    menuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        navbarMenu.classList.toggle('active');
        menuToggle.innerHTML = navbarMenu.classList.contains('active') 
            ? '<i class="fas fa-times"></i>' 
            : '<i class="fas fa-bars"></i>';
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (
            navbarMenu && 
            navbarMenu.classList.contains('active') && 
            !navbarMenu.contains(event.target) && 
            !menuToggle.contains(event.target)
        ) {
            navbarMenu.classList.remove('active');
            menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href !== '#') {
                e.preventDefault();
                
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });

    // Add animation to elements when they come into view
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.feature-card, .about, .salon-card');
        
        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            if (elementPosition < windowHeight - 100) {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }
        });
    };

    // Set initial state for animation
    document.querySelectorAll('.feature-card, .about, .salon-card').forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
    });

    // Run animation on load and scroll
    window.addEventListener('load', animateOnScroll);
    window.addEventListener('scroll', animateOnScroll);

    // Form field enhancement - inputs
    const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"]');
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
            if (this.value) {
                this.parentElement.classList.add('filled');
            } else {
                this.parentElement.classList.remove('filled');
            }
        });
        
        // Check initial state
        if (input.value) {
            input.parentElement.classList.add('filled');
        }
    });
    
    // Password visibility toggle
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        // Create toggle button
        const toggleBtn = document.createElement('span');
        toggleBtn.className = 'password-toggle';
        toggleBtn.innerHTML = '<i class="far fa-eye"></i>';
        
        // Insert after input
        if (input.parentNode) {
            input.parentNode.style.position = 'relative';
            input.parentNode.appendChild(toggleBtn);
            
            // Position the toggle button
            toggleBtn.style.position = 'absolute';
            toggleBtn.style.right = '15px';
            toggleBtn.style.top = '50%';
            toggleBtn.style.transform = 'translateY(-50%)';
            toggleBtn.style.cursor = 'pointer';
            toggleBtn.style.color = '#777';
            
            // Add event listener
            toggleBtn.addEventListener('click', function() {
                if (input.type === 'password') {
                    input.type = 'text';
                    this.innerHTML = '<i class="far fa-eye-slash"></i>';
                } else {
                    input.type = 'password';
                    this.innerHTML = '<i class="far fa-eye"></i>';
                }
            });
        }
    });

    // Add hover effect to salon cards
    const salonCards = document.querySelectorAll('.salon-card');
    salonCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.querySelector('.salon-info').style.backgroundColor = 'rgba(233, 223, 195, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.querySelector('.salon-info').style.backgroundColor = '';
        });
    });
});