"""from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']

"""





from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ultra_securisee_ici'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

client = MongoClient('localhost', 27017)
db = client['Gestion_contacts']
collection_contacts = db['contacts']
collection_utilisateurs = db['utilisateurs']

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
    
    def get_id(self):
        return str(self.user_data['_id'])

@login_manager.user_loader
def load_user(user_id):
    user_data = collection_utilisateurs.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if collection_utilisateurs.find_one({'username': username}):
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = {'username': username, 'password': hashed_password}
            collection_utilisateurs.insert_one(new_user)
            flash('Compte créé avec succès !', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('afficher_donnees'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = collection_utilisateurs.find_one({'username': username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user_obj = User(user_data)
            login_user(user_obj)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('afficher_donnees'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def afficher_donnees():
    donnees = list(collection_contacts.find())
    return render_template('index.html', donnees=donnees)

@app.route('/ajouter', methods=['GET', 'POST'])
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
