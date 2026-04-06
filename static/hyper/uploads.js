
function initUploads() {

  /**
 * UI References
 */
const ppiBody = document.querySelector("#povertyIndexTables tbody");
const paginationControls = document.getElementById("paginationControls");
const rowsPerPageSelect = document.getElementById("rowsPerPage");
const tableInfo = document.getElementById("tableInfo");
const searchInput = document.getElementById("tableSearch"); 
const batchFileInput = document.getElementById("batchFileInput");
const uploadBtn = document.getElementById("uploadBtn");

/**
 * State Management
 */
let currentPage = 1;
let rowsPerPage = parseInt(rowsPerPageSelect.value);
let fullData = [];
let filteredData = [];

/**
 * 1. Data Fetching
 */
async function loadTables() {
    ppiBody.innerHTML = `
        <tr>
            <td colspan="7" class="table-loading">
                <div class="spinner"></div>
            </td>
        </tr>`;

    try {
        const response = await fetch('/api/uploads/batches');
        const result = await response.json();

        if (result.success) {
            fullData = result.data || [];
            filteredData = [...fullData]; 
            currentPage = 1;
            renderTable();
        } else {
            throw new Error("API Failure");
        }
    } catch (error) {
        ppiBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger p-4">Error loading data.</td></tr>`;
    }
}

/**
 * 2. CSV Upload Logic
 * Endpoint: /api/uploads/csv
 */
uploadBtn.addEventListener("click", async () => {
    const file = batchFileInput.files[0];

    // Basic Validation
    if (!file) {
        alert("Please select a file first.");
        return;
    }

    // Strict CSV Validation (Client-side)
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.csv')) {
        alert("Invalid file format. Please upload a .csv file.");
        batchFileInput.value = ""; // Clear the input
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    // Set UI to loading state
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Uploading...`;

    try {
        const response = await fetch('/api/uploads/csv', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            alert("File uploaded successfully!");
            batchFileInput.value = ""; // Reset file input
            loadTables(); // Refresh the table to show the new batch
        } else {
            alert("Upload failed: " + (result.message || "Unknown error"));
        }
    } catch (error) {
        console.error("Upload error:", error);
        alert("A server error occurred during the upload.");
    } finally {
        // Reset UI state
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = "Upload";
    }
});

/**
 * 3. Table Rendering
 */
function renderTable() {
    ppiBody.innerHTML = "";

    if (!filteredData.length) {
        ppiBody.innerHTML = `<tr><td colspan="7" class="text-center p-4">No records found.</td></tr>`;
        tableInfo.innerHTML = "Showing 0 to 0 of 0 entries";
        paginationControls.innerHTML = "";
        return;
    }

    const start = (currentPage - 1) * rowsPerPage;
    const end = Math.min(start + rowsPerPage, filteredData.length);
    const pageData = filteredData.slice(start, end);

    pageData.forEach(row => {
        const date = new Date(row.uploadedAt).toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric', 
            hour: '2-digit', minute: '2-digit'
        });

        ppiBody.insertAdjacentHTML("beforeend", `
            <tr>
                <td>${row.batchId}</td>
                <td class="text-center"><strong>${row.fileName}</strong></td>
                <td class="text-center">${row.clientCount || '-'}</td> 
                <td class="text-center">${row.totalRows.toLocaleString()}</td>
                <td class="text-center">${date}</td>
                <td class="text-center"><span class="badge bg-success">Completed</span></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-secondary py-0" onclick="viewDetails('${row.batchId}')">View</button>
                </td>
            </tr>
        `);
    });

    tableInfo.innerHTML = `Showing ${start + 1} to ${end} of ${filteredData.length} entries`;
    renderPagination();
}

/**
 * 4. Pagination & Search Listeners
 */
function renderPagination() {
    const totalPages = Math.ceil(filteredData.length / rowsPerPage);
    if (totalPages <= 1) {
        paginationControls.innerHTML = "";
        return;
    }

    let buttons = `<button class="btn btn-sm btn-light me-1" ${currentPage === 1 ? "disabled" : ""} onclick="changePage(${currentPage - 1})">«</button>`;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            const activeClass = i === currentPage ? 'btn-crimson text-white' : 'btn-light';
            buttons += `<button class="btn btn-sm ${activeClass} me-1" onclick="changePage(${i})">${i}</button>`;
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            buttons += `<span class="me-1">...</span>`;
        }
    }

    buttons += `<button class="btn btn-sm btn-light" ${currentPage === totalPages ? "disabled" : ""} onclick="changePage(${currentPage + 1})">»</button>`;
    paginationControls.innerHTML = buttons;
}

searchInput.addEventListener("input", function(e) {
    const term = e.target.value.toLowerCase();
    filteredData = fullData.filter(item => 
        (item.fileName && item.fileName.toLowerCase().includes(term)) || 
        (item.batchId && item.batchId.toString().toLowerCase().includes(term))
    );
    currentPage = 1;
    renderTable();
});

window.changePage = function(page) {
    currentPage = page;
    renderTable();
}

rowsPerPageSelect.addEventListener("change", function () {
    rowsPerPage = parseInt(this.value);
    currentPage = 1;
    renderTable();
});

window.viewDetails = function(id) {
    console.log("Viewing details for batch:", id);
}

// Start the app
loadTables();

}

    // Dropzone.autoDiscover = false;

    // new Dropzone("#dropzonePPI", {
    //     url: "/ppi/upload",
    //     maxFilesize: 10,
    //     acceptedFiles: ".csv",
    //     previewsContainer: "#previewsPPI",
    //     previewTemplate: document.querySelector("#previewTemplatePPI").innerHTML,
    //     dictInvalidFileType: "Only CSV files are allowed",
    //     success: function(file, response) {
    //         const progress = file.previewElement.querySelector(".progress");
    //         const successMsg = file.previewElement.querySelector("[data-dz-success-message]");
    //         const thumbnail = file.previewElement.querySelector("[data-dz-thumbnail]");

    //         if(progress){
    //             progress.style.transition = "opacity 0.5s ease";
    //             progress.style.opacity = 0;
    //             setTimeout(() => {
    //                 progress.style.display = "none";

    //                 successMsg.innerText = "Success";
    //                 successMsg.style.fontWeight = "600";

    //                 if(thumbnail){
    //                     thumbnail.src = "/static/hyper/image/csv.png";
    //                 }
    //             }, 500);
    //         }
    //     },
    //     error: function(file, response) {
    //         let message = typeof response === "string" ? response : response.message;
    //         file.previewElement.querySelector("[data-dz-error-message]").innerText = message;
    //     },
    //     init: function() {
    //         this.on("dragover", () => this.element.classList.add("border-primary", "shadow-sm"));
    //         this.on("dragleave", () => this.element.classList.remove("border-primary", "shadow-sm"));
    //     }
    // });



// function initScholarshipUploads() {

//     Dropzone.autoDiscover = false;

//     new Dropzone("#myAwesomeDropzone1", {
//         url: "/scholarship_upload",                
//         maxFilesize: 10,               
//         acceptedFiles: ".csv",         
//         uploadMultiple: false,
//         addRemoveLinks: false,
//         previewsContainer: "#file-previews1",
//         previewTemplate: document.querySelector("#uploadPreviewTemplate1").innerHTML,
//         dictInvalidFileType: "Only CSV files are allowed."  
//     });
// }


// function initAtriskUploads() {

//     Dropzone.autoDiscover = false;

//     new Dropzone("#myAwesomeDropzone2", {
//         url: "/atrisk_upload",                
//         maxFilesize: 10,               
//         acceptedFiles: ".csv",         
//         uploadMultiple: false,
//         addRemoveLinks: false,
//         previewsContainer: "#file-previews2",
//         previewTemplate: document.querySelector("#uploadPreviewTemplate2").innerHTML,
//         dictInvalidFileType: "Only CSV files are allowed."  
//     });
// }
