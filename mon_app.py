import os
from werkzeug.utils import secure_filename

from flask import Flask, Response, render_template, request, redirect, url_for, flash, session

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO


from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import ObjectId
from flask_login import login_required, current_user # Pour la sécurité
from functools import wraps
import re
from flask_wtf.csrf import CSRFProtect
from flask_login import login_required, current_user 


app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ultra_securisee_ici'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

csrf = CSRFProtect(app) 

client = MongoClient('localhost', 27017)
db = client['Gestion_contacts']
collection_contacts = db['contacts']
collection_utilisateurs = db['users']

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
    
    def get_id(self):
        return str(self.user_data['_id'])
    
    @property
    def is_admin(self):
        return self.user_data.get('role') == 'admin'

    @property
    def password_reset_required(self):
        return self.user_data.get('password_reset_required', False)

@login_manager.user_loader
def load_user(user_id):
    user_data = collection_utilisateurs.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accès non autorisé : réservé aux administrateurs.', 'danger')
            return redirect(url_for('afficher_donnees'))
        return f(*args, **kwargs)
    return decorated_function

# app.py

# ... (le reste de votre code) ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Après une connexion réussie, vérifiez si le mot de passe doit être réinitialisé
        if current_user.user_data.get('password_reset_required'):
            flash('Votre mot de passe a été réinitialisé par un administrateur. Veuillez en choisir un nouveau.', 'info')
            return redirect(url_for('change_forced_password'))
        # Redirection vers la page 'about' au lieu de 'afficher_donnees'
        return redirect(url_for('about'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = collection_utilisateurs.find_one({'username': username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            # NOUVELLE VÉRIFICATION : L'utilisateur est-il actif ?
            if not user_data.get('is_active', False):
                flash("Votre compte a été désactivé par un administrateur. Vous ne pouvez pas vous connecter.", 'danger')
                return redirect(url_for('login'))
                
            user_obj = User(user_data)
            login_user(user_obj)
            flash('Connexion réussie !', 'success')
            # Vérifiez à nouveau juste après la connexion pour ne pas rater la redirection
            if user_obj.user_data.get('password_reset_required'):
                flash('Votre mot de passe a été réinitialisé par un administrateur. Veuillez en choisir un nouveau.', 'info')
                return redirect(url_for('change_forced_password'))
            # Redirection vers la page 'about' après une connexion réussie
            return redirect(url_for('about'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

# ... (le reste de votre code) ...


# ... (votre code existant) ...
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        security_answer = request.form['security_answer'] # Ajout de la réponse à la question
        if collection_utilisateurs.find_one({'username': username}):
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            hashed_answer = bcrypt.generate_password_hash(security_answer).decode('utf-8') # Hashez la réponse
            new_user = {'username': username, 
                        'password': hashed_password, 
                        'role': 'user', 
                        'security_answer': hashed_answer,
                        'profile_image': 'default-avatar.png', # <--- AJOUTEZ CETTE LIGNE
                        'is_active': True  # <-- Ajout de l'état actif par défaut
                        }
            collection_utilisateurs.insert_one(new_user)
            flash('Compte créé avec succès !', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')



# Route pour l'ajout d'utilisateurs par l'administrateur
@app.route('/ajouter_utilisateur', methods=['GET', 'POST'])
@login_required
@admin_required # Assure que seuls les admins peuvent y accéder
def ajouter_utilisateur():
    if request.method == 'POST':
        username = request.form['username']
        nom = request.form['nom']
        password = request.form['password']
        role = request.form.get('role', 'user')
        
        if collection_utilisateurs.find_one({'username': username}):
            flash("Ce nom d'utilisateur est déjà pris.", 'danger')
            return redirect(url_for('ajouter_utilisateur')) # Redirection pour réafficher le formulaire
        
        # --- Gestion du téléchargement de l'image ---
        profile_image_path = 'images/default-avatar.png' # Chemin par défaut
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Le chemin enregistré est relatif au dossier 'static' de Flask
                profile_image_path = f"images/uploads/{filename}"
            elif file.filename != '':
                # Si le fichier est présent mais non valide (par ex. .exe)
                flash("Format de fichier non autorisé pour l'image de profil.", 'warning')
                # Continue l'ajout de l'utilisateur avec l'image par défaut
        
        # --- Création de l'utilisateur ---
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = {
            'username': username, 
            'nom': nom,
            'password': hashed_password, 
            'role': role,
            'profile_image': profile_image_path,# Sauvegarde le chemin de l'image
            'is_active': True  # <-- Ajout de l'état actif par défaut
        }
        collection_utilisateurs.insert_one(new_user)
        flash(f"L'utilisateur '{username}' a été ajouté avec succès !", 'success')
        return redirect(url_for('liste_utilisateurs'))
    
    return render_template('ajouter_utilisateur.html')

# ... (votre code existant) ...
# ... (votre code existant) ...

@app.route('/modifier_utilisateur/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_utilisateur(user_id):
    utilisateur = collection_utilisateurs.find_one({'_id': ObjectId(user_id)})
    if not utilisateur:
        flash('Utilisateur non trouvé.', 'danger')
        return redirect(url_for('liste_utilisateurs'))

    if request.method == 'POST':
        new_username = request.form['username']
        new_nom = request.form['nom']
        new_role = request.form.get('role', 'user')
        updates = {'username': new_username, 'role': new_role, 'nom': new_nom }

        new_password = request.form.get('password')
        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            updates['password'] = hashed_password
            # Ajout de l'indicateur de réinitialisation forcée
            updates['password_reset_required'] = True
            flash(f"Le mot de passe de '{new_username}' a été réinitialisé. L'utilisateur devra le changer à la prochaine connexion.", 'success')
        else:
            flash(f"L'utilisateur '{new_username}' a été mis à jour (sans changement de mot de passe).", 'success')

        collection_utilisateurs.update_one({'_id': ObjectId(user_id)}, {'$set': updates})
        
        return redirect(url_for('liste_utilisateurs'))

    return render_template('modifier_utilisateur.html', utilisateur=utilisateur)

@app.route('/supprimer_utilisateur/<user_id>')
@login_required  # L'utilisateur doit être connecté
@admin_required  # L'utilisateur doit être un admin
def supprimer_utilisateur(user_id):
    # Sécurité supplémentaire: Empêcher un utilisateur de se supprimer lui-même
    if str(current_user.get_id()) == user_id:
        flash('Vous ne pouvez pas supprimer votre propre compte administrateur.', 'danger')
        return redirect(url_for('liste_utilisateurs'))

    try:
        # Convertir l'ID string en ObjectId pour MongoDB
        result = collection_utilisateurs.delete_one({'_id': ObjectId(user_id)})
        
        if result.deleted_count == 1:
            flash(f"L'utilisateur avec l'ID {user_id} a été supprimé.", 'success')
        else:
            flash("Utilisateur non trouvé.", 'warning')

    except Exception as e:
        flash(f"Une erreur est survenue lors de la suppression: {e}", 'danger')
        
    return redirect(url_for('liste_utilisateurs'))

# ... (le reste de votre code) ...
# ... (le reste des routes) ...

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        security_answer = request.form['security_answer']
        new_password = request.form['new_password']
        
        user_data = collection_utilisateurs.find_one({'username': username})
        if user_data and bcrypt.check_password_hash(user_data.get('security_answer', ''), security_answer):
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            collection_utilisateurs.update_one(
                {'_id': user_data['_id']},
                {'$set': {'password': hashed_password}}
            )
            flash('Votre mot de passe a été réinitialisé avec succès.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Informations incorrectes. Veuillez réessayer.', 'danger')
            
    return render_template('forgot_password.html')
# --- NOUVELLE ROUTE : Réinitialisation par l'administrateur ---

@app.route('/reset_password_admin/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required # Seuls les administrateurs peuvent y accéder
def reset_password_admin(user_id):
    utilisateur = collection_utilisateurs.find_one({'_id': ObjectId(user_id)})
    
    if not utilisateur:
        flash('Utilisateur non trouvé.', 'danger')
        # Rediriger vers la liste des utilisateurs si elle existe
        return redirect(url_for('liste_utilisateurs')) 
    
    # Empêcher un admin de réinitialiser son propre mot de passe via cet outil
    if str(current_user.get_id()) == user_id:
        flash('Vous ne pouvez pas réinitialiser votre propre mot de passe via l\'interface administrateur.', 'warning')
        return redirect(url_for('liste_utilisateurs'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        
        if not new_password:
            flash('Le mot de passe ne peut pas être vide.', 'danger')
            return render_template('renitialiser_mot_de_pass_utilisateur.html', utilisateur=utilisateur)

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Mettre à jour le mot de passe et définir le flag pour forcer le changement à la prochaine connexion
        collection_utilisateurs.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'password': hashed_password,
                'password_reset_required': True # Force l'utilisateur à changer ce mot de passe temporaire
            }}
        )
        
        flash(f"Le mot de passe de l'utilisateur {utilisateur['username']} a été réinitialisé. Il devra le changer à sa prochaine connexion.", 'success')
        # Rediriger vers la liste des utilisateurs si elle existe
        return redirect(url_for('liste_utilisateurs')) 

    # Afficher le formulaire GET
    return render_template('renitialiser_mot_de_pass_utilisateur.html', utilisateur=utilisateur)

# --- FIN NOUVELLE ROUTE ADMIN ---

# ... (votre code existant) ...

@app.route('/change_forced_password', methods=['GET', 'POST'])
@login_required
def change_forced_password():
    if not current_user.user_data.get('password_reset_required'):
        # Si le mot de passe n'a pas besoin d'être changé, redirigez-le
        return redirect(url_for('afficher_donnees'))

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        if bcrypt.check_password_hash(current_user.user_data['password'], old_password):
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            collection_utilisateurs.update_one(
                {'_id': current_user.user_data['_id']},
                {'$set': {'password': hashed_password, 'password_reset_required': False}}
            )
            flash('Votre mot de passe a été mis à jour avec succès.', 'success')
            return redirect(url_for('afficher_donnees'))
        else:
            flash('Ancien mot de passe incorrect.', 'danger')

    return render_template('change_forced_password.html')



##cette code route  permet à l'utilisateur connecté de changer son mot de pass à tout moment 
# app.py

# ... (vos imports existants) ...

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        user_data = collection_utilisateurs.find_one({'_id': ObjectId(current_user.get_id())})

        # 1. Vérifier si le mot de passe actuel est correct
        if not bcrypt.check_password_hash(user_data['password'], current_password):
            flash('Le mot de passe actuel est incorrect.', 'danger')
            return redirect(url_for('change_password'))

        # 2. Vérifier si les nouveaux mots de passe correspondent
        if new_password != confirm_password:
            flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('change_password'))

        # 3. Vérifier la complexité du mot de passe (exemple simple)
        if len(new_password) < 8 or not re.search("[a-z]", new_password) or not re.search("[A-Z]", new_password) or not re.search("[0-9]", new_password):
            flash('Le mot de passe doit contenir au moins 8 caractères, dont une majuscule, une minuscule et un chiffre.', 'danger')
            return redirect(url_for('change_password'))

        # 4. Hacher le nouveau mot de passe et mettre à jour la BDD
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        collection_utilisateurs.update_one(
            {'_id': ObjectId(current_user.get_id())},
            {'$set': {'password': hashed_password, 'password_reset_required': False}}
        )

        # 5. Mettre à jour la session de l'utilisateur (important pour 'password_reset_required')
        updated_user_data = collection_utilisateurs.find_one({'_id': ObjectId(current_user.get_id())})
        login_user(User(updated_user_data)) 

        flash('Votre mot de passe a été modifié avec succès !', 'success')
        return redirect(url_for('profile')) # Rediriger vers la page de profil ou about

    # Pour la méthode GET, afficher le template
    return render_template('change_password.html')

# ... (le reste de votre code app.py) ...



# Protéger la route de liste des utilisateurs
"""@app.route('/utilisateurs')
@login_required
@admin_required
def liste_utilisateurs():
    utilisateurs = list(collection_utilisateurs.find({}, {'password': 0}))
    return render_template('liste_utilisateurs.html', utilisateurs=utilisateurs)
"""
@app.route('/liste_utilisateurs')
@login_required
@admin_required
def liste_utilisateurs():
    utilisateurs = list(collection_utilisateurs.find({}))
    return render_template('liste_utilisateurs.html', utilisateurs=utilisateurs)

# ... (le reste du code) ..
# Dans app.py

@app.route('/toggle_user_status/<user_id>', methods=['POST'])
@login_required
@admin_required # Seuls les admins peuvent utiliser cette fonction
def toggle_user_status(user_id):
    if str(current_user.get_id()) == user_id:
        flash('Vous ne pouvez pas activer ou désactiver votre propre compte.', 'danger')
        return redirect(url_for('liste_utilisateurs'))

    user = collection_utilisateurs.find_one({'_id': ObjectId(user_id)})
    if user:
        # Inverse l'état actuel (True devient False, False devient True)
        new_status = not user.get('is_active', False)
        collection_utilisateurs.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_active': new_status}}
        )
        action = "activé" if new_status else "désactivé"
        flash(f"Le compte de '{user['username']}' a été {action} avec succès.", 'success')
    else:
        flash('Utilisateur non trouvé.', 'danger')

    return redirect(url_for('liste_utilisateurs'))





@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('login'))

# ... (votre code existant) ...

@app.route('/about')
def about():
    """Route pour afficher la page À propos."""
    return render_template('about.html')


@app.route('/profile')
@login_required # S'assure que seul un utilisateur connecté peut accéder à cette page
def profile():
    return render_template('profile.html')



# Définir où stocker les images téléchargées
UPLOAD_FOLDER = 'static/images/uploads'
# S'assurer que le dossier existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Limiter les types de fichiers autorisés
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ... (Le reste de votre code app.py) ...


@app.route('/upload_profile_pic', methods=['GET', 'POST'])
@login_required
def upload_profile_pic():
    if request.method == 'POST':
        # Vérifie si la requête contient bien un fichier 'file'
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Si l'utilisateur n'a pas sélectionné de fichier, le navigateur soumet une partie vide
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Rend le nom de fichier sûr (ex: "My Image.jpg" devient "my_image.jpg")
            filename = secure_filename(file.filename)
            # Génère un nom unique pour éviter les conflits (bonne pratique)
            unique_filename = f"{current_user.get_id()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Mise à jour de MongoDB
            # Le chemin stocké doit être relatif au dossier 'static' pour url_for
            db_path = f"images/uploads/{unique_filename}" 
            collection_utilisateurs.update_one(
                {'_id': ObjectId(current_user.get_id())},
                {'$set': {'profile_image': db_path}}
            )
            flash('Photo de profil mise à jour avec succès !', 'success')
            return redirect(url_for('profile')) # Redirige vers la page de profil
            
        else:
            flash('Type de fichier non autorisé. Utilisez JPG, JPEG, PNG ou GIF.', 'danger')

    # Si c'est une requête GET, ou si quelque chose a mal tourné, rediriger vers le profil
    return redirect(url_for('profile'))


# ... (votre code existant) ...

"""@app.route('/')
@login_required
def afficher_donnees():
    donnees = list(collection_contacts.find())
    return render_template('index.html', donnees=donnees)
"""
# ... (le reste de votre code) ...

"""@app.route('/', methods=['GET'])
@login_required
def afficher_donnees():
    terme_recherche = request.args.get('search_query', '')
    
    if terme_recherche:
        # Recherche insensible à la casse avec $regex
        query = {'Prenom': {'$regex': terme_recherche, '$options': 'i'}}
        donnees = list(collection_contacts.find(query))
    else:
        donnees = list(collection_contacts.find())
        
    return render_template('index.html', donnees=donnees, terme_recherche=terme_recherche)"""

#modification
def obtenir_contacts(search_query):
    """Fonction utilitaire pour récupérer les contacts en fonction de la recherche."""
    if search_query:
        # Recherche insensible à la casse et qui commence par la chaîne
        pattern = re.compile(f'^{re.escape(search_query)}', re.IGNORECASE)
        contacts = collection_contacts.find({'$or': [
            {'Prenom': {'$regex': pattern}},
            {'Nom': {'$regex': pattern}}
        ]})
    else:
        contacts = collection_contacts.find()
    return list(contacts)

# ... (Vos fonctions utilitaires, classes User, login_manager, etc. restent inchangées) ...

# --- Fonction utilitaire pour interroger la base de données ---
def obtenir_contacts_filtres(criteres_recherche=None):
    """
    Récupère les contacts de la base de données en fonction des critères de recherche.
    """
    mongo_query = {}

    if criteres_recherche:
        search_query = criteres_recherche.get('search_query', '')
        if search_query:
            # Recherche simple sur le prénom uniquement (comme dans votre HTML original)
            mongo_query['Prenom'] = {'$regex': search_query, '$options': 'i'}
        else:
            # Gestion de la recherche avancée
            for key, value in criteres_recherche.items():
                if value and key not in ['search_query', 'csrf_token']: # Ignorer les champs vides et le token CSRF
                    if key == 'age':
                        try:
                            mongo_query['Age'] = int(value)
                        except ValueError:
                            continue
                    # Assurez-vous que les clés correspondent aux noms de vos champs MongoDB (ex: 'Prenom', 'Nom', etc.)
                    elif key in ['Prenom', 'Nom', 'Address', 'Telephone']:
                        mongo_query[key.capitalize()] = {'$regex': value, '$options': 'i'}
    
    return list(collection_contacts.find(mongo_query))


# --- Route Afficher Données (Recherche Simple) ---
@app.route('/')
@app.route('/contacts')
@login_required
def afficher_donnees():
    # Capture tous les arguments de l'URL (même s'il n'y a que search_query)
    current_search_args = request.args.to_dict()
    
    # Stocker les critères actuels (simple) dans la session
    session['derniers_criteres_recherche'] = current_search_args
    
    donnees = obtenir_contacts_filtres(current_search_args)
    
    search_query = current_search_args.get('search_query', '')
    terme_recherche = f"'{search_query}'" if search_query else None
    
    return render_template('index.html', donnees=donnees, terme_recherche=terme_recherche, search_query=search_query)


# --- Route Recherche Avancée ---
@app.route('/recherche-avancee-resultats', methods=['GET'])
@login_required
def recherche_avancee_resultats():
    # Capture tous les arguments de l'URL (prenom, nom, age, etc.)
    query_params = request.args.to_dict()
    
    # Stocker les critères actuels (avancés) dans la session
    session['derniers_criteres_recherche'] = query_params
    
    donnees = obtenir_contacts_filtres(query_params)
    
    # Prépare un terme de recherche affichable pour le template
    terme_recherche = ", ".join([f"{k}: {v}" for k, v in query_params.items() if v]) or "Tous"
    
    # On passe terme_recherche au template, et un search_query vide pour ne pas perturber le bouton PDF
    return render_template('index.html', donnees=donnees, terme_recherche=terme_recherche, search_query="")


# --- ROUTE UNIQUE DE TÉLÉCHARGEMENT PDF ---
""" @app.route('/telecharger-pdf')
@login_required
def telecharger_pdf():
    # Récupérer les derniers critères de recherche depuis la session, par défaut un dict vide s'il n'y a rien
    criteres_recherche = session.get('derniers_criteres_recherche', {})
    
    # Utiliser la fonction unifiée pour récupérer exactement les mêmes données que celles affichées
    contacts = obtenir_contacts_filtres(criteres_recherche) 

    # --- Code ReportLab ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Déterminer le titre du PDF en fonction des critères stockés
    if criteres_recherche.get('search_query'):
        title_text = f"Liste des contacts (Recherche simple : '{criteres_recherche['search_query']}')"
    elif any(v for k, v in criteres_recherche.items()):
         terme_recherche_affichage = ", ".join([f"{k}: {v}" for k, v in criteres_recherche.items() if v])
         title_text = f"Liste des contacts (Recherche avancée : {terme_recherche_affichage})"
    else:
        title_text = "Liste complète des contacts"

    story.append(Paragraph(title_text, styles['Title']))
    story.append(Spacer(1, 12))

    # Préparation et style du tableau (votre code existant)
    data = [['Prenom', 'Nom', 'Address', 'Téléphone']]
    for contact in contacts:
        data.append([ 
            contact.get('Prenom', ''), contact.get('Nom', ''), 
            contact.get('Address', ''), contact.get('Telephone', '') 
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        # ... (autres styles que vous aviez) ...
    ]))
    story.append(table)

    # Génération et retour du PDF
    doc.build(story)
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=contacts_resultats_affiches.pdf'}
    )
 """

# --- ROUTE UNIQUE D'AFFICHAGE/TÉLÉCHARGEMENT PDF ---
@app.route('/afficher-pdf') # Optionnel: vous pouvez changer l'URL pour plus de clarté
@login_required
def afficher_pdf(): # Optionnel: vous pouvez changer le nom de la fonction
    # Récupérer les derniers critères de recherche depuis la session, par défaut un dict vide s'il n'y a rien
    criteres_recherche = session.get('derniers_criteres_recherche', {})
    
    # Utiliser la fonction unifiée pour récupérer exactement les mêmes données que celles affichées
    contacts = obtenir_contacts_filtres(criteres_recherche) 

    # --- Code ReportLab (inchangé) ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Déterminer le titre du PDF en fonction des critères stockés (inchangé)
    if criteres_recherche.get('search_query'):
        title_text = f"Liste des contacts (Recherche simple : '{criteres_recherche['search_query']}')"
    elif any(v for k, v in criteres_recherche.items()):
         terme_recherche_affichage = ", ".join([f"{k}: {v}" for k, v in criteres_recherche.items() if v])
         title_text = f"Liste des contacts (Recherche avancée : {terme_recherche_affichage})"
    else:
        title_text = "Liste complète des contacts"

    story.append(Paragraph(title_text, styles['Title']))
    story.append(Spacer(1, 12))

    # Préparation et style du tableau (inchangé)
    data = [['Prenom', 'Nom', 'Address', 'Téléphone']]
    for contact in contacts:
        data.append([ 
            contact.get('Prenom', ''), contact.get('Nom', ''), 
            contact.get('Address', ''), contact.get('Telephone', '') 
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), 
        # ... (autres styles que vous aviez) ...
    ]))
    story.append(table)

    # Génération et retour du PDF
    doc.build(story)
    buffer.seek(0)
    
    # --- LA MODIFICATION CLÉ EST ICI ---
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        # Remplacez 'attachment' par 'inline'
        headers={'Content-Disposition': 'inline;filename=contacts_resultats_affiches.pdf'}
    )




""" @app.route('/')
@login_required
def afficher_donnees():
    search_query = request.args.get('search_query', '')
    donnees = obtenir_contacts(search_query)
    # Passe la search_query au template pour maintenir l'état du champ de recherche dans la page HTML
    return render_template('index.html', donnees=donnees, search_query=search_query)


@app.route('/telecharger-pdf')
@login_required
def telecharger_pdf():
    search_query = request.args.get('search_query', '')
    contacts = obtenir_contacts(search_query)

    # Création du document PDF en mémoire
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Titre du document
    title_style = styles['Title']
    if search_query:
        title_text = f"Liste des contacts (Recherche : '{search_query}')"
    else:
        title_text = "Liste complète des contacts"
        
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 12))

    # Préparation des données pour le tableau
    data = [['Prenom', 'Nom', 'Address', 'Téléphone']] # En-têtes du tableau
    for contact in contacts:
        # Assurez-vous que ces clés correspondent à celles de votre base de données MongoDB
        data.append([
            contact.get('Prenom', ''),
            contact.get('Nom', ''),
            contact.get('Address', ''),
            contact.get('Telephone', '')
        ])

    # Création du tableau
    table = Table(data)
    # Style du tableau (optionnel, pour l'esthétisme)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)

    # Génération du PDF
    doc.build(story)

    # Récupération du contenu du buffer et création de la réponse HTTP
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=contacts.pdf'}
    )

 """
# Route pour la recherche avançéé
""" @app.route('/recherche_avancee_resultats', methods=['GET'])
def recherche_avancee_resultats():
    
    
    # 1. Récupérer les paramètres du formulaire
    prenom = request.args.get('prenom', '').strip()
    nom = request.args.get('nom', '').strip()
    age_str = request.args.get('age', '').strip()
    address = request.args.get('address', '').strip()
    telephone = request.args.get('telephone', '').strip()
    
    # 2. Construire la requête de filtre pour la base de données (logique AND flexible)
    filtre = {}
    if prenom:
        filtre['Prenom'] = {"$regex": prenom, "$options": "i"}
    if nom:
        filtre['Nom'] = {"$regex": nom, "$options": "i"}
    if address:
        filtre['Address'] = {"$regex": address, "$options": "i"}
    if telephone:
        filtre['Telephone'] = {"$regex": telephone, "$options": "i"}
    
    if age_str.isdigit():
        age = int(age_str)
        filtre['Age'] = {"$gte": age}

    # 3. Exécuter la requête
    donnees_resultats = list(collection_contacts.find(filtre))
    
    # 4. Préparer le message d'affichage pour la template
    criteres = [c for c in [prenom, nom, age_str, address, telephone] if c]
    terme_recherche_affichage = ", ".join(criteres) if criteres else "Tous les contacts"

    # 5. Renvoyer les résultats à la template `index.html`
    # On réutilise la même template mais avec les données filtrées
    return render_template(
        'index.html', 
        donnees=donnees_resultats, 
        terme_recherche=terme_recherche_affichage,
        # Assurez-vous que search_query est défini pour les autres parties du HTML (ex: lien PDF)
        search_query="" 
    )
 """


""" @app.route('/')
@login_required
def afficher_donnees():
    search_query = request.args.get('search_query', '')
    
    if search_query:
        # Recherche insensible à la casse et qui commence par la chaîne
        pattern = re.compile(f'^{re.escape(search_query)}', re.IGNORECASE)
        # Utilisation d'une expression régulière pour une recherche plus flexible
        contacts = collection_contacts.find({'$or': [
            {'Prenom': {'$regex': pattern}},
            {'Nom': {'$regex': pattern}}
        ]})
    else:
        contacts = collection_contacts.find()
    
    donnees = list(contacts)
    return render_template('index.html', donnees=donnees) """

# ... (le reste de votre code) ...


"""@app.route('/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter():
    if request.method == 'POST':
        Prenom = request.form['prenom']
        Nom = request.form['nom']
        Age = request.form['age']
        Address = request.form['address']
        Telephone = request.form['telephone']
        nouveau_contact = {"Prenom": Prenom, "Nom": Nom, "Age": Age, "Address": Address, "Telephone": Telephone}
        collection_contacts.insert_one(nouveau_contact)
        flash('Contact ajouté avec succès !', 'success')
        return redirect(url_for('afficher_donnees'))
    return render_template('ajouter.html')"""

@app.route('/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter():
    if request.method == 'POST':
        # Utilisez .get() pour éviter les erreurs si un champ est manquant
        prenom = request.form.get('prenom', '').strip() 
        nom = request.form.get('nom', '').strip()
        age_str = request.form.get('age', '')
        address = request.form.get('address', '').strip()
        telephone = request.form.get('telephone', '').strip()

        erreurs = []
        if not prenom:
            erreurs.append("Le prénom est requis.")
        if not nom:
            erreurs.append("Le nom est requis.")
        if not address:
            erreurs.append("L'adresse est requise.")
        if not telephone:
            erreurs.append("Le téléphone est requis.")
            
        # Validation spécifique de l'âge côté serveur
        try:
            age = int(age_str)
            if age <= 0:
                erreurs.append("L'âge doit être un nombre positif.")
        except ValueError:
            erreurs.append("L'âge doit être un nombre valide.")

        if erreurs:
            # Si des erreurs existent, affichez-les et renvoyez le formulaire
            for erreur in erreurs:
                flash(erreur, 'danger')
            # Conservez les données saisies dans le formulaire après redirection
            return render_template('ajouter.html', form_data=request.form)
        
        # Si aucune erreur, insérez dans la base de données
        nouveau_contact = {
            "Prenom": prenom,
            "Nom": nom,
            "Age": age, # Utilisez l'âge converti
            "Address": address,
            "Telephone": telephone
        }
        collection_contacts.insert_one(nouveau_contact)
        flash("Contact ajouté avec succès!", 'success')
        return redirect(url_for('afficher_donnees'))
        
    return render_template('ajouter.html')

""" 
@app.route('/modifier_item/<item_id>', methods=['GET', 'POST'])
@login_required
def modifier_item(item_id):
    item = collection_contacts.find_one({'_id': ObjectId(item_id)})
    if request.method == 'POST':
        Prenom = request.form['prenom']
        Nom = request.form['nom']
        Age = request.form['age']
        Address = request.form['address']
        Telephone = request.form['telephone']
        collection_contacts.update_one({'_id': ObjectId(item_id)}, {'$set': {"Prenom": Prenom, "Nom": Nom, "Age": Age, "Address": Address, "Telephone": Telephone}})
        flash('Contact modifié avec succès !', 'success')
        return redirect(url_for('afficher_donnees'))
    return render_template('modifier_item.html', item=item) """

@app.route('/modifier/<item_id>', methods=['GET', 'POST'])
@login_required
def modifier_item(item_id):
    # ... (Logique pour trouver le contact par ID) ...
    # Assurez-vous d'utiliser ObjectId si vous êtes sur MongoDB
    try:
        contact_id = ObjectId(item_id)
    except Exception:
        flash("ID de contact invalide.", "danger")
        return redirect(url_for('afficher_donnees'))
        
    item = collection_contacts.find_one({"_id": contact_id})

    if request.method == 'POST':
        # --- (Logique de mise à jour de la base de données) ---
        nouveau_prenom = request.form['prenom']
        nouveau_nom = request.form['nom']
        # ... récupérer les autres champs ...

        collection_contacts.update_one(
            {"_id": contact_id},
            {"$set": {
                "Prenom": nouveau_prenom,
                "Nom": nouveau_nom,
                # ... autres mises à jour ...
            }}
        )
        flash("Contact mis à jour avec succès !", "success")
        # --------------------------------------------------------

        # === POINT CLÉ : Redirection intelligente ===
        if 'derniers_criteres_recherche' in session and session['derniers_criteres_recherche']:
            # S'il y a des critères de recherche stockés, redirigez vers la route des résultats avancés
            # en passant les critères comme arguments d'URL (grâce à **kwargs)
            return redirect(url_for('recherche_avancee_resultats', **session['derniers_criteres_recherche']))
        else:
            # Sinon, redirigez simplement vers la liste complète
            return redirect(url_for('afficher_donnees'))

    # Pour la méthode GET (affichage du formulaire de modification)
    return render_template('modifier_item.html', item=item)


""" @app.route('/supprimer/<id>')
@login_required
def supprimer_document(id):
    collection_contacts.delete_one({'_id': ObjectId(id)})
    flash('Contact supprimé avec succès !', 'success')
    return redirect(url_for('afficher_donnees')) """

@app.route('/supprimer_document/<id>', methods=['POST', 'GET']) # Utilisez POST de préférence pour la suppression
@login_required
def supprimer_document(id):
    # ... (Logique pour supprimer le contact) ...
    try:
        collection_contacts.delete_one({"_id": ObjectId(id)})
        flash("Contact supprimé avec succès !", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression : {e}", "danger")
    
    # === POINT CLÉ : Redirection intelligente après suppression ===
    if 'derniers_criteres_recherche' in session and session['derniers_criteres_recherche']:
        return redirect(url_for('recherche_avancee_resultats', **session['derniers_criteres_recherche']))
    else:
        return redirect(url_for('afficher_donnees'))


if __name__ == '__main__':
    app.run(debug=True)







""" from flask import Flask, render_template, request, redirect, url_for,flash,session, jsonify
#from flask_bcrypt import Bcrypt
from pymongo import MongoClient
#from bson.objectid import ObjectId
from bson import ObjectId

app = Flask(__name__)
#app.secret_key = "votre_cle_secrete"
#bcrypt = Bcrypt(app)


client = MongoClient('localhost', 27017)
db = client['Gestion_contacts']
collection = db['contacts']




@app.route('/')
def afficher_donnees():
    # Récupérer tous les documents de la collection
    donnees = list(collection.find())
    # Passer les données au template HTML
    return render_template('index.html', donnees=donnees)



@app.route('/ajouter', methods=['GET', 'POST'])
def ajouter():
    if request.method=='POST':
        Prenom = request.form['prenom']
        Nom = request.form['nom']
        Age = request.form['age']
        Address = request.form['address']
        Telephone = request.form['telephone']
        nouveau_contact ={"Prenom":Prenom, "Nom":Nom, "Age":Age, "Address":Address, "Telephone":Telephone}
        collection.insert_one(nouveau_contact)
        
    return render_template('ajouter.html')
 
@app.route('/modifier_item/<item_id>', methods=['GET', 'POST'])
def modifier_item(item_id):
    item = collection.find_one({'_id': ObjectId(item_id)})
    if request.method =='POST':
        Prenom = request.form['prenom']
        Nom = request.form['nom']
        Age = request.form['age']
        Address = request.form['address']
        Telephone = request.form['telephone']
        
        collection.update_one({'_id': ObjectId(item_id)}, {'$set': {"Prenom":Prenom, "Nom":Nom, "Age":Age, "Address":Address, "Telephone":Telephone}})
       
    return render_template('modifier_item.html', item=item) 


@app.route('/supprimer/<id>')
def supprimer_document(id):
        # Convertir l'ID string en ObjectId pour MongoDB
        ObjectId(id)
        collection.delete_one({'_id': ObjectId(id)})
        return redirect(url_for('afficher_donnees'))

if __name__ == '__main__':
    app.run(debug=True) 
 """