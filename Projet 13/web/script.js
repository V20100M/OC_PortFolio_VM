const API_BASE_URL = "http://localhost:8000";

const sectionAPropos = document.getElementById("section-a-propos");
const sectionInscription = document.getElementById("section-inscription");
const zoneConnexion = document.getElementById("zone-connexion");
const zoneUtilisateur = document.getElementById("zone-utilisateur");
const texteBienvenue = document.getElementById("texte-bienvenue");
const messageErreur = document.getElementById("message-erreur");

function afficherErreur(texte) {
    messageErreur.textContent = texte;
    messageErreur.hidden = false;
}

function masquerErreur() {
    messageErreur.hidden = true;
}

function afficherInscription() {
    sectionAPropos.classList.remove("section-active");
    sectionAPropos.classList.add("section-inactive");
    sectionInscription.classList.remove("section-inactive");
    sectionInscription.classList.add("section-active");
    masquerErreur();
}

function afficherAPropos() {
    sectionInscription.classList.remove("section-active");
    sectionInscription.classList.add("section-inactive");
    sectionAPropos.classList.remove("section-inactive");
    sectionAPropos.classList.add("section-active");
    masquerErreur();
}

function enregistrerSession(data) {
    localStorage.setItem("pulsevents_token", data.access_token);
    localStorage.setItem("pulsevents_prenom", data.prenom);
    localStorage.setItem("pulsevents_ville", data.ville);
    afficherEtatConnecte(data.prenom);
}

function afficherEtatConnecte(prenom) {
    zoneConnexion.hidden = true;
    zoneUtilisateur.hidden = false;
    texteBienvenue.textContent = `Bonjour ${prenom}`;
    afficherAPropos(); // force le retour au contenu "à propos", masque l'inscription si elle était affichée
}

function afficherEtatDeconnecte() {
    zoneConnexion.hidden = false;
    zoneUtilisateur.hidden = true;
    document.getElementById("form-login").reset();
    afficherAPropos(); // repart proprement sur l'écran "à propos"
}

// Restaurer la session si un token est déjà présent (rechargement de page)
const tokenExistant = localStorage.getItem("pulsevents_token");
if (tokenExistant) {
    afficherEtatConnecte(localStorage.getItem("pulsevents_prenom"));
} else {
    afficherEtatDeconnecte();
}

document.getElementById("btn-afficher-inscription").addEventListener("click", afficherInscription);
document.getElementById("btn-retour-a-propos").addEventListener("click", afficherAPropos);

document.getElementById("btn-deconnexion").addEventListener("click", () => {
    localStorage.removeItem("pulsevents_token");
    localStorage.removeItem("pulsevents_prenom");
    localStorage.removeItem("pulsevents_ville");
    afficherEtatDeconnecte();
});

document.getElementById("form-login").addEventListener("submit", async (event) => {
    event.preventDefault();
    masquerErreur();

    const login = document.getElementById("login-login").value;
    const mdp = document.getElementById("login-mdp").value;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ login, mdp }),
        });

        if (!response.ok) {
            const erreur = await response.json();
            afficherErreur(erreur.detail || "Identifiants incorrects.");
            return;
        }

        const data = await response.json();
        enregistrerSession(data);
    } catch (e) {
        afficherErreur("Impossible de contacter le serveur.");
    }
});

document.getElementById("form-inscription").addEventListener("submit", async (event) => {
    event.preventDefault();
    masquerErreur();

    const payload = {
        nom: document.getElementById("inscription-nom").value,
        prenom: document.getElementById("inscription-prenom").value,
        age: parseInt(document.getElementById("inscription-age").value, 10),
        code_postal: document.getElementById("inscription-code-postal").value,
        ville: document.getElementById("inscription-ville").value,
        mail: document.getElementById("inscription-mail").value,
        login: document.getElementById("inscription-login").value,
        mdp: document.getElementById("inscription-mdp").value,
    };

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const erreur = await response.json();
            afficherErreur(erreur.detail || "Erreur lors de l'inscription.");
            return;
        }

        const data = await response.json();
        enregistrerSession(data);
    } catch (e) {
        afficherErreur("Impossible de contacter le serveur.");
    }
});