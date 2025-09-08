// Knowledge Management System JavaScript

// Global variables
let searchTimeout;
let currentPage = 1;
let isLoading = false;

// Initialize when document is ready
$(document).ready(function() {
    initializeKnowledgeSystem();
});

function initializeKnowledgeSystem() {
    // Initialize components
    initializeSearch();
    initializeFileUpload();
    initializeComments();
    initializeDocumentViewer();
    initializeFilters();
    initializeCharts();
    initializeTooltips();
    
    // Bind events
    bindEvents();
    
    // Load initial data
    loadDashboardStats();
}

// Search functionality
function initializeSearch() {
    const searchInput = $('#quick-search');
    const suggestionsContainer = $('#search-suggestions');
    
    searchInput.on('input', function() {
        const query = $(this).val().trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                fetchSearchSuggestions(query);
            }, 300);
        } else {
            suggestionsContainer.hide();
        }
    });
    
    // Hide suggestions when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-container').length) {
            suggestionsContainer.hide();
        }
    });
}

function fetchSearchSuggestions(query) {
    $.ajax({
        url: '/knowledge/ajax/search-suggestions/',
        method: 'GET',
        data: { q: query },
        success: function(data) {
            displaySearchSuggestions(data.suggestions);
        },
        error: function() {
            console.error('Failed to fetch search suggestions');
        }
    });
}

function displaySearchSuggestions(suggestions) {
    const container = $('#search-suggestions');
    container.empty();
    
    if (suggestions.length > 0) {
        suggestions.forEach(suggestion => {
            const item = $(`
                <div class="search-suggestion-item" data-url="${suggestion.url}">
                    <div class="d-flex align-items-center">
                        <i class="${suggestion.icon} mr-2"></i>
                        <div>
                            <div class="font-weight-bold">${suggestion.title}</div>
                            <small class="text-muted">${suggestion.description}</small>
                        </div>
                    </div>
                </div>
            `);
            
            item.on('click', function() {
                window.location.href = suggestion.url;
            });
            
            container.append(item);
        });
        
        container.show();
    } else {
        container.hide();
    }
}

// File upload functionality
function initializeFileUpload() {
    const uploadArea = $('.file-upload-area');
    const fileInput = $('#id_file');
    
    // Drag and drop
    uploadArea.on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('dragover');
    });
    
    uploadArea.on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
    });
    
    uploadArea.on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            fileInput[0].files = files;
            displaySelectedFiles(files);
        }
    });
    
    // Click to select
    uploadArea.on('click', function() {
        fileInput.click();
    });
    
    fileInput.on('change', function() {
        displaySelectedFiles(this.files);
    });
}

