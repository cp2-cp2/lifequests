from datetime import date
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quests.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    quest_type = db.Column(db.String(20), nullable=False) # 'main', 'sub', or 'chore'
    due_date = db.Column(db.String(10))
    is_done = db.Column(db.Boolean, default=False)
    last_done = db.Column(db.String(10))
    parent_id = db.Column(db.Integer, db.ForeignKey('quest.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    today = date.today().isoformat()
    # Auto-reset completed chores if a day has passed
    chores = Quest.query.filter_by(user_id=current_user.id, quest_type='chore').all()
    for chore in chores:
        if chore.last_done and chore.last_done < today:
            chore.is_done = False
    db.session.commit()

    quests = Quest.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', quests=quests)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user = User(
            username=request.form['username'], 
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('auth.html', action='Sign Up')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('auth.html', action='Log In')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    new_quest = Quest(
        title=request.form['title'],
        quest_type=request.form['quest_type'],
        due_date=request.form.get('due_date'),
        parent_id=request.form.get('parent_id') or None,
        user_id=current_user.id
    )
    db.session.add(new_quest)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle/<int:id>')
@login_required
def toggle(id):
    quest = Quest.query.get_or_404(id)
    if quest.user_id == current_user.id:
        quest.is_done = not quest.is_done
        if quest.quest_type == 'chore' and quest.is_done:
            quest.last_done = date.today().isoformat()
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)