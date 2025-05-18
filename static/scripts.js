
// Toggles the hamburger menu with click

document.querySelector('.hamburger').addEventListener('click', function () {
    var navRight = document.getElementById('navbarRight');
    if (navRight.style.left === "0px") {
        navRight.style.left = "-100%"; // Slide out
    } else {
        navRight.style.left = "0"; // Slide in
    }
});

document.querySelector('.hamburger').addEventListener('click', function () {
    document.getElementById('navbarRight').style.left = "0"; // Slide in
});

document.querySelector('.closebtn').addEventListener('click', function () {
    document.getElementById('navbarRight').style.left = "-100%"; // Slide out
});




// Toggles the dropdown menu with click

const dropBtn = document.getElementById('dropBtn');
if (dropBtn) { // Check if the element actually exists
    const dropdownContent = document.querySelector('.dropdown-content');

    dropBtn.addEventListener('click', function () {
        console.log('clicked');
        if (dropdownContent.style.display === "none") {
            dropdownContent.style.display = "block";
        } else {
            dropdownContent.style.display = "none";
        }
        console.log(dropdownContent);
    });
}

//Toggles flash

export function showToast(type, message) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const bgColor = {
        success: 'bg-green-500',
        warning: 'bg-yellow-500',
        error: 'bg-red-500'
    }[type] || 'bg-blue-500';

    const toast = document.createElement('div');
    toast.className = `${bgColor} text-white px-4 py-2 rounded shadow-md animate-slide-in-right`;
    toast.innerText = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Animasi CSS
const style = document.createElement('style');
style.innerHTML = `
@keyframes slide-in-right {
    0% { transform: translateX(100%); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
}
.animate-slide-in-right {
    animation: slide-in-right 0.3s ease-out;
}
`;
document.head.appendChild(style);

// ===================
// Tambahan otomatis untuk baca flash-messages
// ===================
document.addEventListener("DOMContentLoaded", function () {
    const flashes = document.querySelectorAll("#flash-messages div");
    flashes.forEach(flash => {
        const type = flash.dataset.category;
        const message = flash.dataset.message;
        showToast(type, message);
    });
});

