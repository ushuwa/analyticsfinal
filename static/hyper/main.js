// Logout
document.getElementById("logoutBtn").onclick = async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
};

// MAIN: dynamic page loader
async function navigate(event, urlPath, pageFile, element) {
    if (event) event.preventDefault();

    try {
        const res = await fetch('/pages/' + pageFile);
        if (!res.ok) throw new Error("Page not found: " + pageFile);

        const html = await res.text();
        document.getElementById("mainContent").innerHTML = html;

        if (pageFile === "dashboard.html") {   // or whatever page contains graphs
            setTimeout(() => {
                if (typeof initDashboard === "function") {
                    initDashboard();
                } else {
                    console.error("initDashboard() missing. Add it inside dashboard.js");
                }
            }, 50);
        }

        if (pageFile === "cardprograms.html") {
            // Run after innerHTML
            if (typeof initCMRIPrograms === "function") {
                initCMRIPrograms();
            } else {
                console.error("initCMRIPrograms() missing.");
            }
        }

        if (pageFile === "povertyinsights.html") {
            // Run after innerHTML
            if (typeof initPovertyInsights === "function") {
                initPovertyInsights();
            } else {
                console.error("initPovertyInsights() missing.");
            }
        }

        // ⭐ Run page-specific JS AFTER the HTML is added
        if (pageFile === "usermanagement.html") {
            setTimeout(() => {
                if (typeof initUserManagementPage === "function") {
                    initUserManagementPage();
                } else {
                    console.error("initUserManagementPage() not found. Did you include users.js?");
                }
            }, 50);
        }

        if (pageFile === "uploads.html") {
            setTimeout(() => {
                if (typeof initUploads === "function") {
                    initUploads();
                } else {
                    console.error("initUploads() not found. Did you include uploads.js?");
                }
            }, 50);
        }

        if (pageFile === "scholarship_dashboard.html") {
            setTimeout(() => {
                if (typeof initScholarshipDashboard === "function") {
                    initScholarshipDashboard();
                } else {
                    console.error("initScholarshipDashboardoads() not found. Did you include scholarship_dashboard.js?");
                }
            }, 50);
        }

        if (pageFile === "scholarship_uploads.html") {
            setTimeout(() => {
                if (typeof initScholarshipUploads === "function") {
                    initScholarshipUploads();
                } else {
                    console.error("initScholarshipUploads() not found. Did you include uploads.js?");
                }
            }, 50);
        }

        if (pageFile === "atrisk_dashboard.html") {
            setTimeout(() => {
                if (typeof initAtriskDashboard === "function") {
                    initAtriskDashboard();
                } else {
                    console.error("initUplinitAtriskDashboardoads() not found. Did you include atrisk_dashboard.js?");
                }
            }, 50);
        }

        if (pageFile === "clientlevelrisk.html") {
            setTimeout(() => {
                if (typeof initClientlevelrisk === "function") {
                    initClientlevelrisk();
                } else {
                    console.error("initClientlevelrisk() not found. Did you include clientlevelrisk.js?");
                }
            }, 50);
        }

        if (pageFile === "atrisk_uploads.html") {
            setTimeout(() => {
                if (typeof initAtriskUploads === "function") {
                    initAtriskUploads();
                } else {
                    console.error("initAtriskUploads() not found. Did you include uploads.js?");
                }
            }, 50);
        }
        

    } catch (err) {
        document.getElementById("mainContent").innerHTML =
            "<p class='text-danger'>Failed to load page.</p>";
        console.error(err);
    }

    history.pushState({}, "", urlPath);

    if (element) setActiveSidebar(element);
}


// Highlight active menu item
function setActiveSidebar(activeLink) {
    // Remove active from ALL menu items (top-level + sub-level)
    document.querySelectorAll(".side-nav-item, .side-nav-second-level li").forEach(item => {
        item.classList.remove("menuitem-active");
    });

    document.querySelectorAll(".side-nav-link, .side-nav-second-level a").forEach(link => {
        link.classList.remove("active");
    });

    // Add active to clicked link
    activeLink.classList.add("active");

    // Add active to its LI
    const li = activeLink.closest("li");
    if (li) li.classList.add("menuitem-active");

    // Add active to parent parent menu (collapsible top-level)
    const parentMenu = activeLink.closest(".collapse");
    if (parentMenu) {
        const topLink = document.querySelector(`a[href="#${parentMenu.id}"]`);
        if (topLink) {
            topLink.classList.add("active");
            topLink.parentElement.classList.add("menuitem-active");
        }

        // Keep the parent open
        parentMenu.classList.add("show");
    }
}


// ⭐ AUTO-DETECT PAGE BASED ON URL (Fixes Reload Issue)
document.addEventListener("DOMContentLoaded", function () {
    const path = window.location.pathname;           // ex: /analytics/usermanagement
    const page = path.split("/analytics/")[1] || "dashboard"; // extract page
    const file = page + ".html";                     // ex: usermanagement.html

    // Find the matching sidebar link
    const activeLink = document.querySelector(`a[href="/analytics/${page}"]`);

    // Load the correct page dynamically
    navigate(new Event("load"), `/analytics/${page}`, file, activeLink);

});


// Handle Back / Forward Browser Navigation
window.onpopstate = function () {
    const path = window.location.pathname;
    const page = path.split("/analytics/")[1] || "dashboard";
    const file = page + ".html";

    const activeLink = document.querySelector(`a[href="/analytics/${page}"]`);

    navigate(null, `/analytics/${page}`, file, activeLink);
};




