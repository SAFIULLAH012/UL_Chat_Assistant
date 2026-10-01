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

    // ==== PROFILE SYSTEM ====
    let currentProfile = {};
    const profileEditScreen = document.getElementById("profileEditScreen");
    const profileNameEl = document.getElementById("profileName");
    const profileDetailsEl = document.getElementById("profileDetails");

    function loadProfile() {
        const profile = JSON.parse(localStorage.getItem("ul-profile") || "null");
        if (profile && profileNameEl && profileDetailsEl) {
            profileNameEl.textContent = profile.type === 'visitor' ? "Visitor" : "Student";
            if (profile.type === 'visitor') {
                profileDetailsEl.textContent = "Guest User";
            } else {
                const parts = [profile.dept, profile.sem ? "Sem " + profile.sem : "", profile.sec ? "Sec " + profile.sec : ""].filter(Boolean);
                profileDetailsEl.textContent = parts.length ? parts.join(" · ") : "Tap to set up profile";
            }
            if (profile.image) {
                const mainImg = document.getElementById("mainProfileImg");
                const mainIcon = document.getElementById("mainProfileIcon");
                if (mainImg) { mainImg.src = profile.image; mainImg.style.display = 'block'; }
                if (mainIcon) { mainIcon.style.display = 'none'; }
                
                const previewImg = document.getElementById("profileImgPreview");
                const previewIcon = document.getElementById("profileImgIcon");
                if (previewImg) { previewImg.src = profile.image; previewImg.style.display = 'block'; }
                if (previewIcon) { previewIcon.style.display = 'none'; }
            }
        }
        currentProfile = profile || {};
        return profile;
    }

    function saveProfile(p) {
        localStorage.setItem("ul-profile", JSON.stringify(p));
        loadProfile();
    }

    // ==== CHAT STATE ====
    let chatState = "idle"; 
    let tempData = {};
    let pendingMessage = null;
    let pendingFlow = null;

    function vibrate() { if (navigator.vibrate) navigator.vibrate(50); }

    function openChat(initialMessage = null) {
        vibrate();
        landingPage.classList.add("hidden");
        chatInterface.classList.remove("hidden");
        
        const profile = loadProfile();
        const initialBotMsg = document.getElementById("initialBotMsg");
        const qqCard = document.getElementById("quickQuestionsCard");
        
        if (!profile && chatState === "idle" && !localStorage.getItem("ul-onboarded")) {
            if(initialBotMsg) initialBotMsg.style.display = "none";
            if(qqCard) qqCard.style.display = "none";
            
            if (initialMessage) pendingMessage = initialMessage;
            
            chatState = "onboard_type";
            const html = `
                <div class="bubble" style="align-self:flex-start;">Welcome to University of Layyah! 👋 Before we continue, are you a student or a visitor?</div>
                <div class="chat-card">
                    <h4 class="chat-card-title">Select User Type</h4>
                    <div class="chip-grid" style="grid-template-columns:1fr 1fr;">
                        <div class="chip-btn" onclick="handleCustomAction('onboard_type', 'student')"><i class="fa-solid fa-user-graduate"></i> Student</div>
                        <div class="chip-btn" onclick="handleCustomAction('onboard_type', 'visitor')"><i class="fa-solid fa-user"></i> Visitor</div>
                    </div>
                </div>`;
            simulateBotHTMLResponse(html, 500);
        } else {
            if(initialBotMsg) initialBotMsg.style.display = "flex";
            if(qqCard) qqCard.style.display = "block";
            
            if (initialMessage) {
                setTimeout(() => handleUserMessage(initialMessage), 500);
            }
        }
    }

    function closeChat() {
        vibrate();
        chatInterface.classList.add("hidden");
        landingPage.classList.remove("hidden");
    }

    // ==== UI HELPERS ====
    function addMessageToUI(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender);
        let innerHTML = '';
        if (sender === 'bot') innerHTML += '<img src="assets/robo.png" alt="Avatar" class="msg-avatar">';
        innerHTML += `<div class="bubble">${text}</div>`;
        msgDiv.innerHTML = innerHTML;
        chatMessages.insertBefore(msgDiv, typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addRawHTMLToUI(htmlContent, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender);
        let innerHTML = '';
        if (sender === 'bot') innerHTML += '<img src="assets/robo.png" alt="Avatar" class="msg-avatar" style="align-self:flex-start; margin-top:5px;">';
        innerHTML += `<div style="display:flex;flex-direction:column;gap:5px;width:100%;max-width:85%;">${htmlContent}</div>`;
        msgDiv.innerHTML = innerHTML;
        chatMessages.insertBefore(msgDiv, typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTyping() { typingIndicator.classList.remove("hidden"); chatMessages.scrollTop = chatMessages.scrollHeight; }
    function hideTyping() { typingIndicator.classList.add("hidden"); }

    function simulateBotHTMLResponse(html, delay = 800) {
        showTyping();
        setTimeout(() => { hideTyping(); addRawHTMLToUI(html, 'bot'); }, delay);
    }

    // ==== HTML GENERATORS FOR CHAT CARDS ====
    function getDeptHTML(context) {
        return `
            <div class="chat-card">
                <h4 class="chat-card-title">Select Department</h4>
                <div class="dept-list">
                    <div class="dept-item" onclick="handleCustomAction('${context}', 'BSCS')">
                        <div class="dept-info"><div class="dept-icon"><i class="fa-solid fa-graduation-cap"></i></div>
                        <div class="dept-text"><h5>BSCS</h5><p>Computer Science</p></div></div><i class="fa-solid fa-chevron-right dept-arrow"></i>
                    </div>
                    <div class="dept-item" onclick="handleCustomAction('${context}', 'BSIT')">
                        <div class="dept-info"><div class="dept-icon"><i class="fa-solid fa-laptop-code"></i></div>
                        <div class="dept-text"><h5>BSIT</h5><p>Information Technology</p></div></div><i class="fa-solid fa-chevron-right dept-arrow"></i>
                    </div>
                    <div class="dept-item" onclick="handleCustomAction('${context}', 'BBA')">
                        <div class="dept-info"><div class="dept-icon"><i class="fa-solid fa-briefcase"></i></div>
                        <div class="dept-text"><h5>BBA</h5><p>Business Administration</p></div></div><i class="fa-solid fa-chevron-right dept-arrow"></i>
                    </div>
                </div>
            </div>`;
    }

    function getSemHTML(context) {
        return `
            <div class="chat-card">
                <h4 class="chat-card-title">Select Semester</h4>
                <div class="chip-grid">
                    ${[1,2,3,4,5,6,7,8].map(s => `<div class="chip-btn" onclick="handleCustomAction('${context}', '${s}')">${s}</div>`).join('')}
                </div>
            </div>`;
    }

    function getSecHTML(context) {
        return `
            <div class="chat-card">
                <h4 class="chat-card-title">Select Section</h4>
                <div class="chip-grid">
                    ${['A','B','C','D'].map(s => `<div class="chip-btn" onclick="handleCustomAction('${context}', '${s}')">${s}</div>`).join('')}
                </div>
            </div>`;
    }

    function getUserTypeHTML(callbackId) {
        return `
            <div class="chat-card">
                <h4 class="chat-card-title">Select User Type</h4>
                <div class="chip-grid" style="grid-template-columns:1fr 1fr;">
                    <div class="chip-btn" onclick="handleCustomAction('${callbackId}', 'student')"><i class="fa-solid fa-user-graduate"></i> Student</div>
                    <div class="chip-btn" onclick="handleCustomAction('${callbackId}', 'visitor')"><i class="fa-solid fa-user"></i> Visitor</div>
                </div>
            </div>`;
    }

    // ==== MAIN ACTION HANDLER (Single unified function) ====
    window.handleCustomAction = function(action, value) {
        // Show user's selection in chat (skip empty values for top-level actions)
        const displayValue = value || action.replace(/_/g, ' ');
        addMessageToUI(displayValue.charAt(0).toUpperCase() + displayValue.slice(1), 'user');
        showTyping();

        setTimeout(() => {
            hideTyping();

            // ===== ONBOARDING FLOW =====
            if (action === 'onboard_type') {
                tempData.type = value;
                if (value === 'visitor') {
                    chatState = "idle";
                    saveProfile(tempData);
                    localStorage.setItem("ul-onboarded", "true");
                    showFinalOnboardOptions();
                } else {
                    chatState = "onboard_dept";
                    addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Which department are you in?</div>` + getDeptHTML('onboard_dept'), 'bot');
                }
                return;
            }
            if (action === 'onboard_dept') {
                tempData.dept = value;
                chatState = "onboard_sem";
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Got it. Which semester?</div>` + getSemHTML('onboard_sem'), 'bot');
                return;
            }
            if (action === 'onboard_sem') {
                tempData.sem = value;
                chatState = "onboard_sec";
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">And your section?</div>` + getSecHTML('onboard_sec'), 'bot');
                return;
            }
            if (action === 'onboard_sec') {
                tempData.sec = value;
                chatState = "idle";
                saveProfile(tempData);
                localStorage.setItem("ul-onboarded", "true");
                showFinalOnboardOptions();
                return;
            }

            // ===== ADMISSIONS FLOW =====
            if (action === 'admissions') {
                pendingFlow = 'admissions';
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Which department are you interested in for admissions?</div>` + getDeptHTML('admissions_dept'), 'bot');
                return;
            }
            if (action === 'admissions_dept') {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Admissions for <b>${value}</b> are currently open for Fall 2026! 🎓<br><br>📋 <b>Steps to Apply:</b><br>1. Visit the UOL Admissions Portal<br>2. Fill out the online application form<br>3. Upload required documents<br>4. Pay the application fee (PKR 2,500)<br><br>📅 <b>Deadline:</b> October 15, 2026<br><br>Would you like to know about scholarships or fee structure?</div>`, 'bot');
                pendingFlow = null;
                return;
            }

            // ===== FEE STRUCTURE FLOW =====
            if (action === 'fee_structure') {
                pendingFlow = 'fee_structure';
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Select department to view fee structure.</div>` + getDeptHTML('fee_dept'), 'bot');
                return;
            }
            if (action === 'fee_dept') {
                const feeHTML = `<div class="bubble" style="align-self:flex-start;">Fee structure for <b>${value}</b>:</div>
                    <div class="chat-card"><h4 class="chat-card-title">Fee Details<br><small style="color:var(--text-secondary);font-weight:400;font-size:12px;">${value}</small></h4>
                    <div class="timetable-container"><table class="timetable">
                        <tr><th>Item</th><th>Amount (PKR)</th></tr>
                        <tr><td>Admission Fee</td><td>50,000</td></tr>
                        <tr><td>Semester Tuition</td><td>1,20,000</td></tr>
                        <tr><td>Lab / IT Fee</td><td>15,000</td></tr>
                        <tr><td>Library Fee</td><td>5,000</td></tr>
                        <tr><td><b>Total Per Semester</b></td><td><b>1,90,000</b></td></tr>
                    </table></div></div>`;
                addRawHTMLToUI(feeHTML, 'bot');
                pendingFlow = null;
                return;
            }

            // ===== TIMETABLE FLOW =====
            if (action === 'timetable') {
                if (currentProfile && currentProfile.dept && currentProfile.sem && currentProfile.sec && currentProfile.type !== 'visitor') {
                    // Student with full profile — show their timetable directly
                    showTimetable(currentProfile.dept, currentProfile.sem, currentProfile.sec);
                } else {
                    pendingFlow = 'timetable';
                    addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Which department's timetable do you need?</div>` + getDeptHTML('tt_dept'), 'bot');
                }
                return;
            }
            if (action === 'tt_dept') {
                tempData.ttDept = value;
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Select semester for ${value}:</div>` + getSemHTML('tt_sem'), 'bot');
                return;
            }
            if (action === 'tt_sem') {
                tempData.ttSem = value;
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Select section:</div>` + getSecHTML('tt_sec'), 'bot');
                return;
            }
            if (action === 'tt_sec') {
                showTimetable(tempData.ttDept || 'BSCS', tempData.ttSem || '1', value);
                pendingFlow = null;
                return;
            }

            // ===== SCHOLARSHIPS FLOW =====
            if (action === 'scholarships') {
                pendingFlow = 'scholarships';
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Are you looking for scholarships as a current student or as a new applicant?</div>` + getUserTypeHTML('scholarship_user_type'), 'bot');
                return;
            }
            if (action === 'scholarship_user_type') {
                if (value === 'visitor') {
                    addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Great news! 🎉 New applicants can apply for these scholarships:<br><br>🏅 <b>Merit Scholarship</b> — Based on your Matric/FSc marks<br>💰 <b>Need-Based Scholarship</b> — Financial assistance program<br>🎓 <b>HEC EHSAAS</b> — Government funded scholarship<br><br>You can apply during the admissions process. Would you like to know about admissions?</div>`, 'bot');
                } else {
                    addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Select your department for scholarship details.</div>` + getDeptHTML('scholarship_dept'), 'bot');
                }
                pendingFlow = null;
                return;
            }
            if (action === 'scholarship_dept') {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Scholarships available for <b>${value}</b>:<br><br>🏅 <b>Merit Scholarship</b> — CGPA 3.5+ (50% tuition waiver)<br>💰 <b>Need-Based</b> — Apply via Financial Aid office<br>🎓 <b>HEC EHSAAS</b> — Full tuition + stipend<br>📝 <b>Sports Scholarship</b> — For varsity athletes<br><br>Visit the Scholarship Portal to download application forms.</div>`, 'bot');
                return;
            }

            // ===== STUDENT SERVICES =====
            if (action === 'student_services') {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Student Services are available at the Admin Block 🏛️<br><br>🕐 <b>Hours:</b> Mon–Fri, 9:00 AM – 4:00 PM<br>📞 <b>Phone:</b> +92-606-123456<br>📧 <b>Email:</b> services@uol.edu.pk<br><br><b>Services include:</b><br>• Transcript requests<br>• Character certificates<br>• ID card replacement<br>• Enrollment verification<br>• Hostel accommodation<br><br>Is there anything specific you need help with?</div>`, 'bot');
                return;
            }

            // ===== QUICK / FALLBACK =====
            if (action === 'quick') {
                handleUserMessage(value);
                return;
            }

        }, 600);
    };

    // ==== TIMETABLE DISPLAY HELPER ====
    function showTimetable(dept, sem, sec) {
        const html = `<div class="bubble" style="align-self:flex-start;">Here is the timetable for <b>${dept}</b> — Semester ${sem}, Section ${sec}:</div>
            <div class="chat-card"><h4 class="chat-card-title">Timetable<br><small style="color:var(--text-secondary);font-weight:400;font-size:12px;">${dept} · Sem ${sem} · Sec ${sec}</small></h4>
            <div class="timetable-container"><table class="timetable">
                <tr><th>Day</th><th>Subject</th><th>Time</th><th>Room</th></tr>
                <tr><td>Mon</td><td>Data Structures</td><td>09:00 - 10:30</td><td>C-201</td></tr>
                <tr><td>Tue</td><td>Database Systems</td><td>11:00 - 12:30</td><td>C-203</td></tr>
                <tr><td>Wed</td><td>Web Engineering</td><td>09:00 - 10:30</td><td>C-201</td></tr>
                <tr><td>Thu</td><td>OOP Lab</td><td>02:00 - 04:00</td><td>Lab-2</td></tr>
                <tr><td>Fri</td><td>Linear Algebra</td><td>10:00 - 11:30</td><td>C-105</td></tr>
            </table></div></div>`;
        addRawHTMLToUI(html, 'bot');
    }

    // ==== POST-ONBOARDING OPTIONS ====
    function showFinalOnboardOptions() {
        if (pendingMessage) {
            const temp = pendingMessage;
            pendingMessage = null;
            setTimeout(() => handleUserMessage(temp), 500);
            return;
        }

        const greet = currentProfile.type === 'visitor' ? "Great to have you here!" : "Profile set up successfully!";
        const qqHTML = `
            <div class="bubble" style="align-self:flex-start;">${greet} What would you like to know about?</div>
            <div class="quick-questions-card" style="width:100%;max-width:100%;margin-top:10px;">
                <h4 class="card-title">Select an option</h4>
                <div class="quick-grid">
                    <button class="quick-btn" onclick="handleCustomAction('admissions', '')"><i class="fa-solid fa-graduation-cap"></i> Admissions</button>
                    <button class="quick-btn" onclick="handleCustomAction('fee_structure', '')"><i class="fa-solid fa-file-invoice-dollar"></i> Fee Structure</button>
                    <button class="quick-btn" onclick="handleCustomAction('timetable', '')"><i class="fa-regular fa-calendar-days"></i> Timetable</button>
                    <button class="quick-btn" onclick="handleCustomAction('scholarships', '')"><i class="fa-solid fa-trophy"></i> Scholarships</button>
                    <button class="quick-btn" onclick="handleCustomAction('student_services', '')" style="grid-column: span 2; justify-content:center;"><i class="fa-solid fa-headset"></i> Student Services</button>
                </div>
            </div>`;
        addRawHTMLToUI(qqHTML, 'bot');
    }

    // ==== GENERIC BOT RESPONSE (for typed messages) ====
    function simulateBotResponse(userText) {
        showTyping();
        const delay = Math.floor(Math.random() * 800) + 600;
        
        setTimeout(() => {
            hideTyping();
            const lowerText = userText ? userText.toLowerCase() : "";
            
            if (lowerText.includes("timetable") || lowerText.includes("time table")) {
                if (currentProfile && currentProfile.dept && currentProfile.sem && currentProfile.sec && currentProfile.type !== 'visitor') {
                    showTimetable(currentProfile.dept, currentProfile.sem, currentProfile.sec);
                } else {
                    addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Which department's timetable do you need?</div>` + getDeptHTML('tt_dept'), 'bot');
                }
            } else if (lowerText.includes("admission")) {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Which department are you interested in for admissions?</div>` + getDeptHTML('admissions_dept'), 'bot');
            } else if (lowerText.includes("fee")) {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Select department to view fee structure.</div>` + getDeptHTML('fee_dept'), 'bot');
            } else if (lowerText.includes("scholarship")) {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Are you looking for scholarships as a current student or a new applicant?</div>` + getUserTypeHTML('scholarship_user_type'), 'bot');
            } else if (lowerText.includes("service") || lowerText.includes("support")) {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">Student Services are available at the Admin Block 🏛️<br><br>🕐 <b>Hours:</b> Mon–Fri, 9:00 AM – 4:00 PM<br>📞 <b>Phone:</b> +92-606-123456<br>📧 <b>Email:</b> services@uol.edu.pk</div>`, 'bot');
            } else if (lowerText.includes("department") || lowerText.includes("dept")) {
                addRawHTMLToUI(`<div class="bubble" style="align-self:flex-start;">University of Layyah offers the following departments:<br><br>💻 BSCS — Computer Science<br>🖥️ BSIT — Information Technology<br>💼 BBA — Business Administration<br>📖 BS English<br>🔢 BS Mathematics<br>⚛️ BS Physics<br>🧪 BS Chemistry<br>🔬 BS Zoology</div>`, 'bot');
            } else {
                const responses = [
                    "That's a great question! I can help you with admissions, fees, timetables, scholarships, and student services. What would you like to know?",
                    "I'd be happy to help! Try asking about admissions, fee structure, timetables, or scholarships.",
                    "Let me know if you need information about admissions, fees, departments, or any other university services."
                ];
                addMessageToUI(responses[Math.floor(Math.random() * responses.length)], 'bot');
            }
        }, delay);
    }

    function handleUserMessage(text) {
        if (!text.trim()) return;
        addMessageToUI(text, 'user');
        chatInput.value = '';
        simulateBotResponse(text);
    }

    // ==== EVENT LISTENERS ====
    if (startChatBtn) startChatBtn.addEventListener("click", () => openChat());
    if (backBtn) backBtn.addEventListener("click", closeChat);

    featureItems.forEach(item => {
        item.addEventListener("click", function() { openChat(this.dataset.name); });
    });

    sendBtn.addEventListener("click", () => handleUserMessage(chatInput.value));
    chatInput.addEventListener("keypress", (e) => { if (e.key === "Enter") handleUserMessage(chatInput.value); });

    // ==== MOBILE KEYBOARD FIX ====
    // When keyboard opens on mobile, scroll chat to bottom so input stays visible
    chatInput.addEventListener("focus", () => {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 350);
    });

    // Use visualViewport API for better keyboard handling on modern mobile browsers
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", () => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    // ==== SETTINGS SCREEN ====
    const openSettingsBtn = document.getElementById("openSettingsBtn");
    const settingsIcon = document.getElementById("settingsIcon");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const settingsScreen = document.getElementById("settingsScreen");
    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const themeText = document.getElementById("themeText");
    const htmlElement = document.documentElement;

    if (openSettingsBtn && settingsScreen) {
        openSettingsBtn.addEventListener("click", () => {
            if (settingsScreen.classList.contains("hidden")) {
                chatInterface.classList.add("hidden"); 
                settingsScreen.classList.remove("hidden");
                if (settingsIcon) {
                    settingsIcon.classList.remove("fa-bars");
                    settingsIcon.classList.add("fa-xmark");
                }
            } else {
                settingsScreen.classList.add("hidden"); 
                chatInterface.classList.remove("hidden");
                if (settingsIcon) {
                    settingsIcon.classList.remove("fa-xmark");
                    settingsIcon.classList.add("fa-bars");
                }
            }
        });
        
        if (closeSettingsBtn) {
            closeSettingsBtn.addEventListener("click", () => {
                settingsScreen.classList.add("hidden"); chatInterface.classList.remove("hidden");
                if (settingsIcon) {
                    settingsIcon.classList.remove("fa-xmark");
                    settingsIcon.classList.add("fa-bars");
                }
            });
        }
    }

    // ==== THEME SYSTEM ====
    let isDark = (htmlElement.getAttribute("data-theme") || "dark") === "dark";
    function applyTheme(dark) {
        isDark = dark;
        htmlElement.setAttribute("data-theme", dark ? "dark" : "light");
        localStorage.setItem("ul-theme", dark ? "dark" : "light");
        const mainToggleIcon = document.querySelector("#mainThemeToggle i");
        if (mainToggleIcon) {
            mainToggleIcon.className = dark ? "fa-solid fa-moon" : "fa-solid fa-sun";
            mainToggleIcon.style.color = dark ? "" : "#f59e0b";
        }
        if (themeToggle) themeToggle.checked = dark;
        if (themeIcon) {
            themeIcon.className = dark ? "fa-solid fa-moon theme-icon" : "fa-solid fa-sun theme-icon";
            themeIcon.style.color = dark ? "" : "#f59e0b";
        }
        if (themeText) themeText.innerText = dark ? "Dark Mode" : "Light Mode";
    }

    const savedTheme = localStorage.getItem("ul-theme");
    if (savedTheme) applyTheme(savedTheme === "dark");

    const mainThemeToggle = document.getElementById("mainThemeToggle");
    if (mainThemeToggle) mainThemeToggle.addEventListener("click", () => applyTheme(!isDark));
    if (themeToggle) themeToggle.addEventListener("change", (e) => applyTheme(e.target.checked));

    // ==== EDIT PROFILE SCREEN ====
    const profileCardSettings = document.getElementById("profileCardSettings");
    const profileMenuItem = document.getElementById("profileMenuItem");
    const closeProfileBtn = document.getElementById("closeProfileBtn");
    const updateProfileBtn = document.getElementById("updateProfileBtn");
    const editUserType = document.getElementById("editUserType");
    const studentFieldsContainer = document.getElementById("studentFieldsContainer");
    
    if (editUserType) {
        editUserType.addEventListener("change", (e) => {
            if (studentFieldsContainer) {
                studentFieldsContainer.style.display = e.target.value === 'visitor' ? 'none' : 'block';
            }
        });
    }

    function openProfileEdit() {
        const p = currentProfile;
        const editDept = document.getElementById("editDept");
        const editSem = document.getElementById("editSem");
        const editSec = document.getElementById("editSec");
        
        if (editUserType) {
            editUserType.value = p.type || 'student';
            if (studentFieldsContainer) {
                studentFieldsContainer.style.display = editUserType.value === 'visitor' ? 'none' : 'block';
            }
        }
        
        if (editDept) editDept.value = p.dept || "";
        if (editSem) editSem.value = p.sem || "";
        if (editSec) editSec.value = p.sec || "";
        settingsScreen.classList.add("hidden");
        profileEditScreen.classList.remove("hidden");
    }

    if (profileCardSettings) profileCardSettings.addEventListener("click", openProfileEdit);
    if (profileMenuItem) profileMenuItem.addEventListener("click", openProfileEdit);
    if (closeProfileBtn) closeProfileBtn.addEventListener("click", () => { profileEditScreen.classList.add("hidden"); settingsScreen.classList.remove("hidden"); });
    
    let pendingImageUpdate = null;
    const profileImgContainer = document.getElementById("profileImgContainer");
    const profileImgUpload = document.getElementById("profileImgUpload");
    if (profileImgContainer && profileImgUpload) {
        profileImgContainer.addEventListener("click", () => {
            profileImgUpload.click();
        });
        profileImgUpload.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    pendingImageUpdate = event.target.result;
                    const previewImg = document.getElementById("profileImgPreview");
                    const previewIcon = document.getElementById("profileImgIcon");
                    if (previewImg) { previewImg.src = pendingImageUpdate; previewImg.style.display = 'block'; }
                    if (previewIcon) { previewIcon.style.display = 'none'; }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (updateProfileBtn) {
        updateProfileBtn.addEventListener("click", () => {
            const type = editUserType ? editUserType.value : 'student';
            const dept = document.getElementById("editDept").value;
            const sem = document.getElementById("editSem").value;
            const sec = document.getElementById("editSec").value;
            
            const newProfile = {
                type, 
                dept: type === 'visitor' ? '' : dept, 
                sem: type === 'visitor' ? '' : sem, 
                sec: type === 'visitor' ? '' : sec,
                image: pendingImageUpdate || currentProfile.image
            };
            
            saveProfile(newProfile);
            profileEditScreen.classList.add("hidden");
            settingsScreen.classList.remove("hidden");
        });
    }

    // ==== LOGOUT / RESET ====
    const logoutBtn = document.querySelector(".logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            if(confirm("Are you sure you want to logout and clear all profile data?")) {
                localStorage.removeItem("ul-profile");
                localStorage.removeItem("ul-onboarded");
                location.reload();
            }
        });
    }

    // ==== INITIAL LOAD ====
    loadProfile();
});
