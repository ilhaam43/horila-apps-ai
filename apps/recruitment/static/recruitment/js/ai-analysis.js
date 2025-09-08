/**
 * AI Analysis JavaScript Module
 * Handles candidate analysis, workflow automation, and UI interactions
 */

class AIAnalysisManager {
    constructor(candidateId) {
        this.candidateId = candidateId;
        this.analysisCache = new Map();
        this.workflowStatus = new Map();
        this.csrfToken = this.getCSRFToken();
        this.apiBaseUrl = '/recruitment/api/v1';
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadExistingAnalysis();
    }

    bindEvents() {
        // Bind workflow action buttons
        document.querySelectorAll('.btn-workflow').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const workflowType = e.target.dataset.workflow;
                this.triggerWorkflow(workflowType);
            });
        });

        // Bind refresh analysis button
        const refreshBtn = document.getElementById('refresh-analysis');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAnalysis();
            });
        }

        // Bind modal events
        this.bindModalEvents();
    }

    bindModalEvents() {
        const modal = document.getElementById('workflowStatusModal');
        if (modal) {
            modal.addEventListener('show.bs.modal', (e) => {
                const workflowType = e.relatedTarget?.dataset.workflow;
                if (workflowType) {
                    this.showWorkflowStatus(workflowType);
                }
            });
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            console.warn('CSRF token not found');
        }
        return token;
    }

    async loadExistingAnalysis() {
        try {
            this.showLoading('analysis-container');
            
            const response = await fetch(
                `${this.apiBaseUrl}/rag/analysis-status/${this.candidateId}/`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    }
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.has_analysis) {
                    this.displayAnalysis(data.analysis);
                } else {
                    this.startNewAnalysis();
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error loading analysis:', error);
            this.showError('analysis-container', 'Failed to load analysis');
        }
    }

    async startNewAnalysis() {
        try {
            this.showLoading('analysis-container', 'Starting AI analysis...');
            
            const response = await fetch(
                `${this.apiBaseUrl}/rag/analyze-resume/`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        candidate_id: this.candidateId,
                        async_processing: true
                    })
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.task_id) {
                    this.pollTaskStatus(data.task_id);
                } else {
                    this.displayAnalysis(data.analysis);
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error starting analysis:', error);
            this.showError('analysis-container', 'Failed to start analysis');
        }
    }

    async pollTaskStatus(taskId) {
        const maxAttempts = 30;
        let attempts = 0;
        
        const poll = async () => {
            try {
                attempts++;
                
                const response = await fetch(
                    `${this.apiBaseUrl}/task-status/${taskId}/`,
                    {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        }
                    }
                );

                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.status === 'SUCCESS') {
                        this.displayAnalysis(data.result);
                        return;
                    } else if (data.status === 'FAILURE') {
                        throw new Error(data.error || 'Analysis failed');
                    } else if (data.status === 'PENDING' && attempts < maxAttempts) {
                        setTimeout(poll, 2000); // Poll every 2 seconds
                        return;
                    }
                }
                
                if (attempts >= maxAttempts) {
                    throw new Error('Analysis timeout');
                }
                
            } catch (error) {
                console.error('Error polling task status:', error);
                this.showError('analysis-container', 'Analysis failed');
            }
        };
        
        poll();
    }

    displayAnalysis(analysis) {
        this.hideLoading('analysis-container');
        
        // Cache the analysis
        this.analysisCache.set(this.candidateId, analysis);
        
        // Display similarity score
        this.displaySimilarityScore(analysis.similarity_score, analysis.confidence_level);
        
        // Display recommendation
        this.displayRecommendation(analysis.recommendation);
        
        // Display skills analysis
        this.displaySkillsAnalysis(analysis.skills_analysis);
        
        // Display sentiment analysis
        this.displaySentimentAnalysis(analysis.sentiment_analysis);
        
        // Display extracted entities
        this.displayExtractedEntities(analysis.extracted_entities);
        
        // Add animation classes
        this.addAnimations();
    }

    displaySimilarityScore(score, confidence) {
        const scoreElement = document.getElementById('similarity-score');
        const confidenceElement = document.getElementById('confidence-level');
        
        if (scoreElement) {
            scoreElement.textContent = `${Math.round(score * 100)}%`;
            scoreElement.parentElement.classList.add('fade-in');
        }
        
        if (confidenceElement) {
            confidenceElement.textContent = `${Math.round(confidence * 100)}%`;
            confidenceElement.parentElement.classList.add('fade-in');
        }
        
        // Update progress bars
        this.updateProgressBar('score-progress', score);
        this.updateProgressBar('confidence-progress', confidence);
    }

    displayRecommendation(recommendation) {
        const recommendationElement = document.getElementById('ai-recommendation');
        if (recommendationElement && recommendation) {
            const badgeClass = this.getRecommendationClass(recommendation.decision);
            recommendationElement.innerHTML = `
                <span class="recommendation-badge ${badgeClass}">
                    ${recommendation.decision}
                </span>
                <p class="mt-2">${recommendation.reasoning || ''}</p>
            `;
            recommendationElement.classList.add('slide-in-right');
        }
    }

    displaySkillsAnalysis(skillsAnalysis) {
        if (!skillsAnalysis) return;
        
        // Display matching skills
        const matchingContainer = document.getElementById('matching-skills');
        if (matchingContainer && skillsAnalysis.matching_skills) {
            matchingContainer.innerHTML = skillsAnalysis.matching_skills
                .map(skill => `
                    <div class="skill-item">
                        <i class="fas fa-check-circle text-success"></i>
                        <span>${skill}</span>
                    </div>
                `).join('');
            matchingContainer.classList.add('slide-in-left');
        }
        
        // Display missing skills
        const missingContainer = document.getElementById('missing-skills');
        if (missingContainer && skillsAnalysis.missing_skills) {
            missingContainer.innerHTML = skillsAnalysis.missing_skills
                .map(skill => `
                    <div class="skill-item missing-skill">
                        <i class="fas fa-times-circle text-danger"></i>
                        <span>${skill}</span>
                    </div>
                `).join('');
            missingContainer.classList.add('slide-in-right');
        }
    }

    displaySentimentAnalysis(sentimentAnalysis) {
        const sentimentContainer = document.getElementById('sentiment-analysis');
        if (sentimentContainer && sentimentAnalysis) {
            const iconClass = this.getSentimentIcon(sentimentAnalysis.label);
            sentimentContainer.innerHTML = `
                <div class="sentiment-indicator sentiment-${sentimentAnalysis.label.toLowerCase()}">
                    <i class="fas fa-${iconClass}"></i>
                    <div>
                        <strong>${sentimentAnalysis.label}</strong> (${Math.round(sentimentAnalysis.score * 100)}%)
                        <br><small class="text-muted">${sentimentAnalysis.explanation || ''}</small>
                    </div>
                </div>
            `;
            sentimentContainer.classList.add('fade-in');
        }
    }

    displayExtractedEntities(entities) {
        const entitiesContainer = document.getElementById('extracted-entities');
        if (entitiesContainer && entities) {
            const entitiesHtml = Object.entries(entities)
                .map(([type, values]) => {
                    if (Array.isArray(values) && values.length > 0) {
                        return `
                            <div class="entity-group mb-3">
                                <h6 class="text-muted text-uppercase">${type}</h6>
                                <div>
                                    ${values.map(value => `<span class="entity-tag">${value}</span>`).join('')}
                                </div>
                            </div>
                        `;
                    }
                    return '';
                })
                .filter(html => html)
                .join('');
            
            entitiesContainer.innerHTML = entitiesHtml || '<p class="text-muted">No entities extracted</p>';
            entitiesContainer.classList.add('fade-in');
        }
    }

    async triggerWorkflow(workflowType) {
        try {
            const button = document.querySelector(`[data-workflow="${workflowType}"]`);
            if (button) {
                button.disabled = true;
                button.innerHTML = `<span class="loading-spinner"></span> Processing...`;
            }
            
            const response = await fetch(
                `${this.apiBaseUrl}/workflow/trigger/`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        candidate_id: this.candidateId,
                        workflow_type: workflowType
                    })
                }
            );

            if (response.ok) {
                const data = await response.json();
                this.workflowStatus.set(workflowType, data);
                this.showWorkflowSuccess(workflowType, data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error triggering workflow:', error);
            this.showWorkflowError(workflowType, error.message);
        } finally {
            // Reset button
            const button = document.querySelector(`[data-workflow="${workflowType}"]`);
            if (button) {
                button.disabled = false;
                button.innerHTML = this.getWorkflowButtonText(workflowType);
            }
        }
    }

    showWorkflowSuccess(workflowType, data) {
        const toast = this.createToast(
            'success',
            'Workflow Triggered',
            `${workflowType} workflow has been started successfully.`
        );
        this.showToast(toast);
    }

    showWorkflowError(workflowType, error) {
        const toast = this.createToast(
            'error',
            'Workflow Failed',
            `Failed to trigger ${workflowType} workflow: ${error}`
        );
        this.showToast(toast);
    }

    async refreshAnalysis() {
        // Clear cache
        this.analysisCache.delete(this.candidateId);
        
        // Start new analysis
        await this.startNewAnalysis();
    }

    // Utility methods
    updateProgressBar(elementId, value) {
        const progressBar = document.getElementById(elementId);
        if (progressBar) {
            const percentage = Math.round(value * 100);
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
    }

    getRecommendationClass(decision) {
        const classMap = {
            'highly_recommended': 'recommendation-highly-recommended',
            'recommended': 'recommendation-recommended',
            'consider': 'recommendation-consider',
            'not_recommended': 'recommendation-not-recommended'
        };
        return classMap[decision] || 'recommendation-consider';
    }

    getSentimentIcon(sentiment) {
        const iconMap = {
            'positive': 'smile',
            'neutral': 'meh',
            'negative': 'frown'
        };
        return iconMap[sentiment.toLowerCase()] || 'meh';
    }

    getWorkflowButtonText(workflowType) {
        const textMap = {
            'screening': '<i class="fas fa-search"></i> Start Screening',
            'interview': '<i class="fas fa-calendar"></i> Schedule Interview',
            'notification': '<i class="fas fa-bell"></i> Send Notification',
            'hiring': '<i class="fas fa-user-check"></i> Hiring Decision'
        };
        return textMap[workflowType] || `<i class="fas fa-play"></i> ${workflowType}`;
    }

    showLoading(containerId, message = 'Loading...') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="loading-spinner mb-3"></div>
                    <p class="text-muted">${message}</p>
                </div>
            `;
        }
    }

    hideLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }
    }

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Error:</strong> ${message}
                    <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="location.reload()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    addAnimations() {
        // Add staggered animations to elements
        const elements = document.querySelectorAll('.analysis-section');
        elements.forEach((el, index) => {
            setTimeout(() => {
                el.classList.add('fade-in');
            }, index * 200);
        });
    }

    createToast(type, title, message) {
        const toastId = `toast-${Date.now()}`;
        const bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
        
        return `
            <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
    }

    showToast(toastHtml) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }
        
        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Initialize and show toast
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Initialize AI Analysis Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const candidateId = document.querySelector('[data-candidate-id]')?.dataset.candidateId;
    if (candidateId) {
        window.aiAnalysisManager = new AIAnalysisManager(candidateId);
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIAnalysisManager;
}