// simple tab behaviour (works together with the DOMContentLoaded handler)
(function () {
    function selectTab(name) {
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        document.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.remove('text-primary', 'border-b-2', 'border-primary');
            b.classList.add('text-gray-500');
        });
        const el = document.getElementById(name);
        if (el) el.classList.remove('hidden');
        const btn = document.querySelector('.tab-btn[data-tab="'+name+'"]');
        if (btn) {
            btn.classList.add('text-primary', 'border-b-2', 'border-primary');
            btn.classList.remove('text-gray-500');
        }
    }
    // default tab
    window.selectTab = selectTab;
    document.addEventListener('click', (e) => {
        const tb = e.target.closest('.tab-btn');
        if (tb && tb.dataset.tab) {
            e.preventDefault();
            selectTab(tb.dataset.tab);
        }
    });
    // show patient-management by default on load
    document.addEventListener('DOMContentLoaded', () => selectTab('patient-management'));
})();

document.addEventListener('DOMContentLoaded', () => {
    const openSidebarButton = document.getElementById('open-sidebar');
    const closeSidebarButton = document.getElementById('close-sidebar');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');

    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
    }

    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    }

    openSidebarButton?.addEventListener('click', openSidebar);
    closeSidebarButton?.addEventListener('click', closeSidebar);
    overlay?.addEventListener('click', closeSidebar);

    // Optional: Close sidebar when clicking outside on mobile
    document.getElementById('app')?.addEventListener('click', (e) => {
        if (window.innerWidth < 768 && !sidebar.contains(e.target) && !openSidebarButton.contains(e.target)) {
            closeSidebar();
        }
    });

    const dashboardData = {
        patients: {
            antenatal: 42,
            malaria: 58,
            immunization: 33,
            other: 19
        },
        stock: [{
            name: "Paracetamol 500mg",
            qty: 220
        }, {
            name: "RDT Kits",
            qty: 35
        }, {
            name: "Amoxicillin",
            qty: 0
        }]
    };

    const visitCards = document.getElementById("visit-cards");
    if (visitCards) {
        visitCards.innerHTML = Object.entries(dashboardData.patients)
            .map(([k, v]) => `
                <div class="bg-teal-500 p-4 rounded-lg text-white">
                    <p class="text-sm capitalize">${k}</p>
                    <p class="text-3xl font-bold">${v}</p>
                </div>
            `).join("");
    }

    const stockTable = document.getElementById("stock-table");
    if (stockTable) {
        stockTable.innerHTML = dashboardData.stock.map(item =>
            `<tr><td class="py-2">${item.name}</td><td>${item.qty}</td><td></td></tr>`
        ).join("");
    }

    // API base
    const API_BASE = 'http://localhost:8000';

    async function registerPatient(payload) {
        const res = await fetch(`${API_BASE}/patients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const txt = await res.text();
            throw new Error('Registration failed: ' + res.status + ' ' + txt);
        }
        return res.json();
    }

    async function callTriage(patientId) {
        const res = await fetch(`${API_BASE}/patients/triage/${patientId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (!res.ok) {
            const txt = await res.text();
            throw new Error('Triage failed: ' + res.status + ' ' + txt);
        }
        return res.json();
    }

    // --- Helpers for registration / form ---
    function parseList(text) {
        if (!text) return [];
        return text.split(/[
,]+/).map(s => s.trim()).filter(Boolean);
    }

    function clearForm() {
        const ids = ['patient-name','patient-age','patient-sex','patient-visit','patient-symptoms','patient-vitals','patient-medical-history'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            if (el.tagName === 'SELECT') el.selectedIndex = 0;
            else el.value = '';
        });
        const triage = document.getElementById('triage-result');
        if (triage) triage.classList.add('hidden');
    }

    function showSuccessOverlay(patientId) {
        const overlay = document.getElementById('success-overlay');
        if (!overlay) return;
        const idEl = overlay.querySelector('#success-overlay-id');
        if (idEl) idEl.textContent = patientId ?? 'unknown';
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
        // auto-hide after 3s
        clearTimeout(window._successOverlayTimeout);
        window._successOverlayTimeout = setTimeout(() => {
            overlay.classList.add('hidden');
            overlay.classList.remove('flex');
        }, 3000);
    }

    // --- Start triage (register patient) handler ---
    async function onStartTriageClick(e) {
        console.log('onStartTriageClick fired');
        e?.preventDefault();
        try {
            const name = (document.getElementById('patient-name') || {}).value?.trim() || 'Anonymous';
            const age = parseInt((document.getElementById('patient-age') || {}).value, 10) || 0;
            const sex = (document.getElementById('patient-sex') || {}).value || 'Male';
            const visit_type = (document.getElementById('patient-visit') || {}).value || 'Routine';
            const symptoms = parseList((document.getElementById('patient-symptoms') || {}).value || '');
            const vitals = (document.getElementById('patient-vitals') || {}).value || '';
            const medical_history = parseList((document.getElementById('patient-medical-history') || {}).value || '');

            if (!name) throw new Error('Name required');
            if (age < 0) throw new Error('Age cannot be negative');

            const payload = { name, age, sex, symptoms, visit_type, vitals, medical_history };
            console.log('register payload', payload);

            const patient = await registerPatient(payload);
            console.log('Registered patient', patient);
            showSuccessOverlay(patient.id);
            clearForm();
        } catch (err) {
            console.error(err);
            alert(err.message || 'Error');
        }
    }

    // Chat helpers for triage assistant
    function appendChatMessage(who, text) {
        const container = document.getElementById('triage-chat');
        if (!container) return;
        const wrap = document.createElement('div');
        wrap.className = who === 'user' ? 'flex justify-end' : 'flex justify-start';
        const bubble = document.createElement('div');
        bubble.className = who === 'user'
            ? 'max-w-[75%] bg-primary text-white px-3 py-2 rounded-lg rounded-br-none whitespace-pre-wrap'
            : 'max-w-[75%] bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg rounded-bl-none whitespace-pre-wrap';
        bubble.textContent = text;
        wrap.appendChild(bubble);
        container.appendChild(wrap);
        container.scrollTop = container.scrollHeight;
    }

    function clearChat() {
        const container = document.getElementById('triage-chat');
        if (container) container.innerHTML = '';
    }

    // wire triage chat send
    document.getElementById('triage-send')?.addEventListener('click', async () => {
        const input = document.getElementById('triage-input');
        if (!input) return;
        const raw = input.value.trim();
        if (!raw) return alert('Enter patient ID');
        const patientId = isNaN(Number(raw)) ? raw : Number(raw);

        // show as user message
        appendChatMessage('user', `Triage request for patient ID: ${patientId}`);

        // show loading
        const sendBtn = document.getElementById('triage-send');
        const loading = document.getElementById('triage-loading');
        sendBtn.disabled = true;
        if (loading) loading.classList.remove('hidden');

        try {
            const res = await callTriage(patientId);
            // format assistant response
            const actions = (res.recommended_actions || []).join(', ');
            const assistantText = `Urgency: ${res.urgency_level}
Actions: ${actions}
Reasoning: ${res.reasoning}`;
            appendChatMessage('assistant', assistantText);
        } catch (err) {
            console.error(err);
            appendChatMessage('assistant', 'Error: ' + (err.message || 'Request failed'));
        } finally {
            sendBtn.disabled = false;
            if (loading) loading.classList.add('hidden');
        }
    });

    // allow Enter to send
    document.getElementById('triage-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('triage-send')?.click();
        }
    });

    document.getElementById('triage-clear')?.addEventListener('click', () => clearChat());

    document.getElementById('start-triage')?.addEventListener('click', onStartTriageClick);

    // --- Inventory Management ---
    const inventoryState = {
        stock: [
            { id: 1, name: "Paracetamol", type: "Drug", current_stock: 45, daily_usage: 10, unit: "Tablets" },
            { id: 2, name: "Gloves", type: "Supply", current_stock: 150, daily_usage: 20, unit: "Pairs" },
            { id: 3, name: "Syringes", type: "Supply", current_stock: 200, daily_usage: 15, unit: "Units" },
            { id: 4, name: "Amoxicillin", type: "Drug", current_stock: 120, daily_usage: 10, unit: "Capsules" }
        ],
        requests: [
            { request_id: 101, item_name: "Paracetamol", quantity: 500, phc_name: "PHC Ajah", request_date: "2025-10-11", status: "Pending", comments: "-" },
            { request_id: 102, item_name: "Syringe", quantity: 200, phc_name: "PHC Lekki", request_date: "2025-10-10", status: "Approved", comments: "Delivered" }
        ]
    };

    function showToast(id) {
        const toast = document.getElementById(id);
        if (!toast) return;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    }

    function openModal(id) { document.getElementById(id)?.classList.remove('hidden'); }
    function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }

    function renderLowStockTable() {
        const tableBody = document.getElementById('low-stock-table-body');
        if (!tableBody) return;
        tableBody.innerHTML = '';
        inventoryState.stock.forEach(item => {
            const daysRemaining = item.daily_usage > 0 ? Math.floor(item.current_stock / item.daily_usage) : Infinity;
            let colorClass = 'text-green-700 bg-green-100 dark:text-green-100 dark:bg-green-700';
            if (daysRemaining <= 5) colorClass = 'text-red-700 bg-red-100 dark:text-red-100 dark:bg-red-700';
            else if (daysRemaining <= 10) colorClass = 'text-yellow-700 bg-yellow-100 dark:text-yellow-100 dark:bg-yellow-700';

            const row = document.createElement('tr');
            row.className = 'border-b border-border-light dark:border-border-dark';
            row.innerHTML = `
                <td class="px-4 py-3">${item.name}</td>
                <td class="px-4 py-3">${item.type}</td>
                <td class="px-4 py-3">${item.current_stock}</td>
                <td class="px-4 py-3">${item.daily_usage}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 font-semibold leading-tight rounded-full ${colorClass}">${isFinite(daysRemaining) ? daysRemaining + ' days' : 'N/A'}</span></td>
                <td class="px-4 py-3">${item.unit}</td>
                <td class="px-4 py-3"><button data-item-id="${item.id}" data-item-name="${item.name}" class="text-primary hover:underline open-request-restock-modal-btn">➕ Request Restock</button></td>
            `;
            tableBody.appendChild(row);
        });
    }

    function renderRestockRequestsTable() {
        const tableBody = document.getElementById('restock-requests-table-body');
        if (!tableBody) return;
        tableBody.innerHTML = '';
        inventoryState.requests.forEach(req => {
            let statusClass = '';
            switch (req.status) {
                case 'Pending': statusClass = 'text-yellow-700 bg-yellow-100 dark:text-yellow-100 dark:bg-yellow-700'; break;
                case 'Approved': statusClass = 'text-green-700 bg-green-100 dark:text-green-100 dark:bg-green-700'; break;
                case 'Declined': statusClass = 'text-red-700 bg-red-100 dark:text-red-100 dark:bg-red-700'; break;
            }
            const row = document.createElement('tr');
            row.className = 'border-b border-border-light dark:border-border-dark';
            row.innerHTML = `
                <td class="px-4 py-3">${req.request_id}</td>
                <td class="px-4 py-3">${req.item_name}</td>
                <td class="px-4 py-3">${req.quantity}</td>
                <td class="px-4 py-3">${req.phc_name}</td>
                <td class="px-4 py-3">${req.request_date}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 font-semibold leading-tight rounded-full ${statusClass}">${req.status}</span></td>
                <td class="px-4 py-3">${req.comments}</td>
                <td class="px-4 py-3">${req.status === 'Pending' ? `<button data-request-id="${req.request_id}" class="text-primary hover:underline open-update-status-modal-btn">✅ Approve / ❌ Decline</button>` : '—'}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    function renderUpdateStockTable() {
        const tableBody = document.getElementById('update-stock-table-body');
        if (!tableBody) return;
        tableBody.innerHTML = '';
        inventoryState.stock.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${item.name}</td>
                <td class="px-4 py-2"><input type="number" data-item-id="${item.id}" class="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700" value="0" min="0"></td>
            `;
            tableBody.appendChild(row);
        });
    }

    function updateSummaryCards() {
        document.getElementById('summary-total-stock').textContent = inventoryState.stock.reduce((acc, item) => acc + item.current_stock, 0);
        document.getElementById('summary-low-stock').textContent = inventoryState.stock.filter(item => item.daily_usage > 0 && (item.current_stock / item.daily_usage) <= 5).length;
        document.getElementById('summary-pending-requests').textContent = inventoryState.requests.filter(req => req.status === 'Pending').length;
        document.getElementById('summary-approved-requests').textContent = inventoryState.requests.filter(req => req.status === 'Approved').length;
    }

    // Event Listeners
    document.querySelectorAll('.inventory-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            document.querySelectorAll('.inventory-tab-content').forEach(c => c.classList.add('hidden'));
            document.getElementById(tabId).classList.remove('hidden');
            document.querySelectorAll('.inventory-tab-btn').forEach(b => {
                b.classList.remove('text-primary', 'border-primary');
                b.classList.add('text-gray-500', 'border-transparent');
            });
            btn.classList.add('text-primary', 'border-primary');
            btn.classList.remove('text-gray-500', 'border-transparent');
        });
    });

    document.getElementById('open-update-stock-modal-btn')?.addEventListener('click', () => { renderUpdateStockTable(); openModal('update-stock-modal'); });
    document.getElementById('cancel-update-stock-btn')?.addEventListener('click', () => closeModal('update-stock-modal'));
    document.getElementById('cancel-restock-btn')?.addEventListener('click', () => closeModal('request-restock-modal'));
    document.getElementById('cancel-update-status-btn')?.addEventListener('click', () => closeModal('update-status-modal'));

    document.addEventListener('click', (e) => {
        if (e.target.matches('.open-request-restock-modal-btn')) {
            document.getElementById('restock-item-id').value = e.target.dataset.itemId;
            document.getElementById('restock-item-name').value = e.target.dataset.itemName;
            openModal('request-restock-modal');
        }
        if (e.target.matches('.open-update-status-modal-btn')) {
            document.getElementById('update-request-id').value = e.target.dataset.requestId;
            openModal('update-status-modal');
        }
    });
    
    // Form Submissions (with dummy API calls)
    document.getElementById('update-stock-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        console.log('POST /inventory/update-stock');
        closeModal('update-stock-modal');
        showToast('toast-stock-updated');
    });

    document.getElementById('request-restock-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        console.log('POST /inventory/restock-requests');
        closeModal('request-restock-modal');
        showToast('toast-restock-sent');
    });

    document.getElementById('update-status-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        const requestId = document.getElementById('update-request-id').value;
        console.log(`PUT /inventory/restock-requests/${requestId}`);
        closeModal('update-status-modal');
        showToast('toast-stock-updated');
    });

    document.getElementById('auto-restock-check-btn')?.addEventListener('click', () => console.log('POST /inventory/auto-restock-check'));
    document.getElementById('check-low-stock-btn')?.addEventListener('click', () => console.log('GET /inventory/low-stock?threshold_days=5'));

    // Initial Render
    renderLowStockTable();
    renderRestockRequestsTable();
    updateSummaryCards();

    function showToast(id) {
        const toast = document.getElementById(id);
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }

    document.querySelector('#request-restock-modal button[type="submit"]').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('request-restock-modal').classList.add('hidden');
        showToast('toast-restock-sent');
    });

    document.querySelector('#update-stock-modal button[type="submit"]').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('update-stock-modal').classList.add('hidden');
        showToast('toast-stock-updated');
    });

     document.getElementById('open-register')?.addEventListener('click', () => {
         // open your registration panel/modal (implement UI action)
         alert('Open registration UI (implement)');
     });
 });