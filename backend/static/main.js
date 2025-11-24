
// Use relative URL for production, localhost for development
//const API_URL = 'http://localhost:5000';
const API_URL = window.location.origin;
const version = 'v1.0';

window.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    checkHealth();
    setupTabs();
    setupForms();
});

async function checkHealth() {
    const statusDiv = document.getElementById('healthStatus');
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        statusDiv.innerHTML = `<span style="color: #10b981;">✓ ${data.service} - ${data.version}</span>`;
    } catch (error) {
        statusDiv.innerHTML = `<span style="color: #ef4444;">✗ Server offline</span>`;
    }
}

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    console.log('Found tabs:', tabBtns.length);
    console.log('Found contents:', tabContents.length);
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            console.log('Tab clicked:', tabId);
            
            // Remove active from all buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            
            // Remove active from all contents
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active to clicked button
            btn.classList.add('active');
            
            // Add active to corresponding content
            const targetContent = document.getElementById(`${tabId}Tab`);
            if (targetContent) {
                targetContent.classList.add('active');
                console.log('Activated content:', tabId);
            } else {
                console.error('Content not found for:', tabId);
            }
            
            // Clear results
            clearResult();
        });
    });
}

function setupForms() {
    // Link form
    const linkForm = document.getElementById('linkForm');
    if (linkForm) {
        linkForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('linkInput').value;
            await validateText('link', url);
        });
    }
    
    // VPA form
    const vpaForm = document.getElementById('vpaForm');
    if (vpaForm) {
        vpaForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const vpa = document.getElementById('vpaInput').value;
            await validateText('vpa', vpa);
        });
    }
    
    // Message form
    const messageForm = document.getElementById('messageForm');
    if (messageForm) {
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = document.getElementById('messageInput').value;
            await validateText('message', message);
        });
    }
    
    // QR form
    const qrForm = document.getElementById('qrForm');
    if (qrForm) {
        qrForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const file = document.getElementById('qrInput').files[0];
            if (file) {
                await validateQR(file);
            } else {
                displayError('Please select a QR code image');
            }
        });
    }
}

