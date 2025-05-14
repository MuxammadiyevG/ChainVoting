document.addEventListener('DOMContentLoaded', function () {
    // Flash xabarlarni avtomatik yashirish (4 soniyada)
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 500);
        }, 4000);
    });
});
