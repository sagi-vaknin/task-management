from flask import Flask, url_for, session, request
from flask import render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from models import *
from flask_login import login_user, logout_user, current_user, login_required

app = Flask(__name__)
login_manager.init_app(app)
app.secret_key = '!secret'
app.config.from_object('config')

db.init_app(app)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)


@app.route('/')
def homepage():
    user = session.get('user')
    return render_template('index.html' )

@app.route('/login')
def login():
    google = oauth.create_client('google') 
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth')
def authorize():
    google = oauth.create_client('google') 
    token = google.authorize_access_token()
    resp = google.get('userinfo') 
    user_info = resp.json()
    user = oauth.google.userinfo()

    current_user = {'username':user["name"], 'email':user["email"], 'picture':user["picture"]}

    db_user = User.query.filter_by(username=current_user['username']).first()
    if db_user:
        current_user['id'] = db_user.id
        print("user exists!")
        print(f"db_user's username: {db_user.username}, email: {db_user.email}.")
        login_user(db_user)
    else:
        new_user = User(username=current_user['username'], email=current_user['email'])
        db.session.add(new_user)
        db.session.commit()
        current_user['id'] = new_user['id']
        login_user(new_user)
        
        print("added a new user!")
        print(f"db_user's username: {new_user.username}, email: {new_user.email}.")
    
    
    session['profile'] = user_info
    session.permanent = True  
    
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
@login_required
def logout():
    for key in list(session.keys()):
        session.pop(key)
    logout_user()
    return redirect('/')

@app.route('/user')
@login_required
def user_dashboard():
    return render_template("user.html", user = current_user)

@app.route('/user/new_task')
@login_required
def new_task_page():
    return render_template("newTaskPage.html", user = current_user)

@app.route('/user/add_task', methods = ["POST"])
@login_required
def add_task():
    if request.method == "POST":
        task_title = request.form.get('task_title')
        task_data = request.form.get('task_data')

        new_task = Task(title=task_title, description=task_data, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('user_dashboard'))
    
@app.route('/user/manage', methods = ["POST","GET"])    
@login_required
def manage_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template("manageTasks.html", user = current_user, tasks = tasks)

@app.route('/archive_task/<int:task_id>', methods=['POST'])
@login_required
def archive_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = 1
    db.session.commit()
    return redirect(url_for('manage_tasks'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('finished_tasks'))

@app.route('/user/finished_tasks', methods = ["POST","GET"])
def finished_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template("finishedTasks.html",user=current_user ,tasks=tasks)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)