// Custom JavaScript for Fintech Admin

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize all custom features
    initAnimations();
    initRealTimeUpdates();
    initInteractiveFeatures();
    initDataTables();
    initCharts();
    initNotifications();
    
});

// Animation Functions
function initAnimations() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card, .info-box');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Add hover effects to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px) scale(1.02)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

// Real-time Updates
function initRealTimeUpdates() {
    // Update dashboard widgets every 30 seconds
    setInterval(updateDashboardData, 30000);
    
    // Update system health every 60 seconds
    setInterval(updateSystemHealth, 60000);
}

function updateDashboardData() {
    fetch('/accounts/admin/api/dashboard-data/')
        .then(response => response.json())
        .then(data => {
            // Update user statistics
            const userStats = document.querySelectorAll('.info-box-number');
            if (userStats.length >= 4) {
                userStats[0].textContent = data.users.total;
                userStats[1].textContent = data.users.verified;
                userStats[2].textContent = data.users.new_today;
            }
            
            // Add update indicator
            showUpdateIndicator();
        })
        .catch(error => console.log('Dashboard update failed:', error));
}

function updateSystemHealth() {
    // Simulate system health updates
    const healthIndicators = document.querySelectorAll('.system-health-indicator');
    healthIndicators.forEach(indicator => {
        const status = Math.random() > 0.1 ? 'healthy' : 'warning';
        indicator.className = `system-health-indicator ${status}`;
        indicator.textContent = status.toUpperCase();
    });
}

function showUpdateIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'update-indicator fade-in';
    indicator.innerHTML = '<i class="fas fa-sync-alt"></i> Updated';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #27ae60;
        color: white;
        padding: 10px 15px;
        border-radius: 20px;
        z-index: 9999;
        font-size: 0.9rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    `;
    
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        indicator.style.opacity = '0';
        setTimeout(() => indicator.remove(), 500);
    }, 2000);
}

// Interactive Features
function initInteractiveFeatures() {
    // Add search functionality
    initSearch();
    
    // Add filter functionality
    initFilters();
    
    // Add export functionality
    initExport();
    
    // Add bulk actions
    initBulkActions();
}

function initSearch() {
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
}

function initFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filterType = this.dataset.filter;
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                if (filterType === 'all') {
                    row.style.display = '';
                } else {
                    const status = row.querySelector('.status-badge');
                    if (status && status.textContent.toLowerCase() === filterType) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
            
            // Update active filter button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function initExport() {
    const exportButtons = document.querySelectorAll('.export-btn');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const format = this.dataset.format || 'csv';
            const table = document.querySelector('table');
            
            if (table) {
                exportTable(table, format);
            }
        });
    });
}

function exportTable(table, format) {
    const rows = Array.from(table.querySelectorAll('tr'));
    let csvContent = '';
    
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        const rowData = cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
        csvContent += rowData + '\n';
    });
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

function initBulkActions() {
    const selectAllCheckbox = document.querySelector('.select-all');
    const actionButtons = document.querySelectorAll('.bulk-action-btn');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('tbody input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionButtons();
        });
    }
    
    // Individual checkbox change
    document.addEventListener('change', function(e) {
        if (e.target.type === 'checkbox' && e.target.closest('tbody')) {
            updateBulkActionButtons();
        }
    });
    
    // Bulk action buttons
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.action;
            const selectedRows = document.querySelectorAll('tbody input[type="checkbox"]:checked');
            
            if (selectedRows.length === 0) {
                showNotification('Please select items to perform bulk action', 'warning');
                return;
            }
            
            performBulkAction(action, selectedRows);
        });
    });
}

function updateBulkActionButtons() {
    const selectedCount = document.querySelectorAll('tbody input[type="checkbox"]:checked').length;
    const actionButtons = document.querySelectorAll('.bulk-action-btn');
    
    actionButtons.forEach(button => {
        button.disabled = selectedCount === 0;
        button.textContent = button.textContent.replace(/\(\d+\)/, `(${selectedCount})`);
    });
}

function performBulkAction(action, selectedRows) {
    const ids = Array.from(selectedRows).map(checkbox => checkbox.value);
    
    // Show confirmation dialog
    if (confirm(`Are you sure you want to ${action} ${ids.length} selected items?`)) {
        // Simulate API call
        showNotification(`Bulk ${action} action completed for ${ids.length} items`, 'success');
        
        // Update UI
        selectedRows.forEach(checkbox => {
            const row = checkbox.closest('tr');
            if (action === 'delete') {
                row.remove();
            } else if (action === 'verify') {
                const statusCell = row.querySelector('.status-badge');
                if (statusCell) {
                    statusCell.textContent = 'Verified';
                    statusCell.className = 'status-badge badge badge-success';
                }
            }
        });
        
        updateBulkActionButtons();
    }
}

// Data Tables Enhancement
function initDataTables() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        // Add sorting functionality
        addTableSorting(table);
        
        // Add pagination
        addTablePagination(table);
        
        // Add responsive features
        makeTableResponsive(table);
    });
}

function addTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable]');
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const column = Array.from(this.parentNode.children).indexOf(this);
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const isAscending = this.classList.contains('sort-asc');
            
            // Sort rows
            rows.sort((a, b) => {
                const aValue = a.children[column].textContent;
                const bValue = b.children[column].textContent;
                
                if (isAscending) {
                    return bValue.localeCompare(aValue);
                } else {
                    return aValue.localeCompare(bValue);
                }
            });
            
            // Update table
            const tbody = table.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));
            
            // Update header classes
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            this.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
        });
    });
}

function addTablePagination(table) {
    const rows = table.querySelectorAll('tbody tr');
    const rowsPerPage = 10;
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    
    if (totalPages > 1) {
        const pagination = createPagination(totalPages);
        table.parentNode.appendChild(pagination);
        
        showPage(1, rows, rowsPerPage);
        
        // Add pagination event listeners
        pagination.addEventListener('click', function(e) {
            if (e.target.classList.contains('page-link')) {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                showPage(page, rows, rowsPerPage);
                
                // Update active page
                pagination.querySelectorAll('.page-link').forEach(link => {
                    link.parentNode.classList.remove('active');
                });
                e.target.parentNode.classList.add('active');
            }
        });
    }
}

function createPagination(totalPages) {
    const pagination = document.createElement('nav');
    pagination.innerHTML = `
        <ul class="pagination justify-content-center">
            <li class="page-item">
                <a class="page-link" href="#" data-page="1">First</a>
            </li>
            ${Array.from({length: totalPages}, (_, i) => i + 1).map(page => `
                <li class="page-item ${page === 1 ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${page}">${page}</a>
                </li>
            `).join('')}
            <li class="page-item">
                <a class="page-link" href="#" data-page="${totalPages}">Last</a>
            </li>
        </ul>
    `;
    return pagination;
}

function showPage(page, rows, rowsPerPage) {
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    
    rows.forEach((row, index) => {
        row.style.display = (index >= start && index < end) ? '' : 'none';
    });
}

function makeTableResponsive(table) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-responsive';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
}

// Charts and Visualizations
function initCharts() {
    // Initialize any chart libraries if available
    if (typeof Chart !== 'undefined') {
        createDashboardCharts();
    }
}

function createDashboardCharts() {
    // User growth chart
    const userGrowthCtx = document.getElementById('userGrowthChart');
    if (userGrowthCtx) {
        new Chart(userGrowthCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'User Growth',
                    data: [65, 78, 90, 105, 125, 140],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
    
    // Transaction volume chart
    const transactionCtx = document.getElementById('transactionChart');
    if (transactionCtx) {
        new Chart(transactionCtx, {
            type: 'bar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Transaction Volume',
                    data: [12000, 19000, 15000, 25000, 22000, 30000, 28000],
                    backgroundColor: '#3498db'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
}

// Notifications System
function initNotifications() {
    // Create notification container
    const notificationContainer = document.createElement('div');
    notificationContainer.id = 'notification-container';
    notificationContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        max-width: 400px;
    `;
    document.body.appendChild(notificationContainer);
}

function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} fade-in`;
    notification.innerHTML = `
        <button type="button" class="close" data-dismiss="alert">&times;</button>
        ${message}
    `;
    
    const container = document.getElementById('notification-container');
    container.appendChild(notification);
    
    // Auto remove after duration
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 500);
    }, duration);
    
    // Manual close
    notification.querySelector('.close').addEventListener('click', function() {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 500);
    });
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Ctrl/Cmd + E for export
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        const exportBtn = document.querySelector('.export-btn');
        if (exportBtn) {
            exportBtn.click();
        }
    }
});

// Performance monitoring
function monitorPerformance() {
    // Monitor page load time
    window.addEventListener('load', function() {
        const loadTime = performance.now();
        console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
        
        if (loadTime > 3000) {
            showNotification('Page load time is slow. Consider optimizing.', 'warning');
        }
    });
    
    // Monitor API response times
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const start = performance.now();
        return originalFetch.apply(this, args).then(response => {
            const duration = performance.now() - start;
            if (duration > 2000) {
                console.warn(`Slow API call: ${duration.toFixed(2)}ms`);
            }
            return response;
        });
    };
}

// Initialize performance monitoring
monitorPerformance(); 