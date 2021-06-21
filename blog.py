from datetime import time
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask.globals import current_app
from flask.helpers import get_flashed_messages
from flask_mysqldb import MySQL
from werkzeug.datastructures import ContentRange
from wtforms import Form, StringField, TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.secret_key = "secretkey"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSOWORD"] = ""
app.config["MYSQL_DB"] = "sme"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

#Kullanıcı Giriş Kontrol Decaratorü
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu Sayfayı Görüntülemek İçin Lütfen Giriş Yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.length(min=5, max=20), validators.DataRequired(message="Lütfen kullanıcı adı giriniz.")])
    email= StringField("E-Mail",validators=[validators.Email(message="Lütfen Geçerli Bir Mail Giriniz.")])
    password = PasswordField("Parola", validators=[validators.length(min=5, max=20), validators.DataRequired(message="Lütfen parola giriniz."), validators.EqualTo(fieldname="confirm", message="Parolalar Uyuşmuyor")])
    confirm = PasswordField("Parola Doğrula")
#Login Formu
class LoginForm(Form):
    username=StringField("Kullanıcı Adı:")
    password=PasswordField("Parola:")

#Makale Oluşturma Formu
class ArticleForm(Form):
    title=StringField("Makale Başlığı", validators=[validators.length(min=5,max=100)])
    content=TextAreaField("Makale İçeriği", validators=[validators.length(min=10)])


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s"
    result=cursor.execute(sorgu,(session["username"],))
    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

    return render_template("dashboard.html")


#Login İşlemi
@app.route("/login", methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method =="POST":
        username = form.username.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()
        sorgu="select * from users where username = %s"
        result=cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password= data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Giriş Yaptınız","success")
                session["logged_in"]=True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Hatalı Parola Girdiniz..","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle Bir Kullanıcı Bulunamadı...", "danger")
            return redirect (url_for("login"))
    else:
        return render_template("login.html", form=form)

#Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Makale Ekleme
@app.route("/addarticle", methods=["GET","POST"])
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title = form.title.data
        content=form.content.data
        cursor=mysql.connection.cursor()
        sorgu="insert into articles(title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Hayrat Başarıyla Eklendi.","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form=form)

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor= mysql.connection.cursor()
    sorgu="select * from articles"
    result=cursor.execute(sorgu)

    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html" , articles=articles)
    else:
        return render_template("articles.html")
    
#Kayıt İşlemi
@app.route("/register", methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method =="POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email= form.email.data
        password=sha256_crypt.encrypt(form.password.data)
        cursor= mysql.connection.cursor()
        sorgu="insert into users (name,email,username,password) VALUES (%s,%s,%s,%s)"
        cursor.execute(sorgu, (name,email,username,password))
        mysql.connection.commit()
        cursor.close
        flash("Başarıyla Kayıt Oldunuz...", "success" )
        return redirect(url_for("login"))

    else:
        return render_template("register.html", form=form)

#Detay Safyası
@app.route("/article/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    sorgu="select * from articles where id= %s"
    result= cursor.execute(sorgu,(id,))

    if result>0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")
        
#Makale Silme İşlemi
@app.route("/delete/<string:id>", methods=["GET","POST"])
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s and id=%s"
    result= cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2="delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silme yetkiniz bulunmamaktadır.","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>", methods=["GET","POST"])
@login_required
def update(id):
    if request.method =="GET":
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where id=%s and author=%s"
        result=cursor.execute(sorgu,(id, session["username"]))
        if result==0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yoktur.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form=ArticleForm()
            form.title.data= article["title"]
            form.content.data=article["content"]
            cursor.close()
            return render_template("update.html", form=form)


    else:
        form=ArticleForm(request.form)
        newtitle=form.title.data
        newcontent=form.content.data
        cursor=mysql.connection.cursor()
        sorgu2="update articles set title=%s, content=%s where id=%s"
        cursor.execute(sorgu2,(newtitle,newcontent,id))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Güncellendi","success")
        return redirect(url_for("dashboard"))

#Makale Arama
@app.route("/search", methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor= mysql.connection.cursor()
        sorgu="select * from articles where title like '%"+ keyword + "%'"
        result = cursor.execute(sorgu)

        if result==0:
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall() 
            return render_template("articles.html",articles=articles)   




if __name__=="__main__":
    app.run(debug=True)
