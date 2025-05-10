/**
 * Blockchain Ovoz Berish Tizimi uchun asosiy JavaScript fayli
 */

document.addEventListener('DOMContentLoaded', function() {
    // Flash xabarlarini yashirish uchun
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Ethereum manzili ko'rinishi uchun
    const ethAddresses = document.querySelectorAll('.eth-address-display');
    ethAddresses.forEach(address => {
        const fullAddress = address.getAttribute('data-address');
        if (fullAddress && fullAddress.length > 10) {
            address.textContent = formatAddress(fullAddress);
            
            // To'liq manzilni ko'rsatish uchun hover effekti
            address.addEventListener('mouseenter', function() {
                this.textContent = fullAddress;
            });
            
            address.addEventListener('mouseleave', function() {
                this.textContent = formatAddress(fullAddress);
            });
        }
    });
    
    // Ovoz berish formasi uchun validatsiya
    const voteForm = document.getElementById('vote-form');
    if (voteForm) {
        voteForm.addEventListener('submit', function(e) {
            const privateKey = document.getElementById('private-key').value;
            if (!privateKey || !privateKey.startsWith('0x')) {
                e.preventDefault();
                showAlert('Yaroqli ETH private key kiriting (0x bilan boshlanishi kerak)', 'danger');
            }
        });
    }
    
    // Saylov natijalarini ko'rsatish uchun grafiklar
    const resultsChart = document.getElementById('results-chart');
    if (resultsChart && window.votingData) {
        renderResultsChart(window.votingData);
    }
    
    // Admin panel uchun kandidat qo'shish formasi
    const addCandidateForm = document.getElementById('add-candidate-form');
    if (addCandidateForm) {
        addCandidateForm.addEventListener('submit', function(e) {
            const name = document.getElementById('candidate-name').value;
            if (!name.trim()) {
                e.preventDefault();
                showAlert('Nomzod nomini kiriting', 'danger');
            }
        });
    }
    
    // Admin panelda saylov vaqtini tekshirish
    const electionForm = document.getElementById('election-form');
    if (electionForm) {
        electionForm.addEventListener('submit', function(e) {
            const startDate = new Date(document.getElementById('start-date').value);
            const endDate = new Date(document.getElementById('end-date').value);
            
            if (endDate <= startDate) {
                e.preventDefault();
                showAlert('Tugash sanasi boshlanish sanasidan keyin bo\'lishi kerak', 'danger');
            }
        });
    }
});

/**
 * Ethereum manzilini formatlash
 * @param {string} address - Ethereum manzili
 * @returns {string} Formatlangan manzil
 */
function formatAddress(address) {
    if (!address || address.length < 10) return address;
    return address.substring(0, 6) + '...' + address.substring(address.length - 4);
}

/**
 * Xabar ko'rsatish
 * @param {string} message - Xabar matni
 * @param {string} type - Xabar turi (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // 5 soniyadan keyin o'chirish
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

/**
 * Natijalar grafiklarini yaratish
 * @param {Array} data - Nomzodlar va ovozlar ma'lumotlari
 */
function renderResultsChart(data) {
    const ctx = document.getElementById('results-chart').getContext('2d');
    
    // Nomzod nomlari va ovozlarni ajratish
    const labels = data.map(item => item.name);
    const votes = data.map(item => item.votes);
    
    // Tasodifiy ranglarni generatsiya qilish
    const colors = data.map(() => {
        const r = Math.floor(Math.random() * 200);
        const g = Math.floor(Math.random() * 200);
        const b = Math.floor(Math.random() * 200);
        return `rgba(${r}, ${g}, ${b}, 0.7)`;
    });
    
    // Chart.js bilan grafikni chizish
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Ovozlar soni',
                data: votes,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.7', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    precision: 0,
                    stepSize: 1
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Saylov natijalari'
                }
            }
        }
    });
    
    // Pie chart ham qo'shish
    const pieCtx = document.getElementById('results-pie-chart').getContext('2d');
    new Chart(pieCtx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: votes,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: 'Ovozlar taqsimoti'
                }
            }
        }
    });
}