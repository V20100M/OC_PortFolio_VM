(function () {
    const API_BASE_URL = "http://localhost:8000";
    const GEO_API_COMMUNES_URL = "https://geo.api.gouv.fr/communes";

    const state = {
        geoField: null,
        geoValue: null,
        conversationId: null,
        messages: [],
        size: localStorage.getItem("pe_widget_size") || "medium",
        position: localStorage.getItem("pe_widget_position") || "right",
        villeInitiale: null,
    };

    // --- Construction du DOM ---
    const button = document.createElement("button");
    button.id = "pe-widget-button";
    button.textContent = "💬";
    document.body.appendChild(button);

    const panel = document.createElement("div");
    panel.id = "pe-widget-panel";
    panel.className = `pe-hidden pe-size-${state.size} pe-pos-${state.position}`;
    panel.innerHTML = `
        <div class="pe-header">
            <span class="pe-header-title">Puls-Events</span>
            <div class="pe-header-controls">
                <button id="pe-size-btn" title="Changer la taille">Taille</button>
                <button id="pe-pos-btn" title="Changer le côté">Côté</button>
                <button id="pe-reset-btn" title="Réinitialiser">↺</button>
                <button id="pe-close-btn" title="Fermer">✕</button>
            </div>
        </div>
        <div id="pe-body"></div>
    `;
    document.body.appendChild(panel);

    const body = panel.querySelector("#pe-body");

    button.addEventListener("click", () => {
        panel.classList.toggle("pe-hidden");
        if (!panel.classList.contains("pe-hidden") && state.messages.length === 0) {
            initConversation();
        }
    });
    panel.querySelector("#pe-close-btn").addEventListener("click", () => {
        panel.classList.add("pe-hidden");
    });

    const sizes = ["small", "medium", "large"];
    panel.querySelector("#pe-size-btn").addEventListener("click", () => {
        const idx = (sizes.indexOf(state.size) + 1) % sizes.length;
        panel.classList.remove(`pe-size-${state.size}`);
        state.size = sizes[idx];
        panel.classList.add(`pe-size-${state.size}`);
        localStorage.setItem("pe_widget_size", state.size);
    });

    panel.querySelector("#pe-pos-btn").addEventListener("click", () => {
        state.position = state.position === "right" ? "left" : "right";
        panel.classList.remove("pe-pos-left", "pe-pos-right");
        panel.classList.add(`pe-pos-${state.position}`);
        localStorage.setItem("pe_widget_position", state.position);
    });

    panel.querySelector("#pe-reset-btn").addEventListener("click", () => {
        state.size = "medium";
        state.position = "right";
        panel.classList.remove("pe-size-small", "pe-size-large", "pe-pos-left");
        panel.classList.add("pe-size-medium", "pe-pos-right");
        localStorage.setItem("pe_widget_size", "medium");
        localStorage.setItem("pe_widget_position", "right");
    });

    // --- Géolocalisation / initialisation de la conversation ---
    function initConversation() {
        const token = localStorage.getItem("pulsevents_token");
        const villeCompte = localStorage.getItem("pulsevents_ville");
        const prenom = localStorage.getItem("pulsevents_prenom");

        if (token && villeCompte) {
            // Utilisateur connecté : ville déjà connue, pas besoin de géoloc IP mais confirmation
            // toujours demandée (l'utilisateur peut vouloir chercher ailleurs).
            resolveCommune(villeCompte).then((commune) => {
                if (commune) {
                    showAccountCityConfirm(commune, prenom);
                } else {
                    renderGeolocFlow();
                }
            });
        } else {
            renderGeolocFlow();
        }
    }

    function showAccountCityConfirm(commune, prenom) {
        body.innerHTML = `
            <div class="pe-geoloc-box">
                <p>Bonjour ${prenom} ! Recherchons-nous près de <strong>${commune.ville}</strong> (votre ville enregistrée) ?</p>
                <div style="display:flex; gap:8px;">
                    <button id="pe-geo-oui">Oui</button>
                    <button id="pe-geo-non">Non, autre ville</button>
                </div>
            </div>
        `;
        body.querySelector("#pe-geo-oui").addEventListener("click", () => showRadiusChoice(commune));
        body.querySelector("#pe-geo-non").addEventListener("click", renderManualSearch);
    }

    async function detectIpCity() {
        try {
            const res = await fetch("https://ipwho.is/");
            const data = await res.json();
            if (data.success === false) return null;
            return data.city || null;
        } catch (e) {
            return null;
        }
    }

    async function resolveCommune(nom) {
        try {
            const url = `${GEO_API_COMMUNES_URL}?nom=${encodeURIComponent(nom)}&fields=nom,departement,region&boost=population&limit=1`;
            const res = await fetch(url);
            const results = await res.json();
            if (!results.length) return null;
            const c = results[0];
            return {
                ville: c.nom,
                departement: c.departement ? c.departement.nom : null,
                region: c.region ? c.region.nom : null,
            };
        } catch (e) {
            return null;
        }
    }

    async function searchCommunes(query) {
        try {
            const url = `${GEO_API_COMMUNES_URL}?nom=${encodeURIComponent(query)}&fields=nom,departement,region&boost=population&limit=8`;
            const res = await fetch(url);
            return await res.json();
        } catch (e) {
            return [];
        }
    }

    async function renderGeolocFlow() {
        body.innerHTML = `<div class="pe-geoloc-box"><p>Localisation en cours...</p></div>`;
        const city = await detectIpCity();
        const commune = city ? await resolveCommune(city) : null;

        if (commune) {
            body.innerHTML = `
                <div class="pe-geoloc-box">
                    <p>Nous vous situons à <strong>${commune.ville}</strong>. Est-ce correct ?</p>
                    <div style="display:flex; gap:8px;">
                        <button id="pe-geo-oui">Oui</button>
                        <button id="pe-geo-non">Non, corriger</button>
                    </div>
                </div>
            `;
            body.querySelector("#pe-geo-oui").addEventListener("click", () => showRadiusChoice(commune));
            body.querySelector("#pe-geo-non").addEventListener("click", renderManualSearch);
        } else {
            renderManualSearch();
        }
    }

    function renderManualSearch() {
        body.innerHTML = `
            <div class="pe-geoloc-box">
                <p>Indiquez votre ville :</p>
                <input type="text" id="pe-ville-input" placeholder="Nom de la ville">
                <select id="pe-ville-select" style="display:none;"></select>
                <button id="pe-ville-valider" style="display:none;">Valider</button>
            </div>
        `;
        const input = body.querySelector("#pe-ville-input");
        const select = body.querySelector("#pe-ville-select");
        const validerBtn = body.querySelector("#pe-ville-valider");
        let currentResults = [];

        input.addEventListener("input", async () => {
            if (input.value.length < 2) return;
            currentResults = await searchCommunes(input.value);
            if (currentResults.length) {
                select.innerHTML = currentResults.map((c, i) => `<option value="${i}">${c.nom}</option>`).join("");
                select.style.display = "block";
                validerBtn.style.display = "block";
            }
        });

        validerBtn.addEventListener("click", () => {
            const c = currentResults[select.value];
            const commune = {
                ville: c.nom,
                departement: c.departement ? c.departement.nom : null,
                region: c.region ? c.region.nom : null,
            };
            showRadiusChoice(commune);
        });
    }

    function showRadiusChoice(commune) {
        body.innerHTML = `
            <div class="pe-geoloc-box">
                <p>Ville : <strong>${commune.ville}</strong><br>
                   Département : <strong>${commune.departement || "N/A"}</strong><br>
                   Région : <strong>${commune.region || "N/A"}</strong></p>
                <select id="pe-niveau">
                    <option value="location_city">Ville</option>
                    <option value="location_department" selected>Département</option>
                    <option value="location_region">Région</option>
                </select>
                <button id="pe-valider-niveau">Rechercher les événements</button>
            </div>
        `;
        body.querySelector("#pe-valider-niveau").addEventListener("click", () => {
            const niveau = body.querySelector("#pe-niveau").value;
            const valeurParNiveau = {
                location_city: commune.ville,
                location_department: commune.departement,
                location_region: commune.region,
            };
            state.geoField = niveau;
            state.geoValue = valeurParNiveau[niveau];
            state.villeInitiale = commune.ville;
            renderChat(`Voici les événements près de ${commune.ville} !`);
        });
    }

    // --- Interface de chat ---
    function renderChat(introMessage) {
        body.innerHTML = `
            <div class="pe-messages" id="pe-messages"></div>
            <div class="pe-input-row">
                <input type="text" id="pe-chat-input" placeholder="Posez votre question...">
                <button id="pe-chat-send">Envoyer</button>
            </div>
        `;
        if (introMessage) {
            addMessage("assistant", introMessage, null);
        }

        const input = body.querySelector("#pe-chat-input");
        const sendBtn = body.querySelector("#pe-chat-send");

        function send() {
            const text = input.value.trim();
            if (!text) return;
            input.value = "";
            addMessage("user", text, null);
            sendToBackend(text);
        }

        sendBtn.addEventListener("click", send);
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") send();
        });
    }

    function formatMarkdownLite(text) {
        // Conversion minimale : gras (**texte**) et sauts de ligne.
        // Suffisant pour les réponses du chatbot, sans dépendance externe.
        const escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    }

    function addMessage(role, text, interactionId) {
        state.messages.push({ role, text, interactionId });
        const messagesEl = body.querySelector("#pe-messages");
        const wrapper = document.createElement("div");
        wrapper.className = `pe-message pe-${role}`;
        wrapper.innerHTML = formatMarkdownLite(text);

        if (role === "assistant" && interactionId != null) {
            const feedbackRow = document.createElement("div");
            feedbackRow.style.marginTop = "6px";
            feedbackRow.innerHTML = `
                <button class="pe-feedback-btn" data-feedback="positif">👍</button>
                <button class="pe-feedback-btn" data-feedback="negatif">👎</button>
            `;
            feedbackRow.querySelectorAll(".pe-feedback-btn").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    await sendFeedback(interactionId, btn.dataset.feedback);
                    feedbackRow.innerHTML = "<span style='font-size:12px;'>Merci pour votre retour !</span>";
                });
            });
            wrapper.appendChild(feedbackRow);
        }

        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function sendFeedback(interactionId, feedback) {
        try {
            await fetch(`${API_BASE_URL}/feedback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ interaction_id: interactionId, feedback }),
            });
        } catch (e) {
            // silencieux : le feedback est un bonus, pas critique
        }
    }

    async function sendToBackend(message) {
        const token = localStorage.getItem("pulsevents_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        try {
            const res = await fetch(`${API_BASE_URL}/chat`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    message,
                    geo_field: state.geoField,
                    geo_value: state.geoValue,
                    ville_initiale: state.villeInitiale,
                    conversation_id: state.conversationId,
                }),
            });
            const data = await res.json();
            state.conversationId = data.conversation_id;
            addMessage("assistant", data.response, data.interaction_id);
        } catch (e) {
            addMessage("assistant", "Désolé, une erreur est survenue.", null);
        }
    }
})();