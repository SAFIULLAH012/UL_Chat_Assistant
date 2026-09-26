document.addEventListener("DOMContentLoaded", () => {
    const landingPage = document.getElementById("landingPage");
    const chatInterface = document.getElementById("chatInterface");
    const startChatBtn = document.getElementById("startChat");
    const backBtn = document.getElementById("backBtn");
    const featureItems = document.querySelectorAll(".feature");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatMessages = document.getElementById("chatMessages");
    const typingIndicator = document.getElementById("typingIndicator");

    const botResponses = [
        "That's a great question about the University of Layyah.",
        "Our admissions are currently open for the Fall semester. You can apply online.",
        "We offer various merit-based and need-based scholarships. Let me know if you need the forms.",
        "Our fee structure is very reasonable and varies slightly by department.",
        "You can find detailed timetables on the student portal.",
        "Student Services is open Monday through Friday, 9am to 4pm."
    ];

    function vibrate() {
        if (navigator.vibrate) navigator.vibrate(50);
    }

    function openChat(initialMessage = null) {
        vibrate();
        landingPage.classList.add("hidden");
        chatInterface.classList.remove("hidden");
        
        if (initialMessage) {
            setTimeout(() => {
                handleUserMessage(initialMessage);
            }, 500);
        }
    }

    function closeChat() {
        vibrate();
        chatInterface.classList.add("hidden");
        landingPage.classList.remove("hidden");
    }

    function addMessageToUI(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender);
        
        let innerHTML = '';
        if (sender === 'bot') {
            innerHTML += '<img src="assets/UOL_Robot_Animation_Layers.svg" alt="Avatar" class="msg-avatar">';
        }
        
        innerHTML += `<div class="bubble">${text}</div>`;
        msgDiv.innerHTML = innerHTML;
        
        chatMessages.insertBefore(msgDiv, typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping() {
        typingIndicator.classList.remove("hidden");
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideTyping() {
        typingIndicator.classList.add("hidden");
    }

    function simulateBotResponse() {
        showTyping();
        const delay = Math.floor(Math.random() * 1500) + 1000;
        
        setTimeout(() => {
            hideTyping();
            const randomResponse = botResponses[Math.floor(Math.random() * botResponses.length)];
            addMessageToUI(randomResponse, 'bot');
        }, delay);
    }

    function handleUserMessage(text) {
        if (!text.trim()) return;
        
        addMessageToUI(text, 'user');
        chatInput.value = '';
        
        simulateBotResponse();
    }

    if (startChatBtn) startChatBtn.addEventListener("click", () => openChat());
    if (backBtn) backBtn.addEventListener("click", closeChat);

    featureItems.forEach(item => {
        item.addEventListener("click", function() {
            const promptText = this.dataset.name;
            openChat(promptText);
        });
    });

    sendBtn.addEventListener("click", () => {
        handleUserMessage(chatInput.value);
    });

    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            handleUserMessage(chatInput.value);
        }
    });

    // Robot animations (blink, pupil wander, ear lights, scan line) are
    // handled natively via CSS @keyframes inside assets/robo.png
});
