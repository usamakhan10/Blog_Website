from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship,Mapped,mapped_column

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#----------------------------flask_login--------------------------------------#

#this decorator returns the specific user entry of which user id is given to it
login_manager = LoginManager(app=app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).where(User.id==user_id)).scalar()
#----------------------------flask_login--------------------------------------#


##CONFIGURE TABLES
#I am defining one to many relationship here where user table is parent
class User(UserMixin,db.Model):
    __tablename__ = "User"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    email: Mapped[str] = mapped_column(db.String, unique=True,nullable=False)
    password: Mapped[str] = mapped_column(db.String,nullable=False)
     # Set up the one-to-many relationship with bye
    hi: Mapped[List["BlogPost"]] = relationship(back_populates="bye")
    with_user_comments:Mapped[List["comments"]] = relationship(back_populates="with_user")


# with app.app_context():
#     db.create_all()

#I am defining one to many relationship here where blog_post table is child
class BlogPost(db.Model):
    __tablename__ = "blog_post"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    author: Mapped[str] = mapped_column(db.String(250), nullable=False)
    title: Mapped[str] = mapped_column(db.String(250), unique=True,nullable=False)
    subtitle: Mapped[str] = mapped_column(db.String(250),nullable=False)
    date: Mapped[str] = mapped_column(db.String(250),nullable=False)
    body: Mapped[str] = mapped_column(db.Text,nullable=False)
    img_url: Mapped[str] = mapped_column(db.String(250),nullable=False)
    author_id: Mapped[int] = mapped_column(db.Integer,ForeignKey("User.id"))
    # Set up the many-to-one relationship with hi
    bye: Mapped["User"] = relationship(back_populates="hi")

    # Set up the one-to-many relationship with hi
    with_comments:Mapped[List["comments"]]=relationship(back_populates="with_blog_posts")

# with app.app_context():
#     db.create_all()
    
class comments(db.Model):
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    content: Mapped[str] = mapped_column(db.Text,nullable=False)

    post_id: Mapped[int] = mapped_column(db.Integer, ForeignKey("blog_post.id"))
    with_blog_posts:Mapped["BlogPost"] = relationship(back_populates="with_comments")

    user_id: Mapped[int] = mapped_column(db.Integer,ForeignKey("User.id"))
    with_user: Mapped["User"] = relationship(back_populates="with_user_comments")
    



@app.route('/')
def get_all_posts():
    posts = db.session.execute(db.select(BlogPost)).scalars()
    year=date.today().strftime("%Y")
    return render_template("index.html", all_posts=posts,year=year)


@app.route('/register',methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.execute(db.select(User).where(User.email==form.email.data)).scalar():
            flash(message="You already had an account please login",category="warning")
            return redirect(url_for("login"))
        with app.app_context():
            hash=generate_password_hash(password=form.password.data, method="pbkdf2:sha256:600000",salt_length=11)
            new_user = User(name=form.name.data,email=form.email.data,password=hash)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html",form=form)


@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with app.app_context():
            #retrieving the user id eith that specific email
            user = db.session.execute(db.select(User).where(User.email==form.email.data)).scalar()
            if not user:
                flash(message="You don't have any account with this email id. Please register your account",category="error")
                return redirect(url_for("register"))
            #checking the password against the hash
            if check_password_hash(pwhash=user.password, password=form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash(message="You entered wrong password",category="error")
                return redirect(url_for("login"))
    return render_template("login.html",form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))



@app.route("/post/<int:post_id>")
def show_post(post_id):
    requested_post = db.session.execute(db.select(BlogPost).where(BlogPost.id==post_id)).scalar()
    post_comments = db.session.execute(db.select(comments).where(comments.post_id==post_id)).scalars().all()
    comment_users_name = [db.session.execute(db.select(User.name).where(User.id==comment_obj.user_id)).scalar() for comment_obj in post_comments]
    comment_user_zip = list(zip(post_comments,comment_users_name))
    
    return render_template("post.html", post=requested_post,comment_user_zip=comment_user_zip)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["GET","POST"])
@login_required
def add_new_post():
    if not current_user.get_id()=="1":
        return login_manager.unauthorized()
    else:
        form = CreatePostForm()
        if form.validate_on_submit():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=form.author.data,
                date=date.today().strftime("%B %d, %Y"),
                author_id=current_user.id

            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
        return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=["GET","POST"])
@login_required
def edit_post(post_id):
    if not current_user.get_id()=="1":
        return login_manager.unauthorized()
    else: 
        post = BlogPost.query.get(post_id)
        edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            author=post.author,
            body=post.body
        )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = edit_form.author.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

        return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    if not current_user.get_id()=="1":
        return login_manager.unauthorized()
    else:
        with app.app_context(): 
            with db.session.no_autoflush:
                comments_to_delete = db.session.execute(db.select(comments).where(comments.post_id==post_id)).scalars()
            print(comments_to_delete)
            for comm in comments_to_delete:
                print(comm)
                db.session.delete(comm)
            db.session.commit()
            post_to_delete = db.session.execute(db.select(BlogPost).where(BlogPost.id==post_id)).scalar()
            db.session.delete(post_to_delete)
            db.session.commit()
            print(post_id)
        return redirect(url_for('get_all_posts'))


@app.route("/comment/<int:post_id>",methods=["GET","POST"])
@login_required
def comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        with app.app_context():
            comment_obj = comments()
            comment_obj.content = form.content.data
            comment_obj.post_id = post_id
            comment_obj.user_id = current_user.id
            db.session.add(comment_obj)
            db.session.commit()
            return redirect(url_for('show_post',post_id=post_id))
    return render_template("comment.html",form=form)

if __name__ == "__main__":
    app.run(debug=True)
