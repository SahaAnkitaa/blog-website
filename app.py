import math
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import json

with open("config.json", "r") as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload-location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)

mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone_no = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=False, nullable=False)
    slug = db.Column(db.String(25), nullable=False)
    content = db.Column(db.String(12), nullable=False)
    tagline = db.Column(db.String(12), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():
    # Get all posts from database
    posts = Posts.query.filter_by().all()

    # Calculate total number of pages
    total_posts = len(posts)
    no_of_posts_per_page = int(params['no_of_posts'])
    last = math.ceil(total_posts / no_of_posts_per_page)

    # Get the current page number
    page = request.args.get('page')
    if not (page and page.isnumeric()):
        page = 1
    page = int(page)

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * no_of_posts_per_page
    end_idx = start_idx + no_of_posts_per_page

    # Get the posts for the current page
    posts = posts[start_idx:end_idx]

    # Determine the previous and next page URLs
    if page == 1:
        prev = "#"
        next = f"/?page={page + 1}"
    elif page == last:
        prev = f"/?page={page - 1}"
        next = "#"
    else:
        prev = f"/?page={page - 1}"
        next = f"/?page={page + 1}"

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/login", methods=['GET', 'POST'])
def dashboard():
    if "user" in session and session['user'] == params['admin-user']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get("user")
        userpass = request.form.get("password")
        if username == params['admin-user'] and userpass == params['admin-password']:
            # set the session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)

    return render_template('login.html', params=params)


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user'] == params['admin-user']:
        if request.method == "POST":
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno == '0':
                post = Posts(title=box_title, slug=slug, content=content, tagline=tline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
                #return redirect('/edit/' + str(post.sno))
                return redirect('/login')
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.tagline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/' + sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)
    else:
        return redirect('/login')


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user'] == params['admin-user']:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded Successfully"


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user'] == params['admin-user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/login")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        '''add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_no=phone, msg=message, date=datetime.now(), email=email)
        db.session.add(entry)
        db.session.commit()
        mail.send_message("New message from " + name, sender=email, recipients=[params['gmail-user']],
                          body=message + "\n" + phone)
    return render_template('contact.html', params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


app.run(debug=True)
