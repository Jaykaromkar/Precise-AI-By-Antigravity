const API_BASE = '/api';

const userId = localStorage.getItem('user_id');
if (!userId) {
    window.location.href = '/';
}

// State
let currentSessionId = null;
let isStreaming = false;
let messageHistory = [];
let chartInstances = {};

// DOM Elements
const sessionList = document.getElementById('sessionList');
const newChatBtn = document.getElementById('newChatBtn');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const currentSessionTitle = document.getElementById('currentSessionTitle');
const emptyState = document.getElementById('emptyState');

// Knowledge Base Drawer Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const attachBtn = document.getElementById('attachBtn');
const uploadStatus = document.getElementById('uploadStatus');
const uploadFilename = document.getElementById('uploadFilename');
const uploadProgressBar = document.getElementById('uploadProgressBar');
const uploadProgressText = document.getElementById('uploadProgressText');
const uploadStatusMessage = document.getElementById('uploadStatusMessage');
const documentList = document.getElementById('documentList');

// Initialize Icons
lucide.createIcons();

// Configure Marked.js with syntax highlighting
marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true
});

// Auto-resize textarea
messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Initial Load
async function init() {
    await fetchSessions();
    if (!currentSessionId) {
        await createNewSession();
    }
    
    // Fetch and display active AI Provider
    try {
        const res = await fetch(`${API_BASE}/chat/provider`);
        if(res.ok) {
            const data = await res.json();
            const badge = document.getElementById('providerName');
            if (badge) badge.textContent = `${data.provider}`;
            // Optional: You can also show the model if requested
            // if (badge) badge.textContent = `${data.provider} (${data.model})`;
        }
    } catch(e) {
        console.error("Failed to load provider config", e);
    }
}

// Session Management
async function fetchSessions() {
    try {
        const res = await fetch(`${API_BASE}/chat/sessions/${userId}`);
        const sessions = await res.json();

        sessionList.innerHTML = '';
        if (sessions.length > 0) {
            sessions.forEach(session => {
                const wrapper = document.createElement('div');
                wrapper.className = `w-full flex items-center justify-between px-3 py-2 rounded-lg mb-1 transition-colors group cursor-pointer ${session.id === currentSessionId ? 'bg-gray-700/60 text-white font-medium' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`;

                const titleBtn = document.createElement('button');
                titleBtn.className = 'flex-1 flex items-center gap-2 text-left truncate text-sm outline-none';
                titleBtn.innerHTML = `<i data-lucide="message-square" class="w-4 h-4 shrink-0"></i> <span class="truncate">${session.title}</span>`;
                titleBtn.onclick = () => loadSession(session.id, session.title);

                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0';

                const editBtn = document.createElement('button');
                editBtn.className = 'p-1 hover:text-blue-400 text-gray-500 transition-colors tooltip';
                editBtn.innerHTML = '<i data-lucide="edit-2" class="w-3.5 h-3.5"></i>';
                editBtn.onclick = (e) => window.renameSession(e, session.id, session.title);

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'p-1 hover:text-red-400 text-gray-500 transition-colors';
                deleteBtn.innerHTML = '<i data-lucide="trash-2" class="w-3.5 h-3.5"></i>';
                deleteBtn.onclick = (e) => window.deleteSession(e, session.id);

                actionsDiv.appendChild(editBtn);
                actionsDiv.appendChild(deleteBtn);
                wrapper.appendChild(titleBtn);
                wrapper.appendChild(actionsDiv);

                sessionList.appendChild(wrapper);
            });
            lucide.createIcons();

            // Set current if none
            if (!currentSessionId) {
                currentSessionId = sessions[0].id;
                currentSessionTitle.textContent = sessions[0].title;
                loadSession(currentSessionId, sessions[0].title);
            }
        }
    } catch (e) {
        console.error("Failed to fetch sessions", e);
    }
}

