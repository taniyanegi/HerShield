const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.continuous = true;

recognition.onresult = function (event) {
    const transcript = event.results[event.resultIndex][0].transcript.trim().toLowerCase();
    if (transcript.includes("help") || transcript.includes("emergency")) {
        alert("Voice Detected: HELP! Sending alert...");
        document.querySelector("button").click();  // Simulates emergency button click
    }
};

recognition.start();
