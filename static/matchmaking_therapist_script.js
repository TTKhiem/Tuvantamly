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