function resetKnowledgeBaseUI() {
    const auditContent = document.getElementById('auditContent');
    if (auditContent) auditContent.innerHTML = '';
    
    const vizContainer = document.getElementById('vizContainer');
    if (vizContainer) vizContainer.innerHTML = '';
    
    const vizEmptyState = document.getElementById('vizEmptyState');
    if (vizEmptyState) {
        vizEmptyState.classList.remove('hidden');
        vizEmptyState.innerHTML = '<i data-lucide="pie-chart" class="w-12 h-12 text-gray-500 mx-auto mb-3"></i><p class="text-sm">Upload a ledger to generate interactive Chart.js modules automatically.</p>';
    }
    
    const docPreviewFrame = document.getElementById('docPreviewFrame');
    if (docPreviewFrame) {
        docPreviewFrame.src = '';
        docPreviewFrame.classList.add('hidden');
    }
    
    const previewEmptyState = document.getElementById('previewEmptyState');
    if (previewEmptyState) previewEmptyState.classList.remove('hidden');
    
    const drawer = document.getElementById('documentDrawer');
    if (drawer) {
        drawer.classList.remove('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
        drawer.classList.add('w-0');
    }
    
    if (typeof activeChartInstances !== 'undefined') {
        activeChartInstances.forEach(c => c.destroy());
        activeChartInstances = [];
    }
    
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function createNewSession() {
    try {
        const res = await fetch(`${API_BASE}/chat/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: parseInt(userId) })
        });
        const session = await res.json();
        currentSessionId = session.id;
        currentSessionTitle.textContent = session.title;
        chatMessages.innerHTML = '';
        chatMessages.appendChild(emptyState);
        emptyState.style.display = 'flex';
        resetKnowledgeBaseUI();
        await fetchSessions();
        await loadDocuments();
    } catch (e) {
        console.error("Failed to create session", e);
    }
}

window.renameSession = async function (e, id, currentTitle) {
    e.stopPropagation();
    const newTitle = prompt("Enter new name for this session:", currentTitle);
    if (!newTitle || newTitle === currentTitle) return;
    try {
        await fetch(`${API_BASE}/chat/sessions/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        if (id === currentSessionId) {
            currentSessionTitle.textContent = newTitle;
        }
        await fetchSessions();
    } catch (err) {
        console.error("Rename failed", err);
    }
};

window.deleteSession = async function (e, id) {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this session and all its data?")) return;
    try {
        await fetch(`${API_BASE}/chat/sessions/${id}`, { method: 'DELETE' });
        if (id === currentSessionId) {
            currentSessionId = null;
            await init();
        } else {
            await fetchSessions();
        }
    } catch (err) {
        console.error("Delete failed", err);
    }
};

async function loadSession(id, title) {
    currentSessionId = id;
    currentSessionTitle.textContent = title;
    resetKnowledgeBaseUI();
    await fetchSessions(); // To update active state in UI
    await loadDocuments(); // Load KB documents explicitly mapping to this session

    // Fetch History
    try {
        const res = await fetch(`${API_BASE}/chat/history/${id}`);
        const history = await res.json();

        chatMessages.innerHTML = '';

        if (history.length === 0) {
            chatMessages.appendChild(emptyState);
            emptyState.style.display = 'flex';
        } else {
            emptyState.style.display = 'none';
            history.forEach(msg => {
                renderMessage(msg.role, msg.content, false);
            });
            scrollToBottom();
        }
    } catch (e) {
        console.error("Failed to load history", e);
    }
}

// Chat UI Rendering
function renderMessage(role, content, isStreamingNode = false) {
    emptyState.style.display = 'none';
    const msgDiv = document.createElement('div');
    msgDiv.className = `flex gap-4 max-w-4xl mx-auto w-full group ${role === 'user' ? 'justify-end' : ''}`;

    let chartData = null;
    let mainContent = content;

    // Check if it's a finished bot message containing JSON chart data
    if (role === 'assistant' && !isStreamingNode && content.includes('```json')) {
        const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch) {
            try {
                const parsed = JSON.parse(jsonMatch[1]);
                if (parsed.type && parsed.data) {
                    chartData = parsed;
                    mainContent = content.replace(jsonMatch[0], '').trim();
                }
            } catch (e) { console.error("Chart parse error:", e); }
        }
    }

    const innerHTML = role === 'user' ? `
        <div class="bg-blue-600 text-white rounded-2xl rounded-br-sm py-3 px-5 shadow-sm max-w-[80%] break-words">
            <div class="prose prose-invert max-w-none text-sm">${marked.parse(mainContent)}</div>
        </div>
        <div class="w-8 h-8 rounded-full bg-blue-500/20 flex flex-shrink-0 items-center justify-center border border-blue-500/30">
            <i data-lucide="user" class="w-4 h-4 text-blue-400"></i>
        </div>
    ` : `
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex flex-shrink-0 items-center justify-center border border-emerald-500/30">
            <i data-lucide="bot" class="w-4 h-4 text-emerald-400"></i>
        </div>
        <div class="bg-gray-800 text-gray-200 rounded-2xl rounded-bl-sm py-3 px-5 shadow-sm border border-gray-700/50 max-w-[85%] break-words">
            <div class="prose prose-invert max-w-none text-sm markdown-body">${marked.parse(mainContent) || '<div class="flex gap-1 py-1"><div class="w-2 h-2 rounded-full bg-gray-500 typing-dot"></div><div class="w-2 h-2 rounded-full bg-gray-500 typing-dot" style="animation-delay: 0.2s"></div><div class="w-2 h-2 rounded-full bg-gray-500 typing-dot" style="animation-delay: 0.4s"></div></div>'}</div>
            ${chartData ? `<div class="w-full mt-4 bg-gray-900/50 rounded-xl p-3 border border-gray-700/50"><canvas id="chart-${Date.now()}"></canvas></div>` : ''}
        </div>
    `;

    msgDiv.innerHTML = innerHTML;
    chatMessages.appendChild(msgDiv);
    lucide.createIcons({ root: msgDiv });

    if (chartData && !isStreamingNode) {
        const canvas = msgDiv.querySelector('canvas');
        if (canvas) {
            new Chart(canvas, {
                type: chartData.type,
                data: chartData.data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#e5e7eb' } } },
                    scales: {
                        x: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } },
                        y: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } }
                    }
                }
            });
            // Give specific height for chart wrapper
            canvas.parentElement.style.height = "300px";
            canvas.parentElement.style.position = "relative";
        }
    }

    scrollToBottom();
    return msgDiv;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Chat Submission
