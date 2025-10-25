// Configuration
const API_BASE_URL = 'http://localhost:5001'; // Local Flask app for testing

// Global variables
let currentJobId = null;
let currentFiles = {};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Set default invoice date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('invoiceDate').value = today;
    
    // Setup file input handlers
    setupFileInputs();
});

function setupFileInputs() {
    const mainFile = document.getElementById('mainFile');
    const adminFile = document.getElementById('adminFile');
    
    mainFile.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            currentFiles.main = file;
            document.getElementById('mainFileInfo').textContent = `${file.name} (${formatFileSize(file.size)})`;
            checkUploadReady();
        }
    });
    
    adminFile.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            currentFiles.admin = file;
            document.getElementById('adminFileInfo').textContent = `${file.name} (${formatFileSize(file.size)})`;
            checkUploadReady();
        }
    });
}

function checkUploadReady() {
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = !(currentFiles.main && currentFiles.admin);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function uploadFiles() {
    if (!currentFiles.main || !currentFiles.admin) {
        showError('Please select both files');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    
    try {
        const formData = new FormData();
        formData.append('main_file', currentFiles.main);
        formData.append('admin_file', currentFiles.admin);
        
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            currentJobId = result.job_id;
            showStep('step2');
            showSuccess('Files uploaded successfully!');
        } else {
            showError(result.error || 'Upload failed');
        }
    } catch (error) {
        showError('Upload failed: ' + error.message);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload Files';
    }
}

async function startProcessing() {
    const invoiceDate = document.getElementById('invoiceDate').value;
    const startInvoiceNumber = document.getElementById('startInvoiceNumber').value;
    const allowIssues = document.getElementById('allowIssues').value === 'true';
    
    if (!invoiceDate) {
        showError('Please select an invoice date');
        return;
    }
    
    const processBtn = document.getElementById('processBtn');
    processBtn.disabled = true;
    processBtn.textContent = 'Starting...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                config: {
                    allow_issues: allowIssues,
                    verbose: true
                }
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStep('step3');
            monitorProgress();
        } else {
            showError(result.error || 'Processing failed to start');
        }
    } catch (error) {
        showError('Failed to start processing: ' + error.message);
    } finally {
        processBtn.disabled = false;
        processBtn.textContent = 'Start Processing';
    }
}

async function monitorProgress() {
    const progressFill = document.getElementById('progressFill');
    const statusText = document.getElementById('statusText');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/status/${currentJobId}`);
            const status = await response.json();
            
            if (response.ok) {
                progressFill.style.width = `${status.progress || 0}%`;
                statusText.textContent = status.message || 'Processing...';
                
                if (status.status === 'completed') {
                    clearInterval(interval);
                    showResults(status.result);
                    showStep('step4');
                } else if (status.status === 'failed') {
                    clearInterval(interval);
                    showError(status.message || 'Processing failed');
                }
            }
        } catch (error) {
            console.error('Status check failed:', error);
        }
    }, 1000);
}

function showResults(result) {
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = `
        <div class="result-item">
            <span>Total Sellers:</span>
            <span>${result.total_sellers}</span>
        </div>
        <div class="result-item">
            <span>Total Issues:</span>
            <span>${result.total_issues}</span>
        </div>
        <div class="result-item">
            <span>Total Labels:</span>
            <span>${result.summary_stats.total_labels.toLocaleString()}</span>
        </div>
        <div class="result-item">
            <span>Total Fees:</span>
            <span>€${result.summary_stats.total_fees.toLocaleString()}</span>
        </div>
        ${result.has_issues ? '<div class="error">⚠️ Issues detected - check the output file</div>' : ''}
    `;
}

async function downloadResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/download/${currentJobId}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `aggregated_results_${currentJobId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            showError(error.error || 'Download failed');
        }
    } catch (error) {
        showError('Download failed: ' + error.message);
    }
}

async function startTeamleaderConversion() {
    const invoiceDate = document.getElementById('invoiceDate').value;
    const startInvoiceNumber = document.getElementById('startInvoiceNumber').value;
    
    const teamleaderBtn = document.getElementById('teamleaderBtn');
    teamleaderBtn.disabled = true;
    teamleaderBtn.textContent = 'Starting...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/teamleader`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                invoice_date: invoiceDate,
                start_invoice_number: parseInt(startInvoiceNumber)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStep('step5');
            monitorTeamleaderProgress();
        } else {
            showError(result.error || 'Teamleader conversion failed to start');
        }
    } catch (error) {
        showError('Failed to start Teamleader conversion: ' + error.message);
    } finally {
        teamleaderBtn.disabled = false;
        teamleaderBtn.textContent = 'Convert to Teamleader';
    }
}

async function monitorTeamleaderProgress() {
    const progressFill = document.getElementById('teamleaderProgressFill');
    const statusText = document.getElementById('teamleaderStatusText');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/status/${currentJobId}`);
            const status = await response.json();
            
            if (response.ok) {
                progressFill.style.width = `${status.progress || 0}%`;
                statusText.textContent = status.message || 'Converting...';
                
                if (status.status === 'completed') {
                    clearInterval(interval);
                    showStep('step6');
                } else if (status.status === 'failed') {
                    clearInterval(interval);
                    showError(status.message || 'Teamleader conversion failed');
                }
            }
        } catch (error) {
            console.error('Status check failed:', error);
        }
    }, 1000);
}

async function downloadTeamleaderResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/download/${currentJobId}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `teamleader_results_${currentJobId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            showError(error.error || 'Download failed');
        }
    } catch (error) {
        showError('Download failed: ' + error.message);
    }
}

function showStep(stepId) {
    // Hide all steps
    document.querySelectorAll('.step').forEach(step => {
        step.classList.add('hidden');
    });
    
    // Show the specified step
    document.getElementById(stepId).classList.remove('hidden');
}

function showError(message) {
    // Remove existing error/success messages
    document.querySelectorAll('.error, .success').forEach(el => el.remove());
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    
    const currentStep = document.querySelector('.step:not(.hidden)');
    currentStep.appendChild(errorDiv);
}

function showSuccess(message) {
    // Remove existing error/success messages
    document.querySelectorAll('.error, .success').forEach(el => el.remove());
    
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    
    const currentStep = document.querySelector('.step:not(.hidden)');
    currentStep.appendChild(successDiv);
}
