normalButton = document.getElementById("matchmake-button-student-normal");
if (normalButton) {
    normalButton.addEventListener("click", async () => {
        const response = await fetch("/api/matchmaking/student-normal", {    // api luôn có dấu / đứng trước
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: document.getElementById("matchmake-topic").value })
        });
    
        if (response.redirected) {
            window.location.href = response.url; // manually follow redirect
        }
    });
}

urgentButton = document.getElementById("matchmake-button-student-urgent");
if (urgentButton) {
    urgentButton.addEventListener("click", async () => {
        const response = await fetch("/api/matchmaking/student-urgent", {    // api luôn có dấu / đứng trước
            method: "POST"
        });
    
        if (response.redirected) {
            window.location.href = response.url; // manually follow redirect
        }
    });
}

cancelButton = document.getElementById("cancel-button");
if (cancelButton) {
    cancelButton.addEventListener("click", async () => {
        const response = await fetch("/api/matchmaking/student-cancel", {    // api luôn có dấu / đứng trước
            method: "POST"
        });
    
        if (response.redirected) {
            window.location.href = response.url; // manually follow redirect
        }
    });
}

matchmakeButton = document.getElementById("matchmake-button-therapist");
if (matchmakeButton) {
    matchmakeButton.addEventListener("click", async () => {
        const response = await fetch("/api/matchmaking/therapist", {    // api luôn có dấu / đứng trước
            method: "POST"
        });
    
        if (response.redirected) {
            window.location.href = response.url; // manually follow redirect
        }
    });
}

cancelButton = document.getElementById("cancel-button");
if (cancelButton) {
    cancelButton.addEventListener("click", async () => {
        const response = await fetch("/api/matchmaking/therapist-cancel", {    // api luôn có dấu / đứng trước
            method: "POST"
        });
    
        if (response.redirected) {
            window.location.href = response.url; // manually follow redirect
        }
    });
}
