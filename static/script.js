 
document.getElementById("startExam").addEventListener("click", () => {
    fetch("/start_exam").then(res => res.json()).then(data =>
        alert(data.status)
    );
    startStatus();
});

document.getElementById("endExam").addEventListener("click", () => {
    fetch("/end_exam").then(res => res.json()).then(data =>
        alert(data.status)
    );
    stopStatus();
});

let statusCheck;

function updateStatus() {
    fetch("/check_status").then(res => res.json()).then(data => {
        document.getElementById("statusText").innerHTML =
            `Exam Running: ${data.exam_in_progress}<br>
             Exam Terminated: ${data.exam_terminated}<br>
             Current Window: ${data.current_window}<br>
             Noise Level: ${data.noise_level}`;

        if (data.exam_terminated) {
            alert("⚠ Exam Terminated Due to Violation!");
            stopStatus();
        }
    });
}

function startStatus() {
    statusCheck = setInterval(updateStatus, 1000);
}

function stopStatus() {
    clearInterval(statusCheck);
}