async function handleSend() {
    if (isStreaming) return;
    const query = messageInput.value.trim();
    if (!query) return;

    if (!currentSessionId) {
        await createNewSession();
    }

    messageInput.value = '';
    messageInput.style.height = 'auto';

    renderMessage('user', query);

    isStreaming = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>';
    lucide.createIcons();

    const assistantMsgNode = renderMessage('assistant', '', true);
    const contentNode = assistantMsgNode.querySelector('.markdown-body');
    let fullContent = '';

    try {
        const source = new EventSource(`${API_BASE}/chat/message/stream?session_id=${currentSessionId}&query=${encodeURIComponent(query)}`);

        let piiMapping = {};

        let auditTurnCount = 0;

        source.addEventListener('audit', function(event) {
            const auditData = JSON.parse(event.data);
            piiMapping = auditData.mapping || {};
            
            if (!auditData.chunks || auditData.chunks.length === 0) return;
            
            auditTurnCount++;
            const container = document.getElementById('auditContainer');
            const emptyState = document.getElementById('auditEmptyState');
            if (emptyState) emptyState.classList.add('hidden');
            
            const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            
            let turnHtml = `<div class="mb-4 border border-gray-700/60 rounded-xl overflow-hidden">
                <div class="bg-gray-800 flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
                    <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1.5">
                        <i data-lucide="activity" class="w-3 h-3"></i>
                        Query ${auditTurnCount} — Context Retrieval
                    </span>
                    <span class="text-[10px] text-gray-500 font-mono">${now}</span>
                </div>
                <div class="p-3 space-y-3">`;

            // Chunks
            auditData.chunks.forEach((chunk, i) => {
                turnHtml += `
                <div class="bg-gray-900/60 rounded-lg border border-gray-700/40">
                    <div class="flex items-center gap-2 px-3 py-1.5 border-b border-gray-700/40">
                        <i data-lucide="scan-text" class="w-3 h-3 text-gray-400"></i>
                        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Chunk ${i+1}</span>
                        <span class="text-[10px] text-blue-400 truncate max-w-[160px] normal-case">${chunk.source}</span>
                    </div>
                    <div class="grid grid-cols-2 divide-x divide-gray-700/40">
                        <div class="p-2">
                            <div class="text-[9px] text-gray-500 uppercase mb-1 tracking-widest">Extracted</div>
                            <div class="text-[10px] text-gray-400 overflow-y-auto max-h-24 custom-scrollbar leading-relaxed">${chunk.original.replace(/</g, '&lt;')}</div>
                        </div>
                        <div class="p-2 bg-emerald-900/10">
                            <div class="text-[9px] text-emerald-500/70 uppercase mb-1 tracking-widest">Masked to LLM</div>
                            <div class="text-[10px] text-emerald-400/80 overflow-y-auto max-h-24 custom-scrollbar leading-relaxed">${chunk.masked.replace(/</g, '&lt;')}</div>
                        </div>
                    </div>
                </div>`;
            });

            // PII Mapping
            if(Object.keys(piiMapping).length > 0) {
                turnHtml += `
                <div class="bg-blue-900/10 rounded-lg p-3 border border-blue-900/30">
                    <h4 class="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <i data-lucide="shield" class="w-3 h-3"></i> Active PII Intercepts
                    </h4>
                    <div class="flex flex-wrap gap-1.5">`;
                for(const [tag, val] of Object.entries(piiMapping)) {
                    turnHtml += `<div class="text-[10px] bg-blue-900/30 border border-blue-800/50 text-blue-300 px-2 py-1 rounded"><strong class="text-white">${tag}</strong> &rarr; ${val}</div>`;
                }
                turnHtml += `</div></div>`;
            }

            turnHtml += `</div></div>`;
            
            // Prepend the new turn at the top of the container (most recent first)
            container.insertAdjacentHTML('afterbegin', turnHtml);
            lucide.createIcons({ root: container });
            
            // Flash the audit tab button badge (don't hijack drawer open)
            const auditTabBtn = document.getElementById('tabAudit');
            if (auditTabBtn && !auditTabBtn.classList.contains('text-blue-400')) {
                let badge = auditTabBtn.querySelector('.audit-badge');
                if (!badge) {
                    const b = document.createElement('span');
                    b.className = 'audit-badge w-2 h-2 bg-blue-500 rounded-full inline-block ml-1 animate-pulse';
                    auditTabBtn.appendChild(b);
                }
            }
        });

        source.addEventListener('message', function(event) {
            const dataStr = event.data;
            if (dataStr === '[DONE]') {
                source.close();
                isStreaming = false;
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<i data-lucide="send" class="w-5 h-5 ml-0.5"></i>';
                lucide.createIcons();
                
                chatMessages.removeChild(assistantMsgNode);
                renderMessage('assistant', fullContent);
                return;
            }

            try {
                const data = JSON.parse(dataStr);
                if (data.delta) {
                    let unmaskedDelta = data.delta;
                    for (const [tag, realVal] of Object.entries(piiMapping)) {
                        unmaskedDelta = unmaskedDelta.split(tag).join(`<span class="bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1 rounded text-[0.9em]" title="Securely unmasked by PIIVault natively in browser">${realVal}</span>`);
                    }
                    fullContent += unmaskedDelta;
                    contentNode.innerHTML = marked.parse(fullContent);
                    scrollToBottom();
                }
            } catch (e) {
                console.error("Parse error in stream chunk", e);
            }
        });

        source.addEventListener('error', function(event) {
            console.error('EventSource failed:', event);
            try {
                const data = JSON.parse(event.data);
                if(data && data.detail) {
                    contentNode.innerHTML += `\n\n<span class="text-red-400 font-bold border border-red-500/50 bg-red-500/10 p-2 rounded">Error: ${data.detail}</span>`;
                }
            } catch(e) {
                if (!fullContent) {
                    contentNode.innerHTML = `<span class="text-red-400">Stream connection unexpectedly terminated.</span>`;
                }
            }
            source.close();
            isStreaming = false;
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i data-lucide="send" class="w-5 h-5 ml-0.5"></i>';
            lucide.createIcons();
        });
    } catch (error) {
        contentNode.innerHTML = `<span class="text-red-400">Error spinning up EventSource pipeline.</span>`;
        console.error(error);
        isStreaming = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i data-lucide="send" class="w-5 h-5 ml-0.5"></i>';
        lucide.createIcons();
    }
}

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});
sendBtn.addEventListener('click', handleSend);
newChatBtn.addEventListener('click', createNewSession);

