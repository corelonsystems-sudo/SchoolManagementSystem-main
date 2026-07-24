(function () {
    'use strict';

    function ensureModal() {
        if (document.getElementById('course-fee-modal-overlay')) return;
        var overlay = document.createElement('div');
        overlay.id = 'course-fee-modal-overlay';
        overlay.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:10000;';
        var modal = document.createElement('div');
        modal.id = 'course-fee-modal';
        modal.style.cssText = 'display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:8px;box-shadow:0 8px 30px rgba(0,0,0,0.3);width:80vw;height:80vh;z-index:10001;overflow:hidden;';
        var header = document.createElement('div');
        header.style.cssText = 'background:#1c4a7a;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;';
        var title = document.createElement('h3');
        title.id = 'course-fee-modal-title';
        title.style.cssText = 'margin:0;font-size:16px;font-weight:600;';
        title.textContent = 'Course Fee Details';
        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.style.cssText = 'background:none;border:none;color:#fff;font-size:24px;cursor:pointer;line-height:1;';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = closeCourseFeeModal;
        header.appendChild(title);
        header.appendChild(closeBtn);
        var iframe = document.createElement('iframe');
        iframe.id = 'course-fee-modal-iframe';
        iframe.style.cssText = 'width:100%;height:calc(100% - 48px);border:none;';
        iframe.setAttribute('scrolling', 'auto');
        modal.appendChild(header);
        modal.appendChild(iframe);
        overlay.appendChild(modal);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) closeCourseFeeModal();
        });
        document.body.appendChild(overlay);
    }

    function openCourseFeeModal(url, title) {
        ensureModal();
        var overlay = document.getElementById('course-fee-modal-overlay');
        var modal = document.getElementById('course-fee-modal');
        var iframe = document.getElementById('course-fee-modal-iframe');
        var titleEl = document.getElementById('course-fee-modal-title');
        if (title) titleEl.textContent = title;
        iframe.src = url + (url.indexOf('?') === -1 ? '?' : '&') + '_popup=1';
        overlay.style.display = 'block';
        modal.style.display = 'block';
    }

    function closeCourseFeeModal() {
        var overlay = document.getElementById('course-fee-modal-overlay');
        var modal = document.getElementById('course-fee-modal');
        var iframe = document.getElementById('course-fee-modal-iframe');
        if (overlay) overlay.style.display = 'none';
        if (modal) modal.style.display = 'none';
        if (iframe) iframe.src = '';
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.course-fee-detail-link').forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                var title = this.getAttribute('data-title') || 'Course Fee Details';
                openCourseFeeModal(this.getAttribute('href'), title);
            });
        });
    });

    window.closeCourseFeeModal = closeCourseFeeModal;
})();
