// ============================================================================
// MEZZARPG — Main JavaScript
// Alpine.js components + WebSocket client + HTMX helpers
// ============================================================================

// --- Global Alpine Data ---
document.addEventListener('alpine:init', () => {
  
  // Toast notifications
  Alpine.data('toast', () => ({
    toasts: [],
    
    show(message, type = 'info', duration = 5000) {
      const id = Date.now();
      this.toasts.push({ id, message, type });
      if (duration > 0) {
        setTimeout(() => this.dismiss(id), duration);
      }
      return id;
    },
    
    dismiss(id) {
      this.toasts = this.toasts.filter(t => t.id !== id);
    },
    
    success(msg, dur) { return this.show(msg, 'success', dur); },
    error(msg, dur) { return this.show(msg, 'error', dur); },
    warning(msg, dur) { return this.show(msg, 'warning', dur); },
    info(msg, dur) { return this.show(msg, 'info', dur); },
  }));
  
  // Modal manager
  Alpine.data('modal', () => ({
    modals: {},
    
    open(name, data = {}) {
      this.modals[name] = { open: true, data };
      document.body.style.overflow = 'hidden';
    },
    
    close(name) {
      this.modals[name] = { open: false, data: {} };
      if (Object.values(this.modals).every(m => !m.open)) {
        document.body.style.overflow = '';
      }
    },
    
    toggle(name, data) {
      if (this.modals[name]?.open) this.close(name);
      else this.open(name, data);
    },
    
    isOpen(name) {
      return this.modals[name]?.open === true;
    },
  }));
  
  // Dice roller component
  Alpine.data('diceRoller', () => ({
    rolling: false,
    lastRoll: null,
    history: [],
    
    async roll(sides, count = 1, modifier = 0) {
      this.rolling = true;
      
      // Simulate roll animation
      await new Promise(r => setTimeout(r, 300 + Math.random() * 200));
      
      const rolls = Array.from({ length: count }, () => Math.floor(Math.random() * sides) + 1);
      const total = rolls.reduce((a, b) => a + b, 0) + modifier;
      
      this.lastRoll = { sides, count, modifier, rolls, total };
      this.history.unshift({ ...this.lastRoll, timestamp: Date.now() });
      if (this.history.length > 20) this.history.pop();
      
      this.rolling = false;
      return this.lastRoll;
    },
    
    rollD20(advantage = false, disadvantage = false) {
      const roll1 = Math.floor(Math.random() * 20) + 1;
      const roll2 = Math.floor(Math.random() * 20) + 1;
      
      let result, rolls;
      if (advantage && !disadvantage) {
        result = Math.max(roll1, roll2);
        rolls = [roll1, roll2];
      } else if (disadvantage && !advantage) {
        result = Math.min(roll1, roll2);
        rolls = [roll1, roll2];
      } else {
        result = roll1;
        rolls = [roll1];
      }
      
      return { result, rolls, isCrit: result === 20, isFumble: result === 1 };
    },
    
    roll4d6DropLowest() {
      const dice = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1);
      dice.sort((a, b) => a - b);
      return {
        dice,
        dropped: dice[0],
        kept: dice.slice(1),
        total: dice.slice(1).reduce((a, b) => a + b, 0)
      };
    },
    
    formatRoll(roll) {
      if (!roll) return '—';
      const modStr = roll.modifier !== 0 ? ` ${roll.modifier >= 0 ? '+' : ''}${roll.modifier}` : '';
      return `${roll.rolls.join(', ')}${modStr} = <strong>${roll.total}</strong>`;
    },
  }));
  
  // Character sheet helper
  Alpine.data('characterSheet', () => ({
    calculateMod(score) {
      return Math.floor((score - 10) / 2);
    },
    
    formatMod(score) {
      const mod = this.calculateMod(score);
      return mod >= 0 ? `+${mod}` : `${mod}`;
    },
    
    calculateHP(level, conMod, hitDie) {
      // Level 1: max hit die + con
      // Subsequent: average (half + 1) + con per level
      if (level <= 1) return hitDie + conMod;
      const avg = Math.floor(hitDie / 2) + 1;
      return hitDie + conMod + (avg + conMod) * (level - 1);
    },
    
    calculateProficiency(level) {
      return Math.ceil((1 + level) / 4) + 1; // 2 at level 1, 3 at 5, 4 at 9, 5 at 13, 6 at 17
    },
    
    getSaveDC(level, primaryStat) {
      return 8 + this.calculateProficiency(level) + this.calculateMod(primaryStat);
    },
  }));
  
  // Inventory manager
  Alpine.data('inventory', () => ({
    items: [],
    capacity: 100, // weight limit
    currency: { pp: 0, gp: 0, ep: 0, sp: 0, cp: 0 },
    
    addItem(item, quantity = 1) {
      const existing = this.items.find(i => i.name === item.name);
      if (existing) {
        existing.quantity += quantity;
      } else {
        this.items.push({ ...item, quantity });
      }
      this.sortItems();
    },
    
    removeItem(name, quantity = 1) {
      const idx = this.items.findIndex(i => i.name === name);
      if (idx === -1) return false;
      
      this.items[idx].quantity -= quantity;
      if (this.items[idx].quantity <= 0) {
        this.items.splice(idx, 1);
      }
      return true;
    },
    
    sortItems() {
      // Sort by type then name
      const typeOrder = { weapon: 0, armor: 1, potion: 2, scroll: 3, tool: 4, ammo: 5, gem: 6, other: 7 };
      this.items.sort((a, b) => {
        const ta = typeOrder[a.type] ?? 7;
        const tb = typeOrder[b.type] ?? 7;
        if (ta !== tb) return ta - tb;
        return a.name.localeCompare(b.name);
      });
    },
    
    getTotalWeight() {
      return this.items.reduce((sum, item) => sum + (item.weight || 0) * item.quantity, 0);
    },
    
    isEncumbered() {
      return this.getTotalWeight() > this.capacity;
    },
    
    formatCurrency() {
      const { pp, gp, ep, sp, cp } = this.currency;
      const parts = [];
      if (pp) parts.push(`${pp} PP`);
      if (gp) parts.push(`${gp} PO`);
      if (ep) parts.push(`${ep} PE`);
      if (sp) parts.push(`${sp} PP`);
      if (cp) parts.push(`${cp} PC`);
      return parts.join(', ') || '—';
    },
  }));
  
  // Combat tracker
  Alpine.data('combatTracker', () => ({
    combatants: [],
    round: 1,
    currentTurn: 0,
    active: false,
    
    addCombatant(data) {
      this.combatants.push({
        ...data,
        id: data.id || `combatant_${Date.now()}`,
        hp: data.hp || data.hp_max,
        conditions: [],
        concentration: false,
        hasActed: false,
        hasBonusAction: false,
        hasReaction: true,
      });
      this.sortInitiative();
    },
    
    sortInitiative() {
      this.combatants.sort((a, b) => b.initiative - a.initiative);
    },
    
    nextTurn() {
      if (this.combatants.length === 0) return;
      
      this.combatants[this.currentTurn].hasActed = false;
      this.combatants[this.currentTurn].hasBonusAction = false;
      this.combatants[this.currentTurn].hasReaction = true;
      
      this.currentTurn = (this.currentTurn + 1) % this.combatants.length;
      
      if (this.currentTurn === 0) {
        this.round++;
        this.combatants.forEach(c => {
          // End of round effects
          c.conditions = c.conditions.filter(cond => !cond.endsWith('_1round'));
        });
      }
      
      this.combatants[this.currentTurn].hasActed = true;
    },
    
    getCurrent() {
      return this.combatants[this.currentTurn] || null;
    },
    
    damage(id, amount, type = 'physical') {
      const c = this.combatants.find(c => c.id === id);
      if (!c) return;
      
      let finalDamage = amount;
      if (type !== 'physical') {
        if (c.vulnerabilities?.includes(type)) finalDamage *= 2;
        if (c.resistances?.includes(type)) finalDamage = Math.floor(finalDamage / 2);
        if (c.immunities?.includes(type)) finalDamage = 0;
      }
      
      c.hp = Math.max(0, c.hp - finalDamage);
      if (c.hp <= 0 && !c.conditions.includes('unconscious')) {
        c.conditions.push('unconscious');
      }
      return finalDamage;
    },
    
    heal(id, amount) {
      const c = this.combatants.find(c => c.id === id);
      if (!c) return;
      c.hp = Math.min(c.hp_max, c.hp + amount);
      if (c.hp > 0) {
        c.conditions = c.conditions.filter(cond => cond !== 'unconscious');
      }
    },
    
    addCondition(id, condition) {
      const c = this.combatants.find(c => c.id === id);
      if (c && !c.conditions.includes(condition)) {
        c.conditions.push(condition);
      }
    },
    
    removeCondition(id, condition) {
      const c = this.combatants.find(c => c.id === id);
      if (c) {
        c.conditions = c.conditions.filter(cond => cond !== condition);
      }
    },
  }));
  
});

