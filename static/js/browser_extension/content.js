// booking_vision_APP/static/js/browser_extension/content.js
/**
 * Browser Extension Content Script
 * Captures booking data from OTA websites
 */

const BookingVisionExtension = {
    channels: {
        'airbnb.com': {
            name: 'Airbnb',
            selectors: {
                reservations: '[data-testid="reservation-card"]',
                guestName: '[data-testid="guest-name"]',
                dates: '[data-testid="reservation-dates"]',
                confirmationCode: '[data-testid="confirmation-code"]',
                status: '[data-testid="reservation-status"]',
                price: '[data-testid="total-price"]'
            }
        },
        'booking.com': {
            name: 'Booking.com',
            selectors: {
                reservations: '.reservation-item',
                guestName: '.guest-name',
                dates: '.reservation-dates',
                confirmationCode: '.confirmation-number',
                status: '.reservation-status',
                price: '.total-price'
            }
        },
        'vrbo.com': {
            name: 'VRBO',
            selectors: {
                reservations: '.reservation-row',
                guestName: '.traveler-name',
                dates: '.stay-dates',
                confirmationCode: '.confirmation-code',
                status: '.booking-status',
                price: '.total-amount'
            }
        }
    },

    init() {
        this.detectChannel();
        this.setupObservers();
        this.injectCaptureUI();
    },

    detectChannel() {
        const hostname = window.location.hostname;
        for (const [domain, config] of Object.entries(this.channels)) {
            if (hostname.includes(domain)) {
                this.currentChannel = config;
                this.currentDomain = domain;
                break;
            }
        }
    },

    setupObservers() {
        if (!this.currentChannel) return;

        // Watch for page changes (SPA navigation)
        const observer = new MutationObserver(() => {
            if (this.isReservationsPage()) {
                this.captureReservations();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial capture
        if (this.isReservationsPage()) {
            setTimeout(() => this.captureReservations(), 2000);
        }
    },

    isReservationsPage() {
        const url = window.location.href;
        const reservationPatterns = [
            '/reservations',
            '/hosting/reservations',
            '/mysettings/bookings',
            '/owner/bookings'
        ];
        return reservationPatterns.some(pattern => url.includes(pattern));
    },

    captureReservations() {
        const selectors = this.currentChannel.selectors;
        const reservations = document.querySelectorAll(selectors.reservations);
        const capturedData = [];

        reservations.forEach(reservation => {
            try {
                const data = {
                    channel: this.currentChannel.name,
                    guestName: this.extractText(reservation, selectors.guestName),
                    dates: this.extractText(reservation, selectors.dates),
                    confirmationCode: this.extractText(reservation, selectors.confirmationCode),
                    status: this.extractText(reservation, selectors.status),
                    price: this.extractText(reservation, selectors.price),
                    capturedAt: new Date().toISOString(),
                    url: window.location.href
                };

                // Parse dates
                const parsedDates = this.parseDates(data.dates);
                if (parsedDates) {
                    data.checkIn = parsedDates.checkIn;
                    data.checkOut = parsedDates.checkOut;
                }

                // Parse price
                data.totalPrice = this.parsePrice(data.price);

                capturedData.push(data);
            } catch (error) {
                console.error('Error capturing reservation:', error);
            }
        });

        if (capturedData.length > 0) {
            this.saveToExtensionStorage(capturedData);
            this.showNotification(`Captured ${capturedData.length} reservations`);
        }
    },

    extractText(element, selector) {
        const target = element.querySelector(selector);
        return target ? target.textContent.trim() : '';
    },

    parseDates(dateString) {
        // Try different date formats
        const patterns = [
            /(\w+\s+\d+)\s*-\s*(\w+\s+\d+)/,  // Jan 1 - Jan 5
            /(\d{1,2}\/\d{1,2}\/\d{4})\s*-\s*(\d{1,2}\/\d{1,2}\/\d{4})/,  // 01/01/2024 - 01/05/2024
        ];

        for (const pattern of patterns) {
            const match = dateString.match(pattern);
            if (match) {
                return {
                    checkIn: match[1],
                    checkOut: match[2]
                };
            }
        }

        return null;
    },

    parsePrice(priceString) {
        const cleanPrice = priceString.replace(/[^\d.]/g, '');
        return parseFloat(cleanPrice) || 0;
    },

    saveToExtensionStorage(data) {
        // Save to extension storage
        chrome.storage.local.get(['bookingVisionData'], (result) => {
            const existingData = result.bookingVisionData || [];
            const newData = [...existingData, ...data];
            
            // Remove duplicates based on confirmation code
            const uniqueData = newData.filter((item, index, self) =>
                index === self.findIndex((t) => t.confirmationCode === item.confirmationCode)
            );

            chrome.storage.local.set({ bookingVisionData: uniqueData }, () => {
                console.log('Data saved to extension storage');
            });
        });

        // Send to Booking Vision server
        this.sendToServer(data);
    },

    sendToServer(data) {
        // Get user token from extension storage
        chrome.storage.sync.get(['bookingVisionToken', 'bookingVisionUrl'], (result) => {
            if (result.bookingVisionToken && result.bookingVisionUrl) {
                fetch(`${result.bookingVisionUrl}/api/extension/sync/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Token ${result.bookingVisionToken}`
                    },
                    body: JSON.stringify({
                        channel: this.currentChannel.name,
                        bookings: data
                    })
                })
                .then(response => response.json())
                .then(result => {
                    console.log('Data sent to server:', result);
                })
                .catch(error => {
                    console.error('Error sending data to server:', error);
                });
            }
        });
    },

    injectCaptureUI() {
        // Inject a floating button for manual capture
        const button = document.createElement('div');
        button.id = 'booking-vision-capture-btn';
        button.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #3b82f6;
                color: white;
                padding: 12px 20px;
                border-radius: 25px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9999;
                font-family: Arial, sans-serif;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/>
                </svg>
                Capture Bookings
            </div>
        `;

        button.addEventListener('click', () => {
            this.captureReservations();
        });

        document.body.appendChild(button);
    },

    showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-family: Arial, sans-serif;
            font-size: 14px;
            animation: slideIn 0.3s ease-out;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => BookingVisionExtension.init());
} else {
    BookingVisionExtension.init();
}