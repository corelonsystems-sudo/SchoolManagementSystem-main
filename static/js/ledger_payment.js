document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(event) {
        var button = event.target.closest('#ledger-pay-submit');
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        var container = document.getElementById('ledger-pay-form');
        var messageDiv = document.getElementById('ledger-pay-message');
        if (!container) {
            alert('Payment container not found.');
            return;
        }

        var csrfInput = document.getElementById('ledger-pay-csrf');
        if (csrfInput) {
            var token = '';
            var adminCsrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (adminCsrf) {
                token = adminCsrf.value;
            }
            if (!token) {
                var cookie = document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)');
                token = cookie ? cookie.pop() : '';
            }
            csrfInput.value = token;
        }

        button.disabled = true;
        var formData = new FormData();
        container.querySelectorAll('input[name]').forEach(function(input) {
            if (input.name !== 'csrfmiddlewaretoken' && (input.value === '' || input.value === null || typeof input.value === 'undefined')) {
                return;
            }
            formData.append(input.name, input.value);
        });
        var action = container.getAttribute('data-action');

        fetch(action, {
            method: 'POST',
            body: formData,
            headers: {'X-Requested-With': 'XMLHttpRequest'},
            credentials: 'same-origin'
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Server returned ' + response.status);
            }
            return response.json();
        })
        .then(function(data) {
            if (messageDiv) {
                messageDiv.textContent = data.message;
                messageDiv.style.color = data.success ? '#16a34a' : '#dc2626';
            }
            if (data.success) {
                setTimeout(function() {
                    try {
                        var modal = document.getElementById('ledger-pay-modal');
                        if (modal) {
                            modal.style.display = 'none';
                        }
                    } catch (e) {}
                    try {
                        window.onbeforeunload = null;
                        if (window.jQuery) {
                            window.jQuery(window).off('beforeunload');
                        }
                    } catch (e) {}
                    window.location.reload();
                }, 800);
            } else {
                button.disabled = false;
            }
        })
        .catch(function(error) {
            if (messageDiv) {
                messageDiv.textContent = 'Payment failed: ' + error.message;
                messageDiv.style.color = '#dc2626';
            }
            button.disabled = false;
        });
    });
});