// --- WebSocket Helper ---
class MesanerdWS {
  constructor(partyId, handlers = {}) {
    this.partyId = partyId;
    this.handlers = {
      onMessage: handlers.onMessage || (() => {}),
      onOpen: handlers.onOpen || (() => {}),
      onClose: handlers.onClose || (() => {}),
      onError: handlers.onError || (console.error),
    };
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
  }
  
  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/${this.partyId}`;
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = (event) => {
      this.reconnectAttempts = 0;
      this.handlers.onOpen(event);
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.onMessage(data);
      } catch (e) {
        console.error('WS parse error:', e, event.data);
      }
    };
    
    this.ws.onclose = (event) => {
      this.handlers.onClose(event);
      this.scheduleReconnect();
    };
    
    this.ws.onerror = (event) => {
      this.handlers.onError(event);
    };
  }
  
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }
    
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts);
    this.reconnectAttempts++;
    
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect();
    }, delay);
  }
  
  send(type, data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ tipo: type, dados: data }));
    } else {
      console.warn('WS not connected, queuing message');
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Make globally available
window.MesanerdWS = MesanerdWS;

// --- HTMX Helpers ---
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

document.addEventListener('htmx:configRequest', (evt) => {
  // Attach CSRF token to all HTMX state-changing requests
  const csrf = getCsrfToken();
  if (csrf) {
    evt.detail.headers['X-CSRF-Token'] = csrf;
  }
});

document.addEventListener('htmx:beforeSwap', (evt) => {
  // Allow custom swap logic
  if (evt.detail.xhr.status === 401) {
    // Redirect to login on unauthorized
    window.location.href = '/auth/login';
    evt.detail.shouldSwap = false;
  }
});

document.addEventListener('htmx:afterSwap', (evt) => {
  // Re-initialize Alpine components in swapped content
  if (window.Alpine) {
    window.Alpine.initTree(evt.detail.target);
  }
});

// --- Utility Functions ---
window.MesanerdUtils = {
  // Format number with sign
  formatMod: (val) => {
    const mod = Math.floor((val - 10) / 2);
    return mod >= 0 ? `+${mod}` : `${mod}`;
  },
  
  // Roll dice notation (e.g., "2d6+3")
  rollDice: (notation) => {
    const match = notation.match(/^(\d*)d(\d+)([+-]\d+)?$/i);
    if (!match) return { total: 0, rolls: [], error: 'Invalid notation' };
    
    const count = parseInt(match[1]) || 1;
    const sides = parseInt(match[2]);
    const mod = parseInt(match[3]) || 0;
    
    const rolls = Array.from({ length: count }, () => Math.floor(Math.random() * sides) + 1);
    const total = rolls.reduce((a, b) => a + b, 0) + mod;
    
    return { total, rolls, modifier: mod };
  },
  
  // Calculate distance between two grid positions
  gridDistance: (x1, y1, x2, y2, diagonal = true) => {
    const dx = Math.abs(x2 - x1);
    const dy = Math.abs(y2 - y1);
    if (diagonal) return Math.max(dx, dy);
    return dx + dy;
  },
  
  // Format HP bar color
  hpColor: (current, max) => {
    const pct = (current / max) * 100;
    if (pct <= 0) return 'var(--blood)';
    if (pct <= 25) return 'var(--blood)';
    if (pct <= 50) return '#F57C00';
    return 'var(--success)';
  },
  
  // Debounce
  debounce: (fn, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn(...args), delay);
    };
  },
  
  // Throttle
  throttle: (fn, limit) => {
    let inThrottle;
    return (...args) => {
      if (!inThrottle) {
        fn(...args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },
  
  // Copy to clipboard
  copyToClipboard: async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      console.error('Copy failed:', e);
      return false;
    }
  },
  
  // Generate UUID
  uuid: () => crypto.randomUUID?.() || 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  }),
};

// --- Keyboard Shortcuts ---
document.addEventListener('keydown', (e) => {
  // Global shortcuts (when not in input)
  const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
  if (isInput) return;
  
  // Ctrl/Cmd + K for command palette (future)
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    // Open command palette
  }
  
  // Escape to close modals
  if (e.key === 'Escape') {
    document.querySelectorAll('[x-show]').forEach(el => {
      if (el._x_dataStack?.[0]?.close) {
        el._x_dataStack[0].close();
      }
    });
  }
});

// --- Initialize on DOM Ready ---
document.addEventListener('DOMContentLoaded', () => {
  // Add fade-in animation to main content
  const main = document.querySelector('main.main-content');
  if (main) {
    main.style.opacity = '0';
    main.style.transform = 'translateY(10px)';
    requestAnimationFrame(() => {
      main.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      main.style.opacity = '1';
      main.style.transform = 'translateY(0)';
    });
  }
  
  // Initialize tooltips (future)
  // Initialize dice roller on elements with data-dice
  document.querySelectorAll('[data-dice]').forEach(el => {
    el.addEventListener('click', () => {
      const notation = el.dataset.dice;
      const result = window.MesanerdUtils.rollDice(notation);
      el.title = `Rolled: ${result.rolls.join(', ')} = ${result.total}`;
    });
  });
});

console.log('🎲 Mesanerd Web JS loaded');