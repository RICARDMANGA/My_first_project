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







from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
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
            new_user = {'username': username, 'password': hashed_password, 'role': 'user', 'security_answer': hashed_answer}
            collection_utilisateurs.insert_one(new_user)
            flash('Compte créé avec succès !', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')


# Ajout d'une route pour l'ajout d'utilisateurs par l'administrateur
@app.route('/ajouter_utilisateur', methods=['GET', 'POST'])
@login_required
@admin_required
def ajouter_utilisateur():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user') # Rôle par défaut 'user'
        
        if collection_utilisateurs.find_one({'username': username}):
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = {'username': username, 'password': hashed_password, 'role': role}
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
        new_role = request.form.get('role', 'user')
        updates = {'username': new_username, 'role': new_role}

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

# ... (le reste du code) ...




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


@app.route('/')
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
    return render_template('index.html', donnees=donnees)

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
    return render_template('modifier_item.html', item=item)

@app.route('/supprimer/<id>')
@login_required
def supprimer_document(id):
    collection_contacts.delete_one({'_id': ObjectId(id)})
    flash('Contact supprimé avec succès !', 'success')
    return redirect(url_for('afficher_donnees'))

if __name__ == '__main__':
    app.run(debug=True)