// Account Modal Logic
const openAccountBtn = document.getElementById('openAccountBtn');
const closeAccountBtn = document.getElementById('closeAccountBtn');
const accountModal = document.getElementById('accountModal');
const accountModalBody = document.getElementById('accountModalBody');

if (openAccountBtn && closeAccountBtn && accountModal) {
    openAccountBtn.onclick = async () => {
        accountModal.classList.remove('hidden');
        accountModal.classList.add('flex');
        setTimeout(() => {
            accountModal.classList.remove('opacity-0');
            accountModalBody.classList.remove('scale-95');
            accountModalBody.classList.add('scale-100');
        }, 10);
        
        try {
            const res = await fetch(`${API_BASE}/auth/me/${userId}`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById('accountUsername').textContent = data.username;
                document.getElementById('accountEmail').textContent = data.email;
            } else {
                document.getElementById('accountUsername').textContent = 'Standard Profile';
                document.getElementById('accountEmail').textContent = 'User details protected';
            }
        } catch (e) {
            console.error("Failed fetching user details:", e);
        }
    };

    closeAccountBtn.onclick = () => {
        accountModal.classList.add('opacity-0');
        accountModalBody.classList.remove('scale-100');
        accountModalBody.classList.add('scale-95');
        setTimeout(() => {
            accountModal.classList.remove('flex');
            accountModal.classList.add('hidden');
        }, 300);
    };
}

