  // Section toggling function
  function showSection(sectionId) {
    const sections = document.querySelectorAll('.content > div');
    sections.forEach(section => section.style.display = 'none');
    document.getElementById(sectionId).style.display = 'block';

    const sectionTitles = {
        'student-list': 'Student List',
        'other-section': 'Other Section',
    };
    document.getElementById('section-title').innerText = sectionTitles[sectionId] || 'Welcome';
}

 // Open the modal and populate the details
function openDetailsModal(index) {
  const student = students[index]; // 'students' is the JSON data passed from Django

  // Populate modal fields
  document.getElementById('modal-photo').src = student.photo || '/static/images/default-avatar.png';
  document.getElementById('modal-name').textContent = `${student.first_name} ${student.last_name}`;
  document.getElementById('modal-degree').textContent = `CERTIFICATE IN ${student.course}`;
  document.getElementById('modal-catalog-year').textContent = student.catalog_year || 'N/A';
  document.getElementById('modal-catalog-yea').textContent = student.catalog_yea || 'N/A';
  document.getElementById('modal-catalog-yeal').textContent = student.catalog_yeal || 'N/A';
  document.getElementById('modal-email').textContent = student.email;
  document.getElementById('modal-phone').textContent = student.phone;
  document.getElementById('modal-subprogram').textContent = student.sub_program || 'Day';
  document.getElementById('modal-registration-status').textContent =
      student.registration_status || 'On Hold';
  document.getElementById('modal-declared-plan').textContent =
      student.declared_grad_plan || 'In-Progress';
  document.getElementById('modal-declared-career').textContent =
      student.declared_career || 'Computer Programmer';

  // Show the modal
  document.getElementById('detailsModal').style.display = 'flex';
}

// Close the modal
document.querySelector('.close').addEventListener('click', () => {
  document.getElementById('detailsModal').style.display = 'none';
});
