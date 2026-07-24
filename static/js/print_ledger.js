document.addEventListener('DOMContentLoaded', function () {
    const printButton = document.querySelector('.print-button');
    if (printButton) {
        printButton.addEventListener('click', function () {
            window.print();  // This triggers the print dialog
        });
    }
});
