/**
 * Clickstream Tracker SDK
 *
 * Lightweight JavaScript tracker for collecting user interactions.
 * Sends events to the Clickstream Analytics backend.
 */

(function(window) {
    'use strict';

    // Configuration
    const DEFAULT_CONFIG = {
        endpoint: '/api/v1/events',
        batchSize: 10,
        flushInterval: 5000,
        debug: false,
        trackClicks: true,
        trackViews: true,
        trackScroll: false,
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
    };

    // Session storage keys
    const SESSION_KEY = 'clickstream_session_id';
    const USER_KEY = 'clickstream_user_id';
    const LAST_ACTIVITY_KEY = 'clickstream_last_activity';

    /**
     * Generate UUID v4
     */
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Get or create session ID
     */
    function getSessionId(config) {
        const lastActivity = parseInt(sessionStorage.getItem(LAST_ACTIVITY_KEY) || '0');
        const now = Date.now();

        // Check if session expired
        if (now - lastActivity > config.sessionTimeout) {
            sessionStorage.removeItem(SESSION_KEY);
        }

        let sessionId = sessionStorage.getItem(SESSION_KEY);
        if (!sessionId) {
            sessionId = 'sess-' + generateUUID().substring(0, 12);
            sessionStorage.setItem(SESSION_KEY, sessionId);
        }

        sessionStorage.setItem(LAST_ACTIVITY_KEY, now.toString());
        return sessionId;
    }

    /**
     * Get or create user ID
     */
    function getUserId() {
        let userId = localStorage.getItem(USER_KEY);
        if (!userId) {
            userId = Math.floor(Math.random() * 1000000);
            localStorage.setItem(USER_KEY, userId.toString());
        }
        return parseInt(userId);
    }

    /**
     * Detect device type
     */
    function getDeviceType() {
        const ua = navigator.userAgent.toLowerCase();
        if (/ipad|tablet|playbook|silk/.test(ua)) {
            return 'tablet';
        }
        if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/.test(ua)) {
            return 'mobile';
        }
        return 'desktop';
    }

    /**
     * Main Tracker Class
     */
    class Tracker {
        constructor() {
            this.config = { ...DEFAULT_CONFIG };
            this.eventQueue = [];
            this.viewCount = 0;
            this.clickCount = 0;
            this.flushTimer = null;
            this.initialized = false;
        }

        /**
         * Initialize the tracker
         */
        init(options = {}) {
            if (this.initialized) {
                this.log('Tracker already initialized');
                return this;
            }

            this.config = { ...DEFAULT_CONFIG, ...options };
            this.sessionId = getSessionId(this.config);
            this.userId = getUserId();
            this.deviceType = getDeviceType();

            this.log('Initializing Clickstream Tracker...');
            this.log('Session ID:', this.sessionId);
            this.log('User ID:', this.userId);
            this.log('Device Type:', this.deviceType);

            // Setup event listeners
            this.setupListeners();

            // Start flush timer
            this.startFlushTimer();

            // Track initial page view
            if (this.config.trackViews) {
                this.trackView();
            }

            // Flush on page unload
            window.addEventListener('beforeunload', () => this.flush());

            this.initialized = true;
            this.updateStatus('connected');

            return this;
        }

        /**
         * Setup event listeners
         */
        setupListeners() {
            // Click tracking - single global handler
            if (this.config.trackClicks) {
                document.addEventListener('click', (e) => this.handleClick(e), { capture: false, passive: true });
            }
        }

        /**
         * Handle click event
         */
        handleClick(event) {
            const target = event.target;
            const element = target.closest('[id], [data-track], button, a');

            if (!element) return;

            const elementId = element.id ?
                '#' + element.id :
                element.getAttribute('data-track') ||
                element.tagName.toLowerCase();

            const eventTitle = element.getAttribute('data-track') ||
                element.textContent?.trim().substring(0, 50) ||
                'click';

            this.trackClick(eventTitle, element, event);
        }

        /**
         * Track page view
         */
        trackView(customUrl = null) {
            const event = this.createEvent('view', {
                url: customUrl || window.location.pathname + window.location.search,
                referrer: document.referrer,
            });

            this.queueEvent(event);
            this.viewCount++;
            this.updateViewCount();
            this.logEvent('view', event);
        }

        /**
         * Track click event
         */
        trackClick(eventTitle, element, mouseEvent) {
            const rect = element.getBoundingClientRect();
            const x = mouseEvent ? mouseEvent.clientX : 0;
            const y = mouseEvent ? mouseEvent.clientY : 0;

            const elementId = element.id ?
                '#' + element.id :
                element.className ?
                    '.' + element.className.split(' ')[0] :
                    element.tagName.toLowerCase();

            const event = this.createEvent('click', {
                url: window.location.pathname + window.location.search,
                referrer: document.referrer,
                payload: {
                    event_title: eventTitle,
                    element_id: elementId,
                    x: Math.round(x),
                    y: Math.round(y),
                }
            });

            this.queueEvent(event);
            this.clickCount++;
            this.updateClickCount();
            this.logEvent('click', event);
        }

        /**
         * Track custom event
         */
        track(eventTitle, data = {}) {
            const event = this.createEvent('click', {
                url: window.location.pathname + window.location.search,
                payload: {
                    event_title: eventTitle,
                    ...data,
                }
            });

            this.queueEvent(event);
            this.logEvent('custom', event);
        }

        /**
         * Create event object
         */
        createEvent(type, data) {
            return {
                type: type,
                session_id: this.sessionId,
                user_id: this.userId,
                url: data.url || window.location.pathname,
                created_at: new Date().toISOString(),
                referrer: data.referrer || document.referrer,
                device_type: this.deviceType,
                user_agent: navigator.userAgent,
                payload: data.payload || null,
            };
        }

        /**
         * Add event to queue
         */
        queueEvent(event) {
            this.eventQueue.push(event);

            // Flush if batch size reached
            if (this.eventQueue.length >= this.config.batchSize) {
                this.flush();
            }
        }

        /**
         * Flush event queue to server
         */
        async flush() {
            if (this.eventQueue.length === 0) return;

            const events = [...this.eventQueue];
            this.eventQueue = [];

            try {
                const response = await fetch(this.config.endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ events }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const result = await response.json();
                this.log(`Flushed ${events.length} events, processed: ${result.processed}`);
                this.updateStatus('connected');

            } catch (error) {
                this.log('Failed to send events:', error.message);
                this.updateStatus('error');

                // Re-queue events on failure
                this.eventQueue = [...events, ...this.eventQueue];
            }
        }

        /**
         * Start periodic flush timer
         */
        startFlushTimer() {
            if (this.flushTimer) {
                clearInterval(this.flushTimer);
            }
            this.flushTimer = setInterval(() => this.flush(), this.config.flushInterval);
        }

        /**
         * Get session ID
         */
        getSessionId() {
            return this.sessionId;
        }

        /**
         * Get user ID
         */
        getUserId() {
            return this.userId;
        }

        /**
         * Logging helper
         */
        log(...args) {
            if (this.config.debug) {
                console.log('[Clickstream]', ...args);
            }
        }

        /**
         * Log event to debug panel
         */
        logEvent(type, event) {
            const logEl = document.getElementById('tracker-log');
            if (!logEl) return;

            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `
                <span class="log-time">${time}</span>
                <span class="log-type log-${type}">${type}</span>
                <span class="log-detail">${event.payload?.event_title || event.url}</span>
            `;

            logEl.insertBefore(entry, logEl.firstChild);

            // Keep only last 10 entries
            while (logEl.children.length > 10) {
                logEl.removeChild(logEl.lastChild);
            }
        }

        /**
         * Update status indicator
         */
        updateStatus(status) {
            const statusEl = document.getElementById('tracker-status');
            if (!statusEl) return;

            statusEl.className = 'tracker-status status-' + status;
        }

        /**
         * Update view count display
         */
        updateViewCount() {
            const el = document.getElementById('view-count');
            if (el) el.textContent = this.viewCount;
        }

        /**
         * Update click count display
         */
        updateClickCount() {
            const el = document.getElementById('click-count');
            if (el) el.textContent = this.clickCount;
        }
    }

    // Create global instance
    window.ClickstreamTracker = new Tracker();

})(window);