// File Upload System & Knowledge Base Drawer Openers
attachBtn.onclick = () => { 
    const drawer = document.getElementById('documentDrawer');
    drawer.classList.remove('w-0');
    drawer.classList.add('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
    switchDrawerTab('files');
    loadDocuments(); 
};

// Activity Log / Workspace Toggle
const toggleDrawerBtn = document.getElementById('toggleDrawerBtn');
if(toggleDrawerBtn) {
    toggleDrawerBtn.onclick = () => {
        const drawer = document.getElementById('documentDrawer');
        if (drawer.classList.contains('w-0')) {
            drawer.classList.remove('w-0');
            drawer.classList.add('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
        } else {
            drawer.classList.remove('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
            drawer.classList.add('w-0');
        }
    };
}

// Drag and drop logic
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('border-blue-500', 'bg-blue-500/10'), false);
});
['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-blue-500', 'bg-blue-500/10'), false);
});

dropZone.addEventListener('drop', handleDrop, false);
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', function () { handleFiles(this.files); });

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length === 0) return;
    uploadFile(files[0]);
    if (fileInput) fileInput.value = '';
}

function uploadFile(file) {
    if (!currentSessionId) return alert("Please create or select a session first.");

    uploadStatus.classList.remove('hidden');
    uploadFilename.textContent = file.name;
    uploadProgressBar.style.width = '0%';
    uploadProgressText.textContent = '0%';
    uploadStatusMessage.textContent = 'Uploading and processing (this may take a moment)...';

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/documents/upload?session_id=${currentSessionId}`, true);

    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            uploadProgressBar.style.width = percentComplete + '%';
            uploadProgressText.textContent = Math.round(percentComplete) + '%';
        }
    };

    xhr.onload = function () {
        if (this.status == 200) {
            uploadStatusMessage.textContent = 'Document successfully embedded to Knowledge Base!';
            uploadStatusMessage.className = 'text-xs text-emerald-400 mt-2 text-center font-medium';
            uploadProgressBar.classList.add('bg-emerald-500');
            loadDocuments();
            setTimeout(() => {
                uploadStatus.classList.add('hidden');
                uploadProgressBar.classList.remove('bg-emerald-500');
                uploadStatusMessage.className = 'text-xs text-gray-500 mt-2 text-center';
            }, 3000);
        } else {
            uploadStatusMessage.textContent = 'Error uploading document: ' + this.responseText;
            uploadStatusMessage.className = 'text-xs text-red-500 mt-2 text-center font-medium';
            uploadProgressBar.classList.add('bg-red-500');
        }
    };

    xhr.onerror = function () {
        uploadStatusMessage.textContent = 'Network Error during upload.';
        uploadStatusMessage.className = 'text-xs text-red-500 mt-2 text-center font-medium';
    };

    xhr.send(formData);
}

async function loadDocuments() {
    if (!currentSessionId) return;
    try {
        const res = await fetch(`${API_BASE}/documents/list/${currentSessionId}`);
        const docs = await res.json();
        documentList.innerHTML = '';
        if (docs.length === 0) {
            documentList.innerHTML = '<p class="text-xs text-gray-500 text-center py-2">No documents in this session.</p>';
        } else {
            docs.forEach(doc => {
                const docEl = document.createElement('div');
                docEl.className = 'flex justify-between items-center p-3 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg border border-gray-700/50 cursor-pointer transition-colors group';
                docEl.onclick = () => previewDocument(doc.filename);

                docEl.innerHTML = `
                    <div class="flex items-center gap-3 overflow-hidden">
                        <i data-lucide="file-text" class="w-4 h-4 text-blue-400 shrink-0 group-hover:text-blue-300"></i>
                        <span class="text-sm text-gray-300 truncate group-hover:text-white">${doc.filename}</span>
                    </div>
                    <div class="flex items-center gap-3">
                        ${doc.report_status === 'COMPLETED' ? 
                            `<button onclick="event.stopPropagation(); window.openReport(${doc.id}, '${doc.filename}')" class="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded border border-blue-500/30 hover:bg-blue-500/30 transition-colors flex items-center gap-1"><i data-lucide="file-search" class="w-3 h-3"></i> Report</button>
                             <button onclick="event.stopPropagation(); window.openVisualizations(${doc.id})" class="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors flex items-center gap-1"><i data-lucide="bar-chart-2" class="w-3 h-3"></i> Visualize</button>`
                            : (doc.report_status === 'FAILED' ? `<span class="px-2 py-1 bg-red-500/10 text-red-400 text-xs rounded flex items-center gap-1"><i data-lucide="alert-circle" class="w-3 h-3"></i> Failed</span>` : (doc.report_status === 'READY' ? `` : `<span class="px-2 py-1 bg-amber-500/10 text-amber-400 text-xs rounded border border-amber-500/20 flex items-center gap-1"><i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Generating...</span>`))
                        }
                        <span class="text-xs text-gray-500 shrink-0 hidden sm:block">${new Date(doc.uploaded_at).toLocaleDateString()}</span>
                    </div>
                `;
                documentList.appendChild(docEl);
            });
            lucide.createIcons();
        }
    } catch (e) {
        console.error("Error loading documents:", e);
    }
}

// Open the AI-generated JSON report as rich HTML in the Report tab
window.openReport = async function(docId, filename) {
    const drawer = document.getElementById('documentDrawer');
    if (drawer.classList.contains('w-0')) {
        drawer.classList.remove('w-0');
        drawer.classList.add('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
    }
    switchDrawerTab('preview');

    const renderer = document.getElementById('reportRenderer');
    const emptyState = document.getElementById('previewEmptyState');
    const headerBar = document.getElementById('previewHeaderBar');
    const titleDisplay = document.getElementById('previewTitleDisplay');

    // Show loading
    if (emptyState) emptyState.classList.add('hidden');
    if (headerBar) headerBar.classList.remove('hidden');
    if (titleDisplay) titleDisplay.textContent = filename;
    renderer.innerHTML = `<div class="flex flex-col items-center justify-center py-16 opacity-60">
        <svg class="animate-spin w-10 h-10 text-emerald-400 mb-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path></svg>
        <p class="text-sm text-gray-400">Loading AI Analysis Report...</p>
    </div>`;

    try {
        const res = await fetch(`${API_BASE}/documents/report/${docId}`);
        if (!res.ok) {
            renderer.innerHTML = `<div class="p-6 text-center opacity-60"><p class="text-red-400 text-sm">Report not ready yet. Please wait for processing to complete.</p></div>`;
            return;
        }
        const data = await res.json();
        const rj = typeof data.report_json === 'string' ? JSON.parse(data.report_json) : data.report_json;
        renderReportHTML(rj, renderer, filename);
    } catch(e) {
        renderer.innerHTML = `<div class="p-6 text-center text-red-400 opacity-70"><p class="text-sm">Error loading report: ${e.message}</p></div>`;
    }
};

function renderReportHTML(rj, container, filename) {
    let html = '';

    // Header banner
    html += `<div class="bg-gradient-to-r from-blue-600/20 to-emerald-600/20 border border-blue-500/20 rounded-xl p-5 mb-5">
        <p class="text-[10px] text-blue-400 uppercase tracking-widest font-bold mb-1">AI Analysis Complete</p>
        <h2 class="text-lg font-bold text-white truncate">${filename}</h2>
    </div>`;

    // KPI Cards
    if (rj.kpis && rj.kpis.length > 0) {
        html += `<div class="grid grid-cols-2 gap-3 mb-5">`;
        rj.kpis.forEach(kpi => {
            const up = kpi.trend && kpi.trend.toLowerCase().includes('up');
            const down = kpi.trend && kpi.trend.toLowerCase().includes('down');
            const color = up ? 'text-emerald-400' : down ? 'text-red-400' : 'text-gray-400';
            html += `<div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                <p class="text-[10px] text-gray-500 uppercase tracking-widest mb-1">${kpi.label}</p>
                <p class="text-xl font-black text-white">${kpi.value}</p>
                <p class="text-xs ${color} font-medium mt-1">${kpi.trend || ''}</p>
            </div>`;
        });
        html += `</div>`;
    }

    // Executive Summary
    if (rj.executive_summary) {
        html += `<div class="bg-blue-500/10 border border-blue-500/20 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-blue-400 uppercase tracking-widest font-bold mb-3">&#x26A1; Executive Summary</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.executive_summary}</p>
        </div>`;
    }

    // Data Overview
    if (rj.data_overview) {
        html += `<div class="bg-gray-800/60 border border-gray-700/50 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-gray-400 uppercase tracking-widest font-bold mb-2">Document Profile</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.data_overview}</p>
        </div>`;
    }

    // Analysis Text
    if (rj.analysis_text) {
        html += `<div class="bg-gray-800/60 border border-gray-700/50 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-gray-400 uppercase tracking-widest font-bold mb-2">Deep Analysis</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.analysis_text}</p>
        </div>`;
    }

    // Predictive Forecast
    if (rj.predictive_forecast) {
        html += `<div class="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-emerald-400 uppercase tracking-widest font-bold mb-2">&#x1F52E; Predictive Forecast</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.predictive_forecast}</p>
        </div>`;
    }

    // Risk Assessment
    if (rj.risk_assessment) {
        html += `<div class="bg-red-500/10 border border-red-500/20 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-red-400 uppercase tracking-widest font-bold mb-2">&#x26A0; Risk Assessment</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.risk_assessment}</p>
        </div>`;
    }

    // Key Insights
    if (rj.key_insights && rj.key_insights.length > 0) {
        html += `<div class="bg-gray-800/60 border border-gray-700/50 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-gray-400 uppercase tracking-widest font-bold mb-3">Key Findings</h3>
            <ul class="space-y-2">`;
        rj.key_insights.forEach(insight => {
            html += `<li class="flex items-start gap-2 text-sm text-gray-300"><span class="text-blue-400 mt-0.5 shrink-0">&#x2022;</span>${insight}</li>`;
        });
        html += `</ul></div>`;
    }

    // Recommendations
    if (rj.recommendations && rj.recommendations.length > 0) {
        html += `<div class="bg-gray-800/60 border border-gray-700/50 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-gray-400 uppercase tracking-widest font-bold mb-3">Strategic Recommendations</h3>
            <ul class="space-y-2">`;
        rj.recommendations.forEach(rec => {
            html += `<li class="flex items-start gap-2 text-sm text-gray-300"><span class="text-emerald-400 mt-0.5 shrink-0">&#x2714;</span>${rec}</li>`;
        });
        html += `</ul></div>`;
    }

    // Conclusion
    if (rj.conclusion) {
        html += `<div class="bg-gray-800/60 border border-gray-700/50 rounded-xl p-5 mb-5">
            <h3 class="text-xs text-gray-400 uppercase tracking-widest font-bold mb-2">Conclusion</h3>
            <p class="text-sm text-gray-300 leading-relaxed">${rj.conclusion}</p>
        </div>`;
    }

    container.innerHTML = html;
    lucide.createIcons();
}

