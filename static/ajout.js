/* document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const tableBody = document.getElementById('contactTableBody'); // L'ID de l'élément <tbody> de la table

    if (searchInput && tableBody) {
        searchInput.addEventListener('input', (event) => {
            const searchQuery = event.target.value.toLowerCase();
            const rows = tableBody.getElementsByTagName('tr');

            for (const row of rows) {
                const prenomCell = row.cells[0]; // La première cellule contient le prénom
                if (prenomCell) {
                    const prenomText = prenomCell.textContent.toLowerCase();
                    if (prenomText.startsWith(searchQuery)) {
                        row.style.display = ''; // Affiche la ligne
                    } else {
                        row.style.display = 'none'; // Cache la ligne
                    }
                }
            }
        });
    }
});
 */


document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('contactForm');

    form.addEventListener('submit', (event) => {
        event.preventDefault(); // Empêche l'envoi du formulaire par défaut

        let isValid = true;
        const fields = [
            { id: 'prenom', name: 'prénom' },
            { id: 'nom', name: 'nom' },
            { id: 'age', name: 'âge' },
            { id: 'address', name: 'adresse' },
            { id: 'telephone', name: 'téléphone' }
        ];

        clearErrors();

        fields.forEach(field => {
            const inputElement = document.getElementById(field.id);
            const errorElement = document.getElementById(`${field.id}Error`);

            if (inputElement.value.trim() === '') {
                isValid = false;
                displayError(inputElement, errorElement, `Le champ ${field.name} est requis.`);
            }
        });

        // Validation spécifique pour l'âge (doit être un nombre positif)
        const ageInput = document.getElementById('age');
        const ageError = document.getElementById('ageError');
        if (ageInput.value.trim() !== '' && (isNaN(ageInput.value) || parseInt(ageInput.value) <= 0)) {
            isValid = false;
            displayError(ageInput, ageError, "L'âge doit être un nombre entier positif.");
        }

        if (isValid) {
            form.submit(); // Si valide, soumet le formulaire
        }
    });

    function displayError(inputElement, errorElement, message) {
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
        if (inputElement) {
            inputElement.classList.add('error-border'); // Ajoute une classe CSS pour la bordure rouge
        }
    }

    function clearErrors() {
        document.querySelectorAll('.error-message').forEach(el => {
            el.textContent = '';
            el.style.display = 'none';
        });
        document.querySelectorAll('.error-border').forEach(el => {
            el.classList.remove('error-border');
        });
    }
});
