// Get username from URL like: dashboard?username=prem
const urlParams = new URLSearchParams(window.location.search);
document.getElementById("usernameDisplay").innerText = urlParams.get("username");
const userId = urlParams.get("user_id");

// ------------------ UPLOAD NOTE ------------------
// Upload a note
async function uploadNote() {
    let data = {
        user_id: userId,
        title: document.getElementById("title").value,
        content: document.getElementById("content").value
    };

    let res = await fetch("/upload_note", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    let result = await res.json();
    document.getElementById("uploadResponse").innerText = result.message || result.error;

    // Reload notes
    loadNotes();
}
// Changed----------------
// Toggle theme function
function toggleTheme() {
    document.body.classList.toggle('dark-mode');

    // Save user preference
    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
}

// Apply saved theme on page load
window.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
    }
});

// Load notes dynamically
async function loadNotes() {
    const res = await fetch("/get_user_notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId })
    });
    const notes = await res.json();
    const container = document.getElementById("notesContainer");
    container.innerHTML = "";

    notes.forEach(note => {
        const card = document.createElement("div");
        card.className = "col-md-4";
        card.innerHTML = `
            <div class="card p-3 shadow h-100">
                <h5>${note.title}</h5>
                <p>${note.content.substring(0, 100)}${note.content.length > 100 ? "..." : ""}</p>
                <button class="btn btn-success me-2 mb-1" onclick="generateNormal(${note.id})">Normal Qs</button>
                <button class="btn btn-warning mb-1" onclick="generateMCQ(${note.id})">MCQs</button>
            </div>
        `;
        container.appendChild(card);
    });
}

// Generate Normal questions
async function generateNormal(noteId) {
    const res = await fetch("/generate_normal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_id: noteId })
    });
    const result = await res.json();
    document.getElementById("outputBox").innerText = JSON.stringify(result, null, 2);
}

// Generate MCQs
async function generateMCQ(noteId) {
    const res = await fetch("/generate_mcq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_id: noteId })
    });
    const result = await res.json();
    document.getElementById("outputBox").innerText = JSON.stringify(result, null, 2);
}