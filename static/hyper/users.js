let allUsers = [];

function initUserManagementPage() {
    loadUsers();
    initSearch();
}

function loadUsers() {
    const tbody = document.getElementById("user-table-body");
    if (!tbody) return;

    fetch("/api/users")
        .then(res => res.json())
        .then(users => {
            allUsers = users;
            renderUsers(users);
        })
        .catch(err => console.error("Failed to load users:", err));
}

function renderUsers(users) {
    const tbody = document.getElementById("user-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";

    users.forEach(user => {
        const fullname = `${user.firstname} ${user.middlename ?? ""} ${user.lastname}`.trim();

        const row = `
            <tr>
                <td>${user.staffid}</td>
                <td>${user.username}</td>
                <td>${fullname}</td>
                <td>
                    <a href="#" onclick="editUser(${user.userid})"><i class="mdi mdi-pencil"></i></a>
                    <a href="#" onclick="deleteUser(${user.userid})"><i class="mdi mdi-delete"></i></a>
                </td>
            </tr>
        `;
        tbody.insertAdjacentHTML("beforeend", row);
    });
}

function initSearch() {
    const searchInput = document.getElementById("user-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", () => {
        const term = searchInput.value.toLowerCase();

        const filtered = allUsers.filter(u =>
            u.staffid.toLowerCase().includes(term) ||
            u.firstname.toLowerCase().includes(term) ||
            (u.middlename && u.middlename.toLowerCase().includes(term)) ||
            u.lastname.toLowerCase().includes(term) || u.username.toLowerCase().includes(term)
        );

        renderUsers(filtered);
    });
}
searchInput.addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        const event = new Event("input");
        searchInput.dispatchEvent(event);
    }
});


function editUser(id) {
    alert("Edit user: " + id);
}

function deleteUser(id) {
    alert("Delete user: " + id);
}
