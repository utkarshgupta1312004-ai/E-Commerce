/**
 * Cartivo AI Shopping Assistant - Client-Side Controller & Action Dispatcher
 */
(function () {
    'use strict';

    class AssistantWidget {
        constructor() {
            this.launcherBtn = document.getElementById('assistant-launcher');
            this.drawer = document.getElementById('assistant-drawer');
            this.closeBtn = document.getElementById('assistant-close-btn');
            this.clearBtn = document.getElementById('assistant-clear-btn');
            this.messagesContainer = document.getElementById('assistant-messages');
            this.chatForm = document.getElementById('assistant-form');
            this.chatInput = document.getElementById('assistant-input');
            this.sendBtn = document.getElementById('assistant-send-btn');
            this.typingIndicator = document.getElementById('assistant-typing');
            this.chipsContainer = document.getElementById('assistant-chips');

            this.storageKey = 'cartivo_assistant_session_id';
            this.sessionId = localStorage.getItem(this.storageKey) || null;
            this.isWaiting = false;

            this.init();
        }

        init() {
            if (!this.launcherBtn || !this.drawer) return;

            // Bind Launcher toggle
            this.launcherBtn.addEventListener('click', () => this.toggleDrawer());
            if (this.closeBtn) {
                this.closeBtn.addEventListener('click', () => this.closeDrawer());
            }

            // Bind Clear Chat
            if (this.clearBtn) {
                this.clearBtn.addEventListener('click', () => this.clearChat());
            }

            // Bind Form Submit
            if (this.chatForm) {
                this.chatForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleSendMessage();
                });
            }

            // Bind Quick Chips
            if (this.chipsContainer) {
                this.chipsContainer.querySelectorAll('.assistant-chip').forEach(chip => {
                    chip.addEventListener('click', () => {
                        const prompt = chip.getAttribute('data-prompt') || chip.textContent.trim();
                        this.chatInput.value = prompt;
                        this.handleSendMessage();
                    });
                });
            }

            // Global escape key listener
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && !this.drawer.classList.contains('hidden')) {
                    this.closeDrawer();
                }
            });
        }

        toggleDrawer() {
            const isHidden = this.drawer.classList.contains('hidden');
            if (isHidden) {
                this.openDrawer();
            } else {
                this.closeDrawer();
            }
        }

        openDrawer() {
            this.drawer.classList.remove('hidden');
            this.scrollToBottom();
            setTimeout(() => {
                if (this.chatInput) this.chatInput.focus();
            }, 100);
        }

        closeDrawer() {
            this.drawer.classList.add('hidden');
        }

        clearChat() {
            if (!confirm('Are you sure you want to clear your conversation history?')) return;
            localStorage.removeItem(this.storageKey);
            this.sessionId = null;
            
            // Keep initial greeting only
            const initialGreetings = this.messagesContainer.querySelectorAll('.assistant-msg-initial');
            this.messagesContainer.innerHTML = '';
            if (initialGreetings.length > 0) {
                initialGreetings.forEach(node => this.messagesContainer.appendChild(node));
            } else {
                this.appendMessage('assistant', "Hello! I am your Cartivo AI Assistant. How can I assist with your shopping today?");
            }
        }

        scrollToBottom() {
            if (this.messagesContainer) {
                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            }
        }

        appendMessage(sender, text) {
            const msgEl = document.createElement('div');
            msgEl.className = `assistant-msg ${sender}`;

            const bubbleEl = document.createElement('div');
            bubbleEl.className = 'assistant-bubble';
            
            // Render basic markdown formatting (bold, newlines)
            bubbleEl.innerHTML = this.formatMessageText(text);

            const timeEl = document.createElement('div');
            timeEl.className = 'assistant-msg-time';
            const now = new Date();
            timeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            msgEl.appendChild(bubbleEl);
            msgEl.appendChild(timeEl);

            this.messagesContainer.appendChild(msgEl);
            this.scrollToBottom();
        }

        formatMessageText(text) {
            if (!text) return '';
            const escaped = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // Bold **text**
            const formatted = escaped
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`([^`]+)`/g, '<code class="bg-slate-200 px-1 py-0.5 rounded text-xs">$1</code>')
                .replace(/\n/g, '<br>');
            return formatted;
        }

        showTyping() {
            if (this.typingIndicator) {
                this.typingIndicator.classList.remove('hidden');
                this.scrollToBottom();
            }
        }

        hideTyping() {
            if (this.typingIndicator) {
                this.typingIndicator.classList.add('hidden');
            }
        }

        extractBrowserContext() {
            const visibleProducts = [];
            document.querySelectorAll('.product-card').forEach(card => {
                const id = card.getAttribute('data-product-id');
                const title = card.getAttribute('data-product-title') || card.querySelector('h3, .font-semibold')?.textContent?.trim();
                const price = card.getAttribute('data-product-price') || card.querySelector('.font-bold, .text-slate-900')?.textContent?.trim();
                if (title) {
                    visibleProducts.push({
                        id: id ? parseInt(id, 10) : null,
                        title: title,
                        price: price || '0.00'
                    });
                }
            });

            const badge = document.querySelector('#cart-badge, .cart-badge-count');
            const cartCount = badge ? parseInt(badge.textContent.trim(), 10) || 0 : 0;

            return {
                url: window.location.pathname,
                page_title: document.title,
                cart_count: cartCount,
                visible_products: visibleProducts.slice(0, 10)
            };
        }

        async handleSendMessage() {
            if (this.isWaiting) return;
            const message = (this.chatInput.value || '').trim();
            if (!message) return;

            // Add user bubble
            this.appendMessage('user', message);
            this.chatInput.value = '';
            this.isWaiting = true;
            if (this.sendBtn) this.sendBtn.disabled = true;
            this.showTyping();
            const browserContext = this.extractBrowserContext();

            try {
                const response = await fetch('/api/assistant/message/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: this.sessionId,
                        browser_context: browserContext
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    const errorMsg = data.error || `Server responded with status ${response.status}.`;
                    this.appendMessage('assistant', `⚠️ ${errorMsg}`);
                    return;
                }

                // Update session ID if returned
                if (data.session_id) {
                    this.sessionId = data.session_id;
                    localStorage.setItem(this.storageKey, this.sessionId);
                }

                // Display assistant reply
                if (data.reply) {
                    this.appendMessage('assistant', data.reply);
                }

                // Dispatch UI actions
                if (Array.isArray(data.actions) && data.actions.length > 0) {
                    this.dispatchActions(data.actions);
                }

            } catch (err) {
                console.error('[Cartivo Assistant Error]:', err);
                this.appendMessage('assistant', 'Sorry, I ran into a connection error while processing your request. Please try again.');
            } finally {
                this.hideTyping();
                this.isWaiting = false;
                if (this.sendBtn) this.sendBtn.disabled = false;
            }
        }

        /**
         * Dispatches deterministic UI actions returned from tool execution
         */
        dispatchActions(actions) {
            actions.forEach(action => {
                if (!action || !action.type) return;

                console.log(`[Assistant Action] Dispatching: ${action.type}`, action.payload);

                switch (action.type) {
                    case 'compare_products':
                        this.actionCompareProducts(action.payload);
                        break;
                    case 'filter_products':
                        this.actionFilterProducts(action.payload);
                        break;
                    case 'update_cart_badge':
                        this.actionUpdateCartBadge(action.payload);
                        break;
                    case 'open_modal':
                        this.actionOpenModal(action.payload);
                        break;
                    case 'navigate_to':
                        this.actionNavigateTo(action.payload);
                        break;
                    case 'highlight_element':
                        this.actionHighlightElement(action.payload);
                        break;
                    default:
                        console.warn(`[Assistant Action] Unrecognized action type: ${action.type}`);
                }
            });
        }

        actionCompareProducts(payload) {
            const productIds = payload.product_ids || [];
            if (productIds.length > 0) {
                const cards = document.querySelectorAll('.product-card');
                cards.forEach(card => {
                    const cardId = parseInt(card.getAttribute('data-product-id'), 10);
                    if (productIds.includes(cardId)) {
                        card.style.opacity = '1';
                        card.classList.add('assistant-highlight-glow');
                        setTimeout(() => card.classList.remove('assistant-highlight-glow'), 6000);
                    } else {
                        card.style.opacity = '0.35';
                        setTimeout(() => card.style.opacity = '1', 6000);
                    }
                });

                const gridSection = document.querySelector('.product-card')?.closest('section') ||
                                    document.querySelector('.grid.grid-cols-2');
                if (gridSection) {
                    gridSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        }

        actionFilterProducts(payload) {
            const productIds = payload.product_ids || [];
            const cards = document.querySelectorAll('.product-card');

            if (cards.length > 0) {
                let matchedCount = 0;
                cards.forEach(card => {
                    const cardId = parseInt(card.getAttribute('data-product-id'), 10);
                    const cardTitle = (card.getAttribute('data-product-title') || '').toLowerCase();
                    const query = (payload.query || '').toLowerCase();

                    const isMatch = (productIds.length > 0 && productIds.includes(cardId)) ||
                                    (query && cardTitle.includes(query));

                    if (isMatch) {
                        card.style.opacity = '1';
                        card.classList.add('assistant-highlight-glow');
                        matchedCount++;
                        setTimeout(() => card.classList.remove('assistant-highlight-glow'), 4000);
                    } else if (productIds.length > 0) {
                        // Dim non-matching items slightly to focus attention
                        card.style.opacity = '0.4';
                        setTimeout(() => card.style.opacity = '1', 6000);
                    }
                });

                // Smooth scroll to product grid section
                const gridSection = document.querySelector('.product-card')?.closest('section') ||
                                    document.querySelector('.grid.grid-cols-2');
                if (gridSection) {
                    gridSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        }

        actionUpdateCartBadge(payload) {
            const count = payload.count !== undefined ? payload.count : null;
            if (count === null) return;

            const badgeElements = document.querySelectorAll('#cart-badge, .cart-badge-count');
            badgeElements.forEach(badge => {
                badge.textContent = String(count);
                badge.classList.remove('cart-badge-bounce');
                // Force reflow
                void badge.offsetWidth;
                badge.classList.add('cart-badge-bounce');
                setTimeout(() => badge.classList.remove('cart-badge-bounce'), 800);
            });
        }

        actionOpenModal(payload) {
            const modalId = payload.modal_id;
            if (!modalId) return;

            // Try existing global openModal helper if available
            if (typeof window.openModal === 'function') {
                window.openModal(modalId);
                return;
            }

            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('hidden');
                modal.classList.add('active');
            }
        }

        actionNavigateTo(payload) {
            const url = payload.url;
            if (!url) return;

            if (payload.new_tab) {
                window.open(url, '_blank');
            } else {
                window.location.href = url;
            }
        }

        actionHighlightElement(payload) {
            const selector = payload.selector;
            if (!selector) return;

            try {
                const element = document.querySelector(selector);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element.classList.add('assistant-highlight-glow');
                    setTimeout(() => element.classList.remove('assistant-highlight-glow'), 3500);
                }
            } catch (e) {
                console.warn(`[Assistant Action] Invalid selector: ${selector}`, e);
            }
        }
    }

    // Initialize when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.cartivoAssistant = new AssistantWidget();
        });
    } else {
        window.cartivoAssistant = new AssistantWidget();
    }
})();
