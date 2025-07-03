/**
 * API helper functions for Booking Vision
 * This file handles all AJAX requests to the backend
 * Location: booking_vision_APP/static/js/api.js
 */

const BookingVisionAPI = {
    // Base API configuration
    getCsrfToken: function() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    },

    // Dashboard Stats API
    getDashboardStats: function() {
        return fetch('/api/dashboard/stats/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
            }
        }).then(response => response.json());
    },

    // Revenue Analytics API
    getRevenueAnalytics: function(period = '12months') {
        return fetch(`/api/analytics/revenue/?period=${period}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
            }
        }).then(response => response.json());
    },

    // Toggle AI Feature
    toggleAIFeature: function(feature, enabled) {
        return fetch(`/api/ai/toggle/${feature}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify({ enabled: enabled })
        }).then(response => response.json());
    },

    // Simulate real-time updates (polling)
    startDashboardUpdates: function(updateInterval = 30000) {
        // Update dashboard stats every 30 seconds
        setInterval(() => {
            this.getDashboardStats().then(data => {
                // Update dashboard elements
                const elements = {
                    'total-properties': data.total_properties,
                    'total-bookings': data.total_bookings,
                    'total-revenue': `$${data.total_revenue.toFixed(2)}`,
                    'occupancy-rate': `${data.occupancy_rate}%`
                };

                Object.keys(elements).forEach(id => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = elements[id];
                    }
                });
            }).catch(error => {
                console.error('Error updating dashboard:', error);
            });
        }, updateInterval);
    }
};

// Initialize API on page load
document.addEventListener('DOMContentLoaded', function() {
    // Only start updates on dashboard page
    if (document.getElementById('dashboard-container')) {
        BookingVisionAPI.startDashboardUpdates();
    }
});

// Export for use in other scripts
window.BookingVisionAPI = BookingVisionAPI;