async function validateText(type, value) {
    if (!value.trim()) {
        displayError('Please enter a value');
        return;
    }
    
    showLoading(true);
    clearResult();
    
    const clientStartTime = Date.now();
    
    try {
        const formData = new FormData();
        formData.append('type', type);
        formData.append('value', value);
        
        const response = await fetch(`${API_URL}/validate`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        const clientTime = Date.now() - clientStartTime;
        
        displayResult(data, type, clientTime);
    } catch (error) {
        displayError(`Error: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function validateQR(file) {
    showLoading(true);
    clearResult();
    
    const clientStartTime = Date.now();
    
    try {
        const formData = new FormData();
        formData.append('type', 'qr');
        formData.append('file', file);
        
        const response = await fetch(`${API_URL}/validate`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        const clientTime = Date.now() - clientStartTime;
        
        displayResult(data, 'qr', clientTime);
    } catch (error) {
        displayError(`Error: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function displayResult(data, type, clientTime) {
    const resultDiv = document.getElementById('result');
    
    if (data.error) {
        displayError(data.error);
        return;
    }
    
    const verdict = data.final_verdict || data.verdict || 'UNKNOWN';
    const score = data.risk_score || 0;  // ✅ FIXED - Use final risk_score only
    const cached = data.cached ? '⚡ CACHED' : '🔍 ANALYZED';
    const responseTime = data.response_time_ms || clientTime;
    
    // Verdict styling
    const verdictConfig = {
        'OK': { color: '#10b981', icon: '✅', label: 'SAFE' },
        'WARN': { color: '#f59e0b', icon: '⚠️', label: 'WARNING' },
        'BLOCK': { color: '#ef4444', icon: '⛔', label: 'BLOCKED' }
    };
    
    const config = verdictConfig[verdict] || verdictConfig['WARN'];
    
    // ✅ COLLECT ALL REASONS FROM ALL SOURCES
    let allReasons = [];
    
    // Get from main reasons array first
    if (data.reasons && data.reasons.length > 0) {
        allReasons = allReasons.concat(data.reasons);
    }
    
    // Add Stage 1 reasons if not already included
    if (data.stage1?.reasons) {
        data.stage1.reasons.forEach(r => {
            if (!allReasons.includes(r)) {
                allReasons.push(r);
            }
        });
    }
    
    // ✅ ADD STAGE 2 REASONS - THE HEADLESS BROWSER STUFF!
    if (data.stage2?.reasons) {
        data.stage2.reasons.forEach(r => {
            if (!allReasons.includes(r)) {
                allReasons.push(r);
            }
        });
    }
    
    // Default if still empty
    if (allReasons.length === 0) {
        allReasons = ['Standard analysis completed'];
    }
    
    let html = `
        <div class="result-box">
            <div class="verdict">
                <span class="verdict-icon">${config.icon}</span>
                <div>
                    <div class="verdict-text" style="color: ${config.color};">${config.label}</div>
                    <div class="meta-info">${cached} • ${responseTime}ms</div>
                </div>
                <div style="margin-left: auto; text-align: right;">
                    <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">Risk Score</div>
                    <div style="font-size: 24px; font-weight: bold; color: ${config.color};">
                        ${Math.round(score * 100)}%
                    </div>
                </div>
            </div>
            
            <div class="score-bar">
                <div class="score-fill" style="width: ${score * 100}%; background: ${config.color};"></div>
            </div>
            
            ${data.stage2?.ml_score !== undefined ? `
                <div style="margin-bottom: 15px; padding: 10px; background: white; border-radius: 6px; font-size: 13px;">
                    <span style="color: #6b7280;">ML Confidence:</span>
                    <strong style="color: #374151; margin-left: 6px;">${Math.round(data.stage2.ml_score * 100)}%</strong>
                </div>
            ` : ''}
            
            <div class="details">
                <div style="font-weight: 600; margin-bottom: 10px; color: #374151; font-size: 14px;">
                    ${data.stage2 ? '🔬 ' : ''}Analysis Details:
                </div>
                <ul>
                    ${allReasons.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
            
            ${data.stage1 && data.stage2 ? `
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                    <div style="font-weight: 600; margin-bottom: 10px; color: #374151; font-size: 13px;">
                        🔬 Two-Stage Analysis Breakdown
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 13px;">
                        <div>
                            <div style="color: #9ca3af; margin-bottom: 4px;">📊 Stage 1 (Static ML)</div>
                            <div style="font-weight: 600; color: #374151;">${data.stage1.verdict} • ${Math.round(data.stage1.score * 100)}%</div>
                            <ul style="margin-top: 8px; font-size: 12px; color: #6b7280;">
                                ${(data.stage1.reasons || []).map(r => `<li>• ${r}</li>`).join('')}
                            </ul>
                        </div>
                        <div>
                            <div style="color: #9ca3af; margin-bottom: 4px;">🌐 Stage 2 (Headless Browser)</div>
                            <div style="font-weight: 600; color: #374151;">${data.stage2.verdict} • ${Math.round(data.stage2.score * 100)}%</div>
                            <ul style="margin-top: 8px; font-size: 12px; color: #6b7280;">
                                ${(data.stage2.reasons || []).map(r => `<li>• ${r}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    
                    ${data.stage2.behavioral ? `
                        <div style="margin-top: 10px; padding: 10px; background: #f9fafb; border-radius: 6px; font-size: 12px;">
                            <div style="font-weight: 600; margin-bottom: 6px; color: #374151;">🔍 Headless Browser Findings:</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; color: #6b7280;">
                                ${data.stage2.behavioral.has_password_field ? '<div>⚠️ Password field detected</div>' : ''}
                                ${data.stage2.behavioral.has_otp_field ? '<div>⚠️ OTP field detected</div>' : ''}
                                ${data.stage2.behavioral.mimics_banking_ui ? '<div>⚠️ Banking UI mimicry</div>' : ''}
                                ${data.stage2.behavioral.redirects_to_different_domain ? '<div>⚠️ Domain redirect</div>' : ''}
                                ${data.stage2.behavioral.suspicious_javascript ? '<div>⚠️ Malicious JavaScript</div>' : ''}
                                ${data.stage2.behavioral.suspicious_domain ? '<div>⚠️ Suspicious domain</div>' : ''}
                                ${data.stage2.behavioral.connection_failed ? '<div>ℹ️ Connection failed</div>' : ''}
                                ${data.stage2.behavioral.trusted_domain ? '<div style="color: #10b981;">✅ Trusted domain</div>' : ''}
                            </div>
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;
    
    resultDiv.innerHTML = html;
    resultDiv.style.display = 'block';
}

function displayError(message) {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = `
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; color: #991b1b;">
            <strong>⚠️ Error:</strong> ${message}
        </div>
    `;
    resultDiv.style.display = 'block';
}

function showLoading(show) {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.style.display = show ? 'block' : 'none';
    }
}

function clearResult() {
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        resultDiv.innerHTML = '';
        resultDiv.style.display = 'none';
    }
}
