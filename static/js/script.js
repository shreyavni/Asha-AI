document.addEventListener('DOMContentLoaded', () => {
    // --- Get DOM Elements ---
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const clearButton = document.getElementById('clear-button');
    const micButton = document.getElementById('mic-button');
    const typingIndicator = document.getElementById('typing-indicator');
    const settingsButton = document.getElementById('settings-button');
    const voiceModal = document.getElementById('voice-modal');
    const closeModalButton = document.getElementById('close-modal-button');
    const voiceListDiv = document.getElementById('voice-list');
    const saveVoiceButton = document.getElementById('save-voice-button');
    const testVoiceButton = document.getElementById('test-voice-button');


    // --- Speech Synthesis (TTS) Setup ---
    const synth = window.speechSynthesis;
    let availableVoices = [];
    let currentUtterance = null;
    let selectedVoiceURI = localStorage.getItem('selectedVoiceURI'); // Load saved voice URI


    // --- Speech Recognition (STT) Setup ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    // --- Initialize STT ---
    if (SpeechRecognition) {
        try {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.lang = 'en-IN';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onresult = (event) => {
                const transcript = event.results[event.results.length - 1][0].transcript.trim();
                userInput.value = transcript;
                stopListening();
                adjustTextareaHeight();
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error, event.message);
                let errorMessage = `Speech error: ${event.error}`;
                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    errorMessage = "Mic permission denied.";
                } else if (event.error === 'no-speech') {
                    errorMessage = "No speech detected.";
                } else if (event.error === 'audio-capture') {
                    errorMessage = "Mic audio capture error.";
                } else if (event.error === 'network') {
                    errorMessage = "Network error during speech recognition.";
                }
                userInput.placeholder = errorMessage;
                setTimeout(() => { userInput.placeholder = "Ask about jobs, interviews..."; }, 3000);
                stopListening();
            };

            recognition.onend = () => {
                console.log("Speech recognition ended.");
                if (isListening) {
                    stopListening();
                }
            };
        } catch (e) {
            console.error("Failed to initialize SpeechRecognition:", e);
            if (micButton) { micButton.disabled = true; micButton.title = "Voice input init failed"; }
        }

    } else {
        console.warn("Speech Recognition API not supported.");
        if (micButton) { micButton.disabled = true; micButton.title = "Voice input not supported"; }
    }

    // --- STT Control Functions ---
    function startListening() {
        if (!recognition || isListening) return;
        if (synth.speaking) { console.log("Stopping TTS to start STT..."); synth.cancel(); }
        if (synth.speaking) { setTimeout(startListening, 150); return; }

        try {
            userInput.placeholder = "Listening...";
            recognition.start();
            isListening = true;
            micButton.classList.add('listening');
            micButton.innerHTML = '<i class="ri-mic-fill"></i>';
            micButton.title = "Stop Listening";
            console.log("Speech recognition started.");
        } catch (error) {
            if (error.name === 'InvalidStateError') {
                console.warn('Recognition already started? Attempting to stop and restart.');
                setTimeout(startListening, 150);
            } else {
                console.error("Error starting recognition:", error);
                isListening = false;
                micButton.classList.remove('listening');
                micButton.innerHTML = '<i class="ri-mic-line"></i>';
                micButton.title = "Use Voice Input";
                userInput.placeholder = "Couldn't start mic.";
            }
        }
    }

    function stopListening() {
        if (!recognition) return;
        if (!isListening) {
            micButton.classList.remove('listening');
            micButton.innerHTML = '<i class="ri-mic-line"></i>';
            micButton.title = "Use Voice Input";
            if (userInput.placeholder === "Listening...") {
                userInput.placeholder = "Ask about jobs, interviews...";
            }
            return;
        }
        console.log("Attempting to stop speech recognition...");
        try { recognition.abort(); }
        catch (e) { console.warn("Error aborting recognition:", e); try { recognition.stop(); } catch (e2) { console.warn("Error stopping recognition:", e2); } }
        finally {
            isListening = false;
            micButton.classList.remove('listening');
            micButton.innerHTML = '<i class="ri-mic-line"></i>';
            micButton.title = "Use Voice Input";
            userInput.placeholder = "Ask about jobs, interviews...";
        }
    }

    // --- Mic Button Listener ---
    if (micButton) {
        micButton.addEventListener('click', () => {
            if (isListening) { stopListening(); } else { startListening(); }
        });
    }


    // --- Voice Loading and Modal Population ---
    function populateVoiceList() {
        if (!voiceListDiv) return;
        voiceListDiv.innerHTML = '';
        const filteredVoices = availableVoices
            .filter(voice => voice.lang.startsWith('en-'))
            .sort((a, b) => {
                if (a.lang === 'en-IN' && b.lang !== 'en-IN') return -1;
                if (a.lang !== 'en-IN' && b.lang === 'en-IN') return 1;
                if (a.lang === 'en-GB' && b.lang !== 'en-GB') return -1;
                if (a.lang !== 'en-GB' && b.lang === 'en-GB') return 1;
                if (a.lang === 'en-US' && b.lang !== 'en-US') return -1;
                if (a.lang !== 'en-US' && b.lang === 'en-US') return 1;
                return a.name.localeCompare(b.name);
            });

        if (filteredVoices.length === 0) {
            voiceListDiv.innerHTML = "<p>No English voices found in this browser.</p>";
            return;
        }
        const currentSelectedVoice = availableVoices.find(voice => voice.voiceURI === selectedVoiceURI);
        filteredVoices.forEach(voice => {
            const radio = document.createElement('input');
            radio.type = 'radio'; radio.name = 'voiceSelection';
            radio.value = voice.voiceURI; radio.id = voice.voiceURI;
            // Check based on saved URI first, then fallback logic
            if (selectedVoiceURI === voice.voiceURI) {
                radio.checked = true;
            } else if (!selectedVoiceURI && currentSelectedVoice && voice.voiceURI === currentSelectedVoice.voiceURI) {
                // This case might not be needed if selectedVoiceURI is always updated
                radio.checked = true;
            } else if (!selectedVoiceURI && !currentSelectedVoice && voice === filteredVoices[0]) {
                // Fallback: check the first voice in the filtered list if nothing else matches
                radio.checked = true;
            }

            const label = document.createElement('label');
            label.htmlFor = voice.voiceURI; label.appendChild(radio);
            label.appendChild(document.createTextNode(` ${voice.name} `));
            const langSpan = document.createElement('span');
            langSpan.className = 'voice-lang'; langSpan.textContent = `(${voice.lang})`;
            label.appendChild(langSpan);
            voiceListDiv.appendChild(label);
        });
        const containerStatus = voiceListDiv.previousElementSibling;
        if (containerStatus && containerStatus.tagName === 'P') { containerStatus.textContent = 'Select a preferred voice:'; }
    }

    function loadVoices() {
        try {
            let voices = synth.getVoices();
            if (voices.length > 0) {
                availableVoices = voices;
                console.log("Voices loaded:", availableVoices.length);
                populateVoiceList();
            } else {
                console.log("Voice list empty initially, waiting for voiceschanged event.");
            }
        } catch (e) { console.error("Error loading voices:", e); }
    }
    loadVoices();
    if (synth.onvoiceschanged !== undefined) { synth.onvoiceschanged = loadVoices; }
    setTimeout(loadVoices, 500);


    // --- Modal Event Listeners ---
    if (settingsButton && voiceModal && closeModalButton && saveVoiceButton && testVoiceButton) {
        settingsButton.addEventListener('click', () => { populateVoiceList(); voiceModal.style.display = 'block'; });
        closeModalButton.addEventListener('click', () => { voiceModal.style.display = 'none'; });
        window.addEventListener('click', (event) => { if (event.target == voiceModal) { voiceModal.style.display = 'none'; } });
        saveVoiceButton.addEventListener('click', () => {
            const selectedRadio = voiceListDiv.querySelector('input[name="voiceSelection"]:checked');
            if (selectedRadio) {
                selectedVoiceURI = selectedRadio.value;
                localStorage.setItem('selectedVoiceURI', selectedVoiceURI);
                console.log("Saved voice preference:", selectedVoiceURI);
                voiceModal.style.display = 'none';
            } else { console.warn("No voice selected to save."); }
        });
        testVoiceButton.addEventListener('click', () => {
            const selectedRadio = voiceListDiv.querySelector('input[name="voiceSelection"]:checked');
            if (selectedRadio && selectedRadio.value) {
                const voiceToTest = availableVoices.find(v => v.voiceURI === selectedRadio.value);
                if (voiceToTest) {
                    if (synth.speaking) synth.cancel();
                    const testUtterance = new SpeechSynthesisUtterance("Hello! This is a test of the selected voice.");
                    testUtterance.voice = voiceToTest; testUtterance.rate = 1.0; testUtterance.pitch = 1.0;
                    synth.speak(testUtterance);
                } else { console.error("Selected voice object not found for testing."); }
            } else { console.warn("No voice selected to test."); }
        });
    } else { console.error("Modal elements not found in the DOM."); }



    
    // --- Function to add a message ---
    function addMessage(sender, messageContent, suggestions = []) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);
        let scrollBehavior = 'smooth';
        let shouldScroll = true;
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        if (sender === 'user') {
            contentDiv.textContent = messageContent;
            messageElement.appendChild(contentDiv);
        } else {
            const speakButton = document.createElement('button');
            speakButton.classList.add('speak-button');
            speakButton.innerHTML = '<i class="ri-volume-up-line"></i>'; // Use icon
            speakButton.title = "Read aloud";
            speakButton.setAttribute('aria-label', 'Read message aloud');
            const botTextContent = messageContent || "";
            speakButton.onclick = (e) => { e.stopPropagation(); speakText(speakButton, botTextContent); };
            const options = { breaks: true, gfm: true };
            const rawHtml = marked.parse(messageContent || "", options);
            contentDiv.innerHTML = rawHtml;
            contentDiv.appendChild(speakButton);
            contentDiv.querySelectorAll('a').forEach(a => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
            messageElement.appendChild(contentDiv);

            if (suggestions && suggestions.length > 0) {
                const suggestionsDiv = document.createElement('div');
                suggestionsDiv.classList.add('inline-suggestions');
                suggestions.forEach(suggestionText => {
                    const button = document.createElement('button');
                    button.classList.add('inline-suggestion-button');
                    button.textContent = suggestionText;
                    button.onclick = () => { userInput.value = suggestionText; sendMessage(); suggestionsDiv.remove(); };
                    suggestionsDiv.appendChild(button);
                });
                messageElement.appendChild(suggestionsDiv);
            }
            shouldScroll = false;
            scrollBehavior = 'auto';

            setTimeout(() => {
                try {
                    const mermaidElements = messageElement.querySelectorAll('.language-mermaid');
                    if (mermaidElements.length > 0) {
                        const nodesToRender = [];
                        mermaidElements.forEach(el => {
                            if (el && el.parentNode) {
                                const pre = document.createElement('pre');
                                pre.className = 'mermaid';
                                pre.textContent = el.textContent || '';
                                const parentPre = el.closest('pre');
                                if (parentPre && parentPre.parentNode) { parentPre.parentNode.replaceChild(pre, parentPre); nodesToRender.push(pre); }
                                else { el.parentNode.replaceChild(pre, el); nodesToRender.push(pre); }
                            }
                        });
                        if (nodesToRender.length > 0 && typeof mermaid !== 'undefined' && mermaid.run) {
                            console.log(`Rendering ${nodesToRender.length} Mermaid diagrams...`);
                            mermaid.run({ nodes: nodesToRender });
                        } else if (nodesToRender.length > 0) { console.warn("Mermaid library not ready or run function not found."); }
                    }
                } catch (e) { console.error("Mermaid rendering error:", e); }
            }, 100);

        }


        const currentTypingIndicator = chatBox.querySelector('.typing-indicator');
        if (currentTypingIndicator) { chatBox.insertBefore(messageElement, currentTypingIndicator); }
        else { chatBox.appendChild(messageElement); }

        const scrollThreshold = 150;
        if (chatBox && chatBox.scrollHeight > chatBox.clientHeight) {
            const isNearBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < scrollThreshold;
            if (shouldScroll || (sender === 'bot' && isNearBottom)) { chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: scrollBehavior }); }
        } else if (chatBox) { chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: scrollBehavior }); }
    }

    // --- Function to handle Text-to-Speech ---
    function speakText(buttonElement, textToSpeak) {
        if (!synth) { console.error("Speech Synthesis not supported."); /*...*/ return; }
        if (isListening) { console.log("Stopping STT to start TTS..."); stopListening(); }
        if (isListening) { setTimeout(() => speakText(buttonElement, textToSpeak), 150); return; }

        const emojiRegex = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F0CF}\u{1F170}-\u{1F171}\u{1F17E}-\u{1F17F}\u{1F18E}\u{1F191}-\u{1F19A}\u{1F201}-\u{1F202}\u{1F21A}\u{1F22F}\u{1F232}-\u{1F23A}\u{1F250}-\u{1F251}\u{200D}\u{203C}\u{2049}\u{2122}\u{2139}\u{2194}-\u{2199}\u{21A9}-\u{21AA}\u{231A}-\u{231B}\u{2328}\u{23CF}\u{23E9}-\u{23F3}\u{23F8}-\u{23FA}\u{24C2}\u{25AA}-\u{25AB}\u{25B6}\u{25C0}\u{25FB}-\u{25FE}\u{2934}-\u{2935}\u{2B05}-\u{2B07}\u{2B1B}-\u{2B1C}\u{2B50}\u{2B55}\u{3030}\u{303D}\u{3297}\u{3299}]/gu;
        let cleanText = textToSpeak
            .replace(emojiRegex, '') // Remove emojis
            .replace(/\[.*?\]\(.*?\)/g, '') // Remove markdown links
            .replace(/```mermaid.*?```/gs, 'Diagram follows.')
            .replace(/```.*?```/gs, 'Code snippet follows.')
            .replace(/[*_`#]/g, '')
            .replace(/\s+/g, ' ')
            .trim();

        if (currentUtterance && synth.speaking && buttonElement && buttonElement.classList.contains('speaking')) { synth.cancel(); return; }
        if (synth.speaking) { synth.cancel(); }

        document.querySelectorAll('.speak-button.speaking').forEach(btn => { btn.classList.remove('speaking'); btn.innerHTML = '<i class="ri-volume-up-line"></i>'; }); // Reset with icon

        if (!cleanText) { console.log("No text content to speak after cleaning."); return; }

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-IN';

        // Apply Saved or Default Voice
        let voiceToUse = null;
        if (selectedVoiceURI && availableVoices.length > 0) {
            voiceToUse = availableVoices.find(v => v.voiceURI === selectedVoiceURI);
            if (voiceToUse) {
                console.log("Using saved voice:", voiceToUse.name, voiceToUse.lang);
            } else {
                console.warn("Saved voice URI not found, falling back to default selection.");
                selectedVoiceURI = null; // Clear invalid saved URI
                localStorage.removeItem('selectedVoiceURI');
            }
        }

        // *** Start Fallback Logic ***
        if (!voiceToUse && availableVoices.length > 0) {
            // Prioritize Indian English Female
            voiceToUse = availableVoices.find(voice => voice.lang === 'en-IN' && /female/i.test(voice.name));
            // Fallback to any Indian English
            if (!voiceToUse) {
                voiceToUse = availableVoices.find(voice => voice.lang === 'en-IN');
            }
            // Fallback to British Female
            if (!voiceToUse) {
                voiceToUse = availableVoices.find(voice => voice.lang === 'en-GB' && /female/i.test(voice.name));
            }
            // Fallback to US Female
            if (!voiceToUse) {
                voiceToUse = availableVoices.find(voice => voice.lang === 'en-US' && /female/i.test(voice.name));
            }
            // Fallback to any English
            if (!voiceToUse) {
                voiceToUse = availableVoices.find(voice => voice.lang.startsWith('en-'));
            }
            if (voiceToUse) console.log("Using default selected voice:", voiceToUse.name, voiceToUse.lang);
            else console.log("Using system default voice.");
        }
        // *** End Fallback Logic ***
        else if (!voiceToUse) {
            console.log("Voice list not ready or empty, using system default voice.");
        }

        if (voiceToUse) {
            utterance.voice = voiceToUse;
        }

        // Set Rate and Pitch
        utterance.rate = 1.8; // 1 is default, adjust as needed (e.g., 1.1 for slightly faster)
/*************  ✨ Windsurf Command 🌟  *************/
        utterance.rate = 1.7; // 1 is default, range 0.1-10
        utterance.pitch = 1.7; // 1 is default, range 0-2
        utterance.volume = 1.0; // 1 is default, range 0-1
        utterance.clarity = 1;

        utterance.addEventListener('start', () => {
            if (buttonElement) {
                buttonElement.classList.add('speaking');
                buttonElement.innerHTML = '<i class="ri-pause-fill"></i>';
            }
            currentUtterance = utterance;
        });
        utterance.onstart = () => { if (buttonElement) { buttonElement.classList.add('speaking'); buttonElement.innerHTML = '<i class="ri-pause-fill"></i>'; } currentUtterance = utterance; };
        utterance.onend = () => {
            if (buttonElement) { buttonElement.classList.remove('speaking'); buttonElement.innerHTML = '<i class="ri-volume-up-line"></i>'; }
            if (currentUtterance === utterance) { currentUtterance = null; }
        };
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error); // Log error instead of alert
            if (buttonElement) {
                buttonElement.title = `Speech error: ${event.error}`;
                buttonElement.classList.remove('speaking');
                buttonElement.innerHTML = '<i class="ri-volume-up-line"></i>';
            }
            if (currentUtterance === utterance) { currentUtterance = null; }
        };
        synth.speak(utterance);
    }


    // --- Function to show/hide typing indicator ---
    function showTypingIndicator() {
        typingIndicator.style.display = 'flex';
        chatBox.appendChild(typingIndicator);
        chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
    }
    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
    }

    // --- Function to handle sending a message ---
    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (messageText === '' || sendButton.disabled) return;

        if (synth.speaking) { synth.cancel(); }
        if (isListening) { stopListening(); }

        addMessage('user', messageText);

        userInput.value = '';
        userInput.disabled = true;
        sendButton.disabled = true;
        clearButton.disabled = true;
        if (micButton) micButton.disabled = true;
        adjustTextareaHeight();
        document.querySelectorAll('.inline-suggestions').forEach(el => el.remove());

        showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', },
                body: JSON.stringify({ message: messageText }),
            });

            const data = await response.json();

            hideTypingIndicator();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error ${response.status}: ${response.statusText}`);
            }

            addMessage('bot', data.response, data.suggestions);

        } catch (error) {
            hideTypingIndicator();
            console.error('Error sending message:', error);
            addMessage('bot', `😕 Sorry, there was an error: ${error.message}`);
        } finally {
            userInput.disabled = false;
            sendButton.disabled = false;
            clearButton.disabled = false;
            if (micButton) micButton.disabled = false;
            userInput.focus();
        }
    }

    // --- Function to clear chat history ---
    async function clearHistory() {
        // Removed confirm() call
        if (synth.speaking) { synth.cancel(); }
        if (isListening) { stopListening(); }

        clearButton.disabled = true;
        if (micButton) micButton.disabled = true;
        userInput.disabled = true;

        try {
            const response = await fetch('/clear_history', { method: 'POST' });
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                throw new Error(`Failed to clear history (status ${response.status})`);
            }
            chatBox.innerHTML = ''; // Clear everything first
            // Add welcome message back dynamically so speaker button gets added
            addMessage('bot', "History cleared! 👋 How can I help you start fresh? 😊");
            document.querySelectorAll('.inline-suggestions').forEach(el => el.remove());
            console.log("History cleared successfully.");
        } catch (error) {
            console.error('Error clearing history:', error);
            addMessage('bot', `Sorry, couldn't clear history: ${error.message}`);
        } finally {
            clearButton.disabled = false;
            if (micButton) micButton.disabled = false;
            userInput.disabled = false;
            userInput.focus();
        }
    }

    // --- Function to adjust textarea height ---
    function adjustTextareaHeight() {
        userInput.style.height = 'auto'; // Reset height first
        let scrollHeight = userInput.scrollHeight;
        const maxHeight = 120; // Match CSS
        const minHeight = 42; // Match button height approx
        // Calculate new height considering min/max and box sizing
        const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
        userInput.style.height = newHeight + 'px';
    }


    // --- Event listeners ---
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    clearButton.addEventListener('click', clearHistory);
    userInput.addEventListener('input', adjustTextareaHeight);

    // Initial adjustment and focus
    adjustTextareaHeight();
    userInput.focus();
});
