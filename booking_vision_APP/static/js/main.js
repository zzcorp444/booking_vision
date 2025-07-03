/*
Main JavaScript file for Booking Vision application.
This file contains common functionality and AI-powered features.
Location: booking_vision_APP/static/js/main.js
*/

// Global variables
let charts = {};
let aiFeatures = {
    pricing: false,
    maintenance: false,
    guestExperience: false,
    businessIntelligence: false
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadDashboardData();
});

// Initialize application
function initializeApp() {
    console.log('Booking Vision App Initialized');
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialize AI features
    initializeAIFeatures();
}

// Setup event listeners
function setupEventListeners() {
    // Navigation highlighting
    highlightActiveNavItem();
    
    // Form enhancements
    enhanceForms();
    
    // Real-time updates
    setupRealTimeUpdates();
    
    // AI feature toggles
    setupAIFeatureToggles();
}

// Highlight active navigation item
function highlightActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Enhance forms with validation and UX improvements
function enhanceForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Add loading states to submit buttons
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.innerHTML = '<span class="loading-spinner"></span> Processing...';
            this.disabled = true;
        });
    });
}

// Setup real-time updates using WebSockets
function setupRealTimeUpdates() {
    if (typeof WebSocket !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/updates/`;
        
        const socket = new WebSocket(wsUrl);
        
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleRealTimeUpdate(data);
        };
        
        socket.onclose = function() {
            console.log('WebSocket connection closed');
            // Attempt to reconnect after 5 seconds
            setTimeout(() => {
                setupRealTimeUpdates();
            }, 5000);
        };
    }
}

// Handle real-time updates
function handleRealTimeUpdate(data) {
    switch(data.type) {
        case 'booking_update':
            updateBookingData(data.payload);
            break;
        case 'pricing_update':
            updatePricingData(data.payload);
            break;
        case 'maintenance_alert':
            showMaintenanceAlert(data.payload);
            break;
        case 'guest_message':
            showGuestMessage(data.payload);
            break;
        default:
            console.log('Unknown update type:', data.type);
    }
}

// Initialize AI Features
function initializeAIFeatures() {
    // Smart Pricing AI
    if (document.getElementById('smart-pricing-container')) {
        initializeSmartPricing();
    }
    
    // Predictive Maintenance AI
    if (document.getElementById('predictive-maintenance-container')) {
        initializePredictiveMaintenance();
    }
    
    // Guest Experience AI
    if (document.getElementById('guest-experience-container')) {
        initializeGuestExperience();
    }
    
    // Business Intelligence AI
    if (document.getElementById('business-intelligence-container')) {
        initializeBusinessIntelligence();
    }
}

// Smart Pricing AI Functions
function initializeSmartPricing() {
    console.log('Initializing Smart Pricing AI...');
    
    // Load pricing data
    loadPricingData();
    
    // Setup pricing chart
    setupPricingChart();
    
    // AI pricing recommendations
    loadPricingRecommendations();
}

function loadPricingData() {
    fetch('/api/pricing/data/')
        .then(response => response.json())
        .then(data => {
            updatePricingDisplay(data);
        })
        .catch(error => {
            console.error('Error loading pricing data:', error);
        });
}

function setupPricingChart() {
    const ctx = document.getElementById('pricingChart');
    if (!ctx) return;
    
    charts.pricing = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Current Pricing',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4
            }, {
                label: 'AI Recommended Pricing',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                borderDash: [5, 5]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Pricing Optimization'
                },
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Price ($)'
                    }
                }
            }
        }
    });
}

// Predictive Maintenance AI Functions
function initializePredictiveMaintenance() {
    console.log('Initializing Predictive Maintenance AI...');
    
    // Load maintenance predictions
    loadMaintenancePredictions();
    
    // Setup maintenance alerts
    setupMaintenanceAlerts();
}

function loadMaintenancePredictions() {
    fetch('/api/maintenance/predictions/')
        .then(response => response.json())
        .then(data => {
            updateMaintenanceDisplay(data);
        })
        .catch(error => {
            console.error('Error loading maintenance predictions:', error);
        });
}

function setupMaintenanceAlerts() {
    // Check for urgent maintenance items
    setInterval(() => {
        checkUrgentMaintenance();
    }, 60000); // Check every minute
}

function checkUrgentMaintenance() {
    fetch('/api/maintenance/urgent/')
        .then(response => response.json())
        .then(data => {
            if (data.urgent_items && data.urgent_items.length > 0) {
                showMaintenanceAlert(data.urgent_items);
            }
        })
        .catch(error => {
            console.error('Error checking urgent maintenance:', error);
        });
}

// Guest Experience AI Functions
function initializeGuestExperience() {
    console.log('Initializing Guest Experience AI...');
    
    // Load guest preferences
    loadGuestPreferences();
    
    // Setup automated responses
    setupAutomatedResponses();
    
    // Initialize sentiment analysis
    initializeSentimentAnalysis();
}

function loadGuestPreferences() {
    fetch('/api/guests/preferences/')
        .then(response => response.json())
        .then(data => {
            updateGuestPreferencesDisplay(data);
        })
        .catch(error => {
            console.error('Error loading guest preferences:', error);
        });
}

function setupAutomatedResponses() {
    const messageContainer = document.getElementById('guest-messages');
    if (!messageContainer) return;
    
    // Setup auto-response suggestions
    const messageInputs = document.querySelectorAll('.message-input');
    messageInputs.forEach(input => {
        input.addEventListener('input', function() {
            generateResponseSuggestions(this.value);
        });
    });
}

function initializeSentimentAnalysis() {
    // Analyze existing messages
    const messages = document.querySelectorAll('.guest-message');
    messages.forEach(message => {
        analyzeSentiment(message);
    });
}

function analyzeSentiment(messageElement) {
    const text = messageElement.textContent;
    
    fetch('/api/ai/sentiment-analysis/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        addSentimentIndicator(messageElement, data.sentiment);
    })
    .catch(error => {
        console.error('Error analyzing sentiment:', error);
    });
}

// Business Intelligence AI Functions
function initializeBusinessIntelligence() {
    console.log('Initializing Business Intelligence AI...');
    
    // Load market data
    loadMarketData();
    
    // Setup competitor analysis
    setupCompetitorAnalysis();
    
    // Initialize demand forecasting
    initializeDemandForecasting();
}

function loadMarketData() {
    fetch('/api/market/data/')
        .then(response => response.json())
        .then(data => {
            updateMarketDataDisplay(data);
        })
        .catch(error => {
            console.error('Error loading market data:', error);
        });
}

function setupCompetitorAnalysis() {
    const ctx = document.getElementById('competitorChart');
    if (!ctx) return;
    
    charts.competitor = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Pricing', 'Reviews', 'Occupancy', 'Response Time', 'Amenities'],
            datasets: [{
                label: 'Your Properties',
                data: [0, 0, 0, 0, 0],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.2)'
            }, {
                label: 'Market Average',
                data: [0, 0, 0, 0, 0],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.2)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Competitor Analysis'
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 10
                }
            }
        }
    });
}

// Utility Functions
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

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

// Dashboard Data Loading
function loadDashboardData() {
    if (document.getElementById('dashboard-container')) {
        loadDashboardStats();
        loadRecentBookings();
        loadRevenueChart();
        loadOccupancyChart();
    }
}

function loadDashboardStats() {
    fetch('/api/dashboard/stats/')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.error('Error loading dashboard stats:', error);
        });
}

function updateDashboardStats(data) {
    // Update stat cards
    if (data.total_properties) {
        document.getElementById('total-properties').textContent = data.total_properties;
    }
    if (data.total_bookings) {
        document.getElementById('total-bookings').textContent = data.total_bookings;
    }
    if (data.total_revenue) {
        document.getElementById('total-revenue').textContent = formatCurrency(data.total_revenue);
    }
    if (data.occupancy_rate) {
        document.getElementById('occupancy-rate').textContent = data.occupancy_rate + '%';
    }
}

function loadRevenueChart() {
    const ctx = document.getElementById('revenueChart');
    if (!ctx) return;
    
    fetch('/api/analytics/revenue/')
        .then(response => response.json())
        .then(data => {
            charts.revenue = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: data.revenue,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Revenue Over Time'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Revenue ($)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading revenue chart:', error);
        });
}

// AI Feature Toggles
function setupAIFeatureToggles() {
    const toggles = document.querySelectorAll('.ai-feature-toggle');
    
    toggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const feature = this.dataset.feature;
            const enabled = this.checked;
            
            toggleAIFeature(feature, enabled);
        });
    });
}

function toggleAIFeature(feature, enabled) {
    fetch(`/api/ai/toggle/${feature}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            aiFeatures[feature] = enabled;
            showNotification(`${feature} AI feature ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } else {
            showNotification('Error toggling AI feature', 'error');
        }
    })
    .catch(error => {
        console.error('Error toggling AI feature:', error);
        showNotification('Error toggling AI feature', 'error');
    });
}

// Export functions for global use
window.BookingVision = {
    showNotification,
    formatCurrency,
    formatDate,
    getCookie,
    toggleAIFeature,
    charts,
    aiFeatures
};