function displaySelectedFiles(files) {
    const container = $('#selected-files');
    container.empty();
    
    Array.from(files).forEach(file => {
        const fileItem = $(`
            <div class="selected-file-item d-flex align-items-center justify-content-between p-2 mb-2 border rounded">
                <div class="d-flex align-items-center">
                    <i class="${getFileIcon(file.name)} mr-2"></i>
                    <div>
                        <div class="font-weight-bold">${file.name}</div>
                        <small class="text-muted">${formatFileSize(file.size)}</small>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger remove-file">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `);
        
        container.append(fileItem);
    });
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    
    switch (ext) {
        case 'pdf':
            return 'fas fa-file-pdf text-danger';
        case 'doc':
        case 'docx':
            return 'fas fa-file-word text-primary';
        case 'xls':
        case 'xlsx':
            return 'fas fa-file-excel text-success';
        case 'ppt':
        case 'pptx':
            return 'fas fa-file-powerpoint text-warning';
        case 'txt':
            return 'fas fa-file-alt text-secondary';
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return 'fas fa-file-image text-info';
        default:
            return 'fas fa-file text-muted';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Comments functionality
function initializeComments() {
    // Add comment form submission
    $('#add-comment-form').on('submit', function(e) {
        e.preventDefault();
        
        const form = $(this);
        const formData = new FormData(this);
        
        $.ajax({
            url: form.attr('action'),
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(data) {
                if (data.success) {
                    loadComments();
                    form[0].reset();
                    showNotification('Comment added successfully', 'success');
                } else {
                    showNotification('Failed to add comment', 'error');
                }
            },
            error: function() {
                showNotification('Failed to add comment', 'error');
            }
        });
    });
    
    // Reply to comment
    $(document).on('click', '.reply-comment', function() {
        const commentId = $(this).data('comment-id');
        showReplyForm(commentId);
    });
}

function loadComments() {
    const documentId = $('#document-id').val();
    
    $.ajax({
        url: `/knowledge/ajax/comments/${documentId}/`,
        method: 'GET',
        success: function(data) {
            $('#comments-container').html(data.html);
        },
        error: function() {
            console.error('Failed to load comments');
        }
    });
}

function showReplyForm(commentId) {
    const replyForm = $(`
        <form class="reply-form mt-2" data-comment-id="${commentId}">
            <div class="form-group">
                <textarea class="form-control" name="content" rows="2" placeholder="Write a reply..."></textarea>
            </div>
            <div class="form-group">
                <button type="submit" class="btn btn-sm btn-primary">Reply</button>
                <button type="button" class="btn btn-sm btn-secondary cancel-reply">Cancel</button>
            </div>
        </form>
    `);
    
    $(`.comment-item[data-comment-id="${commentId}"]`).append(replyForm);
    
    replyForm.find('textarea').focus();
}

// Document viewer functionality
function initializeDocumentViewer() {
    // Track document views
    const documentId = $('#document-id').val();
    if (documentId) {
        trackDocumentView(documentId);
    }
    
    // Initialize document actions
    $('.download-document').on('click', function() {
        const url = $(this).data('url');
        trackDocumentDownload(documentId);
        window.open(url, '_blank');
    });
    
    $('.share-document').on('click', function() {
        showShareModal(documentId);
    });
    
    $('.bookmark-document').on('click', function() {
        toggleBookmark(documentId);
    });
}

function trackDocumentView(documentId) {
    $.ajax({
        url: `/knowledge/ajax/track-view/${documentId}/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        success: function(data) {
            if (data.view_count) {
                $('.view-count').text(data.view_count);
            }
        }
    });
}

function trackDocumentDownload(documentId) {
    $.ajax({
        url: `/knowledge/ajax/track-download/${documentId}/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    });
}

// Filters functionality
function initializeFilters() {
    $('.filter-checkbox').on('change', function() {
        applyFilters();
    });
    
    $('.filter-select').on('change', function() {
        applyFilters();
    });
    
    $('#clear-filters').on('click', function() {
        clearFilters();
    });
}

function applyFilters() {
    const filters = {};
    
    // Collect filter values
    $('.filter-checkbox:checked').each(function() {
        const name = $(this).attr('name');
        if (!filters[name]) filters[name] = [];
        filters[name].push($(this).val());
    });
    
    $('.filter-select').each(function() {
        const name = $(this).attr('name');
        const value = $(this).val();
        if (value) filters[name] = value;
    });
    
    // Apply filters
    loadFilteredDocuments(filters);
}

function loadFilteredDocuments(filters) {
    if (isLoading) return;
    
    isLoading = true;
    showLoadingSpinner();
    
    $.ajax({
        url: '/knowledge/documents/',
        method: 'GET',
        data: filters,
        success: function(data) {
            $('#documents-container').html(data.html);
            updatePagination(data.pagination);
        },
        error: function() {
            showNotification('Failed to load documents', 'error');
        },
        complete: function() {
            isLoading = false;
            hideLoadingSpinner();
        }
    });
}

function clearFilters() {
    $('.filter-checkbox').prop('checked', false);
    $('.filter-select').val('');
    applyFilters();
}

// Charts functionality
function initializeCharts() {
    // Document types chart
    const docTypesCtx = document.getElementById('docTypesChart');
    if (docTypesCtx) {
        loadDocumentTypesChart();
    }
    
    // Activity chart
    const activityCtx = document.getElementById('activityChart');
    if (activityCtx) {
        loadActivityChart();
    }
}

function loadDocumentTypesChart() {
    $.ajax({
        url: '/knowledge/ajax/chart-data/document-types/',
        method: 'GET',
        success: function(data) {
            const ctx = document.getElementById('docTypesChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: [
                            '#4e73df',
                            '#1cc88a',
                            '#36b9cc',
                            '#f6c23e',
                            '#e74a3b',
                            '#858796'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: 'bottom'
                    }
                }
            });
        }
    });
}

