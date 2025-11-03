

document.addEventListener('DOMContentLoaded', () => {
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