document.getElementById('closeDrawerBtn').onclick = () => {
    const drawer = document.getElementById('documentDrawer');
    drawer.classList.remove('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
    drawer.classList.add('w-0');
};

// AI Visualization Framework
let activeChartInstances = [];

window.openVisualizations = async function(docId) {
    const drawer = document.getElementById('documentDrawer');
    const vizContainer = document.getElementById('vizContainer');
    const vizEmptyState = document.getElementById('vizEmptyState');
    
    if (drawer.classList.contains('w-0')) {
        drawer.classList.remove('w-0');
        drawer.classList.add('w-[400px]', 'lg:w-[500px]', 'xl:w-[600px]');
    }
    switchDrawerTab('visualizations');

    // Reset view
    vizEmptyState.classList.remove('hidden');
    vizEmptyState.innerHTML = '<i data-lucide="loader-2" class="w-12 h-12 text-blue-400 mx-auto mb-3 animate-spin"></i><p class="text-sm text-gray-400">Booting Analytics Engine...</p>';
    vizContainer.classList.add('hidden');
    
    // Clear old charts
    activeChartInstances.forEach(c => c.destroy());
    activeChartInstances = [];
    vizContainer.innerHTML = '';
    lucide.createIcons();

    try {
        const res = await fetch(`${API_BASE}/documents/report/${docId}`);
        if(res.ok) {
            const data = await res.json();
            if(data.status === 'COMPLETED') {
                renderVisualizations(data.report_json);
            } else {
                vizEmptyState.innerHTML = '<i data-lucide="alert-circle" class="w-12 h-12 text-red-400 mx-auto mb-3"></i><p class="text-sm text-red-400">Data not ready. Still processing in backend.</p>';
                lucide.createIcons();
            }
        }
    } catch(e) {
        vizEmptyState.innerHTML = '<i data-lucide="wifi-off" class="w-12 h-12 text-red-400 mx-auto mb-3"></i><p class="text-sm text-red-400">Connection error fetching analytics.</p>';
        lucide.createIcons();
    }
};

function renderVisualizations(jsonSchema) {
    try {
        if (typeof jsonSchema === 'string') {
            jsonSchema = JSON.parse(jsonSchema);
        }
    } catch (e) { console.error("Failed to parse report JSON", e); return; }

    const vizEmptyState = document.getElementById('vizEmptyState');
    const vizContainer = document.getElementById('vizContainer');
    
    vizEmptyState.classList.add('hidden');
    vizContainer.classList.remove('hidden');

    // Inject KPIs first
    if(jsonSchema.kpis && jsonSchema.kpis.length > 0) {
        let kpiHtml = `<div class="grid grid-cols-2 gap-4 mb-6">`;
        jsonSchema.kpis.forEach(kpi => {
            let trendIcon = kpi.trend.toLowerCase().includes('up') ? '<i data-lucide="trending-up" class="w-4 h-4 text-emerald-400"></i>' : (kpi.trend.toLowerCase().includes('down') ? '<i data-lucide="trending-down" class="w-4 h-4 text-red-400"></i>' : '<i data-lucide="minus" class="w-4 h-4 text-gray-400"></i>');
            kpiHtml += `
                <div class="bg-gray-800/80 border border-gray-700 rounded-xl p-4 shadow-xl">
                    <p class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-2">${kpi.label}</p>
                    <div class="flex items-center gap-2">
                        <p class="text-2xl font-black text-gray-100">${kpi.value}</p>
                        ${trendIcon}
                    </div>
                </div>
            `;
        });
        kpiHtml += `</div>`;
        vizContainer.innerHTML += kpiHtml;
    }

    // Inject Executive Insight 
    if(jsonSchema.executive_summary) {
        vizContainer.innerHTML += `
            <div class="bg-blue-500/10 border border-blue-500/20 rounded-xl p-5 mb-6">
                <h4 class="text-blue-400 text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2"><i data-lucide="lightbulb" class="w-4 h-4"></i> Executive Vector</h4>
                <p class="text-sm text-blue-100/80 leading-relaxed">${jsonSchema.executive_summary}</p>
            </div>
        `;
    }

    // Charting
    if(jsonSchema.charts && jsonSchema.charts.length > 0) {
        const chartConfigsToRender = [];
        jsonSchema.charts.forEach((chartData, idx) => {
            const canvasId = `aiChart_${idx}`;
            vizContainer.innerHTML += `
                <div class="bg-gray-800/80 border border-gray-700/50 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-colors">
                    <p class="text-sm font-semibold text-gray-200 mb-4 whitespace-nowrap">${chartData.title}</p>
                    <div class="w-full relative h-[250px]">
                        <canvas id="${canvasId}"></canvas>
                    </div>
                </div>
            `;
            chartConfigsToRender.push({ id: canvasId, config: chartData });
        });

        setTimeout(() => {
            chartConfigsToRender.forEach(instance => {
                const chartData = instance.config;
                const isRadial = ['pie', 'doughnut', 'radar'].includes(chartData.type);
                
                const backgroundColors = isRadial 
                    ? ['rgba(239, 68, 68, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(16, 185, 129, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(139, 92, 246, 0.8)'] 
                    : 'rgba(16, 185, 129, 0.5)';
                    
                const chartOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { display: isRadial, position: 'bottom', labels: { color: '#cbd5e1', font: {size: 11} } }
                    }
                };
                
                if (!isRadial) {
                    chartOptions.scales = {
                        y: { display: true, beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { display: true, grid: { display: false }, ticks: { color: '#94a3b8' } }
                    };
                } else if (chartData.type === 'radar') {
                    chartOptions.scales = { r: { grid: { color: '#334155' }, angleLines: { color: '#334155' }, pointLabels: { color: '#94a3b8' }, ticks: { display: false } } };
                }

                const inst = new Chart(document.getElementById(instance.id), {
                    type: chartData.type,
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: 'Metrics',
                            data: chartData.data,
                            backgroundColor: backgroundColors,
                            borderColor: isRadial && chartData.type !== 'radar' ? 'transparent' : '#10b981',
                            borderWidth: chartData.type === 'radar' ? 2 : (isRadial ? 0 : 2),
                            borderRadius: chartData.type === 'bar' ? 4 : 0,
                            tension: 0.4,
                            fill: chartData.type === 'line' ? true : false
                        }]
                    },
                    options: chartOptions
                });
                activeChartInstances.push(inst);
            });
            lucide.createIcons();
        }, 50);
    }
}

window.switchDrawerTab = function(tab) {
    const tabMap = {
        'files':          { btnId: 'tabFiles',          contentId: 'filesContent' },
        'preview':        { btnId: 'tabPreview',        contentId: 'previewContent' },
        'visualizations': { btnId: 'tabVisualizations', contentId: 'visualizationsContent' },
        'audit':          { btnId: 'tabAudit',          contentId: 'auditContent' }
    };
    
    Object.entries(tabMap).forEach(([t, ids]) => {
        const btn = document.getElementById(ids.btnId);
        const content = document.getElementById(ids.contentId);
        if (!btn || !content) return;
        
        if (t === tab) {
            btn.classList.remove('text-gray-500', 'font-medium', 'border-transparent');
            btn.classList.add('text-blue-400', 'font-bold', 'border-blue-400');
            content.classList.remove('hidden');
            // Remove audit badge when user opens audit tab
            if (t === 'audit') {
                const badge = btn.querySelector('.audit-badge');
                if (badge) badge.remove();
            }
        } else {
            btn.classList.remove('text-blue-400', 'font-bold', 'border-blue-400');
            btn.classList.add('text-gray-500', 'font-medium', 'border-transparent');
            content.classList.add('hidden');
        }
    });
};

// Start
init();
