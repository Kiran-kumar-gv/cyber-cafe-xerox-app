// Main JavaScript for Cyber Café Xerox Service

document.addEventListener('DOMContentLoaded', function() {
    // File upload form handling
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('progressContainer');
    const fileInput = document.getElementById('file');

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            // Show loading state
            uploadBtn.classList.add('loading');
            uploadBtn.disabled = true;
            
            // Show progress container
            if (progressContainer) {
                progressContainer.style.display = 'block';
                
                // Simulate progress (since we can't get real upload progress easily in basic setup)
                let progress = 0;
                const progressBar = progressContainer.querySelector('.progress-bar');
                const interval = setInterval(() => {
                    progress += Math.random() * 15;
                    if (progress > 90) progress = 90; // Don't complete until form actually submits
                    progressBar.style.width = progress + '%';
                    
                    if (progress >= 90) {
                        clearInterval(interval);
                    }
                }, 100);
            }
        });
    }

    // File input validation
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files;
            if (file) {
                // Check file size (16MB limit)
                const maxSize = 16 * 1024 * 1024; // 16MB in bytes
                if (file.size > maxSize) {
                    alert('File size too large. Please select a file smaller than 16MB.');
                    this.value = '';
                    return;
                }

                // Check file type
                const allowedTypes = ['application/pdf', 'application/msword', 
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
                
                if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().match(/\.(pdf|docx?|jpe?g|png|gif)$/)) {
                    alert('Invalid file type. Please select a PDF, Word document, or image file.');
                    this.value = '';
                    return;
                }

                // Show file info
                console.log('Selected file:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
            }
        });
    }

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm dialogs for admin actions
    const confirmLinks = document.querySelectorAll('[onclick*="confirm"]');
    confirmLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to perform this action?')) {
                e.preventDefault();
            }
        });
    });
});

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(message, type = 'success') {
    // Simple toast notification (you can enhance this with Bootstrap toast component)
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}