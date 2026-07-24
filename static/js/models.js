function showAcademicInfo() {
    const modalBody = document.getElementById("modal-body");
    modalBody.innerHTML = `
        <h3>Academic Information</h3>
        <div class="details-grid">
            <p><strong>Sub-Program:</strong> Bachelor of Science</p>
            <p><strong>GPA:</strong> 3.75</p>
            <p><strong>Major:</strong> Computer Science</p>
            <p><strong>Enrollment Year:</strong> 2020</p>
        </div>`;
}

function showPayments() {
    const modalBody = document.getElementById("modal-body");
    modalBody.innerHTML = `
        <h3>Payment Details</h3>
        <div class="details-grid">
            <p><strong>Total Fees Paid:</strong> $12,000</p>
            <p><strong>Outstanding Balance:</strong> $2,000</p>
            <p><strong>Last Payment Date:</strong> 15th January 2025</p>
            <p><strong>Scholarship:</strong> None</p>
        </div>`;
}

function showParentsDetails() {
    const modalBody = document.getElementById("modal-body");
    modalBody.innerHTML = `
        <h3>Parents Details</h3>
        <div class="details-grid">
            <p><strong>Father's Name:</strong> John Graham</p>
            <p><strong>Father's Phone:</strong> +1 555-123-4567</p>
            <p><strong>Mother's Name:</strong> Jane Graham</p>
            <p><strong>Mother's Phone:</strong> +1 555-987-6543</p>
        </div>`;
}

function showDocuments() {
    const modalBody = document.getElementById("modal-body");
    modalBody.innerHTML = `
        <h3>Student Documents</h3>
        <div class="details-grid">
            <p><strong>Transcript:</strong> <a href="#">Download</a></p>
            <p><strong>ID Copy:</strong> <a href="#">Download</a></p>
            <p><strong>Enrollment Letter:</strong> <a href="#">Download</a></p>
            <p><strong>Other Documents:</strong> <a href="#">Download</a></p>
        </div>`;
}