function loadActivityChart() {
    $.ajax({
        url: '/knowledge/ajax/chart-data/activity/',
        method: 'GET',
        success: function(data) {
            const ctx = document.getElementById('activityChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Documents Created',
                        data: data.created,
                        borderColor: '#4e73df',
                        backgroundColor: 'rgba(78, 115, 223, 0.1)',
                        fill: true
                    }, {
                        label: 'Documents Viewed',
                        data: data.viewed,
                        borderColor: '#1cc88a',
                        backgroundColor: 'rgba(28, 200, 138, 0.1)',
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    });
}

// Dashboard stats
function loadDashboardStats() {
    $.ajax({
        url: '/knowledge/ajax/dashboard-stats/',
        method: 'GET',
        success: function(data) {
            updateDashboardStats(data);
        },
        error: function() {
            console.error('Failed to load dashboard stats');
        }
    });
}

function updateDashboardStats(stats) {
    $('#total-documents').text(stats.total_documents || 0);
    $('#total-categories').text(stats.total_categories || 0);
    $('#total-views').text(stats.total_views || 0);
    $('#pending-reviews').text(stats.pending_reviews || 0);
}

// AI Processing
function triggerAIProcessing(documentId) {
    $.ajax({
        url: `/knowledge/ai/process/${documentId}/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        success: function(data) {
            if (data.success) {
                showNotification('AI processing started', 'success');
                checkAIProcessingStatus(data.job_id);
            } else {
                showNotification('Failed to start AI processing', 'error');
            }
        },
        error: function() {
            showNotification('Failed to start AI processing', 'error');
        }
    });
}

function checkAIProcessingStatus(jobId) {
    const checkStatus = () => {
        $.ajax({
            url: `/knowledge/ai/status/${jobId}/`,
            method: 'GET',
            success: function(data) {
                if (data.status === 'completed') {
                    showNotification('AI processing completed', 'success');
                    location.reload();
                } else if (data.status === 'failed') {
                    showNotification('AI processing failed', 'error');
                } else {
                    setTimeout(checkStatus, 2000);
                }
            }
        });
    };
    
    setTimeout(checkStatus, 2000);
}

// Event bindings
function bindEvents() {
    // AI processing buttons
    $('.trigger-ai-processing').on('click', function() {
        const documentId = $(this).data('document-id');
        triggerAIProcessing(documentId);
    });
    
    // Infinite scroll
    $(window).on('scroll', function() {
        if ($(window).scrollTop() + $(window).height() >= $(document).height() - 100) {
            loadMoreDocuments();
        }
    });
    
    // Tag selection
    $('.tag-item').on('click', function() {
        $(this).toggleClass('selected');
        applyFilters();
    });
    
    // Bulk actions
    $('.select-all-documents').on('change', function() {
        $('.document-checkbox').prop('checked', $(this).is(':checked'));
    });
    
    $('.bulk-action-btn').on('click', function() {
        const action = $(this).data('action');
        const selectedDocs = $('.document-checkbox:checked').map(function() {
            return $(this).val();
        }).get();
        
        if (selectedDocs.length > 0) {
            performBulkAction(action, selectedDocs);
        } else {
            showNotification('Please select documents first', 'warning');
        }
    });
}

// Utility functions
function getCsrfToken() {
    return $('[name=csrfmiddlewaretoken]').val();
}

function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const notification = $(`
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        </div>
    `);
    
    $('#notifications-container').append(notification);
    
    setTimeout(() => {
        notification.alert('close');
    }, 5000);
}

function showLoadingSpinner() {
    $('#loading-spinner').show();
}

function hideLoadingSpinner() {
    $('#loading-spinner').hide();
}

function initializeTooltips() {
    $('[data-toggle="tooltip"]').tooltip();
}

function loadMoreDocuments() {
    if (isLoading) return;
    
    currentPage++;
    
    $.ajax({
        url: '/knowledge/documents/',
        method: 'GET',
        data: { page: currentPage },
        success: function(data) {
            if (data.html.trim()) {
                $('#documents-container').append(data.html);
            }
        }
    });
}

function performBulkAction(action, documentIds) {
    $.ajax({
        url: `/knowledge/bulk/${action}/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        data: {
            document_ids: documentIds
        },
        success: function(data) {
            if (data.success) {
                showNotification(`Bulk ${action} completed successfully`, 'success');
                location.reload();
            } else {
                showNotification(`Bulk ${action} failed`, 'error');
            }
        },
        error: function() {
            showNotification(`Bulk ${action} failed`, 'error');
        }
    });
}

// Export functions for global access
window.KnowledgeSystem = {
    triggerAIProcessing,
    loadComments,
    applyFilters,
    showNotification
};