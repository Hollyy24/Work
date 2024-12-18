import os

import requests
from werkzeug.security import generate_password_hash, check_password_hash

from flask import render_template, redirect, url_for, Flask, flash, request
from flask_bootstrap import Bootstrap4
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, RadioField, SelectField
from wtforms.validators import DataRequired, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Integer, func
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
Bootstrap4(app)

login_manager = LoginManager()
login_manager.init_app(app)

session = {}


class Base(DeclarativeBase):
    pass


app.config["SECRET_KEY"] = os.getenv('MYKEY')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///booklibrary.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(model_class=Base)
db.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Classuser, user_id)


def get_available_id():
    existing_ids = db.session.query(Books.id).all()
    existion_ids = {id[0] for id in existing_ids}
    next_id = 1
    while next_id in existion_ids:
        next_id += 1
    return next_id


# 書本資料
class Books(db.Model):
    __tablename__ = "書籍資料"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    ISBN_number: Mapped[str] = mapped_column(String)
    position: Mapped[str] = mapped_column(String)
    borrower: Mapped[str] = mapped_column(String)


# 班級教師資料
class Classuser(UserMixin, db.Model):
    __tablename__ = "班級表單"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_: Mapped[str] = mapped_column(String,unique=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)

    def __init__(self, class_,name, password):
        self.class_ = class_
        self.name = name
        self.password = password


# 學生名單資料
class Students(db.Model):
    __tablename__ = "學生名單"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_number: Mapped[str] = mapped_column(Integer, unique=True)
    class_id: Mapped[str] = mapped_column(String)


# 登入表單
class User_login(FlaskForm):
    name = StringField("班級帳號", validators=[DataRequired()])
    password = StringField("班級密碼", validators=[DataRequired()])
    submit = SubmitField("登入")


# 手動新增書本表單
class Addbook(FlaskForm):
    id = StringField('ＩＤ', render_kw={'readonly': True})
    ISBN = StringField('ISBN', validators=[DataRequired()])
    bookname = StringField('書名', validators=[DataRequired()])
    author = StringField("作者", validators=[DataRequired()])
    position = SelectField('位置', choices=[("圖書室", "圖書室")],
                           validators=[DataRequired()])
    borrower = StringField("借閱人", validators=[Optional()])
    submit = SubmitField("送出")


# 管理員表單
class Userform(FlaskForm):
    class_ = StringField("班級名稱",validators=[DataRequired()])
    name = StringField("班級帳號", validators=[DataRequired()])
    password = StringField("班級密碼", validators=[DataRequired()])
    submit = SubmitField("送出")


# 學生輸入表單
class Studentform(FlaskForm):
    class_id = StringField('所屬班級', validators=[DataRequired()])
    number = StringField("學生號碼", validators=[DataRequired()])
    submit = SubmitField("送出")


# ISBN新增表單
class Isbnadd(FlaskForm):
    ISBN_input = StringField("ISBN輸入", validators=[DataRequired()])
    submit = SubmitField("匯入")


# 搜尋書本表單
class Search(FlaskForm):
    ways = SelectField('查詢方式', choices=[("ISBN碼", "ISBN碼"), ("書名", "書名"), ("作者", "作者"), ("位置", "位置")],
                       validators=[DataRequired()])
    string = StringField('輸入關鍵字', validators=[DataRequired()])
    submit = SubmitField("送出")


# 書本位置借閱表單
class Bookposition(FlaskForm):
    book_number = StringField("書本編號", validators=[DataRequired()])
    submit = SubmitField("借閱")


# 借閱人表單
class Borrowerbook(FlaskForm):
    book_number = StringField("書本編號", validators=[DataRequired()])
    student_number = StringField('學生號碼', validators=[DataRequired()])
    submit = SubmitField("借閱")


with app.app_context():
    db.create_all()
    if not Classuser.query.filter_by().all():
        admin = Classuser(class_="辦公室",name='admin', password='admin')
        db.session.add(admin)
        db.session.commit()


# ---------網頁框架------------#

# 不需要登入
@app.route("/")
def home():
    return render_template("home_page.html", logged_in=current_user.is_authenticated)


# 不需要登入
@app.route("/search", methods=["GET", "POST"])
def research():
    search = Search()
    page = request.args.get('page', default=1, type=int)
    books = Books.query.paginate(page=page, per_page=10)

    if search.validate_on_submit():
        if search.ways.data == "ISBN碼":
            ISBN = search.string.data
            books = Books.query.filter_by(ISBN_number=ISBN).paginate(page=page, per_page=10)
        elif search.ways.data == "書名":
            bookname = search.string.data
            books = Books.query.filter_by(name=bookname).paginate(page=page, per_page=10)
        elif search.ways.data == "作者":
            author = search.string.data
            books = Books.query.filter_by(author=author).paginate(page=page, per_page=10)
        elif search.ways.data == "位置":
            position = search.string.data
            books = Books.query.filter_by(position=position).paginate(page=page, per_page=10)
    start_page = max(1, page - 2)
    end_page = min(books.pages, page + 2)

    return render_template("research_page.html", search=search, books=books,start_page=start_page, end_page=end_page, logged_in=current_user.is_authenticated)


# 需要登入
@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    global session
    available_id = get_available_id()
    isbn_add = Isbnadd()
    classusers = Classuser.query.all()
    if 'isbn_input' in session:
        if session['isbn_input']:
            if session['isbn_input']['ISBN'] is None:
                session['isbn_input']['ISBN'] = "---"
            if session['isbn_input']['書名'] is None:
                session['isbn_input']['書名'] = "---"
            if session['isbn_input']['作者'] is None:
                session['isbn_input']['作者'] = "---"
            addbook = Addbook(
                id=available_id,
                ISBN=session['isbn_input']['ISBN'][12:],
                title=session['isbn_input']['書名'],
                author=session['isbn_input']['作者'],
            )

        else:
            addbook = Addbook(id=available_id,
                              ISBN="沒有搜尋到",
                              title="沒有搜尋到",
                              author="沒有搜尋到",
                              position="沒有搜尋到")
    else:
        addbook = Addbook(id=available_id )
        addbook.position.choices = [(user.class_, user.class_) for user in classusers]
    if isbn_add.validate_on_submit():
        info = Bookinfo(isbn_add.ISBN_input.data)
        info.book_info()
        session['isbn_input'] = info.info_list
        return redirect(url_for("add"))
    if addbook.validate_on_submit():

        books = Books(
            id=available_id,
            ISBN_number=addbook.ISBN.data,
            author=addbook.author.data,
            title=addbook.bookname.data,
            position=addbook.position.data,
            borrower="---"
        )
        db.session.add(books)
        db.session.commit()
        session = {}
        flash("新增完成！")
        return redirect(url_for("add"))
    return render_template("add_page.html", isbn_add=isbn_add, addbook=addbook,
                           logged_in=current_user.is_authenticated)


# 需要登入
@app.route("/delet/<string:book_id>", methods=["GET", "POST"])
def delete(book_id):
    book = Books.query.filter_by(id=book_id).first()
    if book.borrower != "---":
        flash("書本借閱中！不可以刪除。")
    elif book:
        db.session.delete(book)
        db.session.commit()
        flash("刪除成功！")
    return redirect(url_for('research', logged_in=current_user.is_authenticated))


# 需要登入
@app.route("/class_borrow", methods=["GET", "POST"])
@login_required
def class_borrow():
    bookposition = Bookposition()
    current_position = current_user.name
    books = Books.query.filter_by(position=current_position).all()
    if bookposition.validate_on_submit():
        bookmove = Books.query.filter_by(id=bookposition.book_number.data).first()
        if bookmove:
            bookmove.position = current_position
            db.session.commit()
            return redirect(url_for("class_borrow"))
        else:
            flash("沒有搜尋到該本書籍")
    return render_template("class_borrow_page.html", bookposition=bookposition, books=books,
                           logged_in=current_user.is_authenticated)


# 需要登入
@app.route("/student_borrow", methods=["GET", "POST"])
@login_required
def student_borrow():
    borrowerbook = Borrowerbook()
    studentform = Studentform(class_id=current_user.class_)
    students = Students.query.filter_by(class_id=current_user.id).all()
    if borrowerbook.validate_on_submit():
        bookmove = Books.query.filter_by(id=borrowerbook.book_number.data).first()
        if bookmove:
            bookmove.borrower = f"{current_user.name}-{borrowerbook.student_number.data}"
            db.session.commit()
            return redirect(url_for("student_borrow"))
        else:
            flash("沒有搜尋到該本書籍")
    return render_template("student_borrow.html", studentform=studentform,
                           students=students, borrowerbook=borrowerbook,
                           logged_in=current_user.is_authenticated)


@app.route("/student", methods=["GET", "POST"])
@login_required
def student():
    studentform = Studentform(class_id=current_user.class_)
    students = Students.query.filter_by(class_id=current_user.id).all()
    books = Books.query.filter_by().all()
    if studentform.validate_on_submit():
        student = Students(
            class_id=current_user.id,
            student_number=f"{current_user.id}-{studentform.number.data}")
        try:
            db.session.add(student)
            db.session.commit()
            students = Students.query.filter_by(class_id=current_user.id).all()
            print(students)
            return render_template("student_manager.html", students=students,
                                   studentform=studentform,
                                   logged_in=current_user.is_authenticated)
        except IntegrityError:
            db.session.rollback()
            flash("學號已經存在!請重新輸入", "error")

    return render_template("student_manager.html", students=students, books=books,
                           studentform=studentform,
                           logged_in=current_user.is_authenticated)


@app.route("/returnoffice/<string:book_id>", methods=["GET", "POST"])
@login_required
def returnoffice(book_id):
    bookmove = Books.query.filter_by(id=book_id).first()
    if bookmove.borrower != "---":
        flash("尚有學生未歸還書籍，不可移動紀錄")
    elif bookmove:
        bookmove.position = "辦公室"
        db.session.commit()
        flash("退還成功！")
    else:
        flash("沒有搜尋到該本書籍")
    return redirect(url_for("class_borrow"))


@app.route("/returnbook/<string:book_id>", methods=["GET", "POST"])
def returnbook(book_id):
    books = Books.query.filter_by(id=book_id).first()
    books.borrower = "---"
    db.session.commit()
    flash("退還成功！")
    return redirect(url_for('student_borrow'))


@app.route("/delete_student/<string:student_number>", methods=["GET", "POST"])
def delete_student(student_number):
    student = Students.query.filter_by(student_number=student_number).first()
    book = Books.query.filter_by(borrower=student.student_number).first()
    if book:
        flash("有書籍尚未歸還，不可以刪除帳號。")
    elif student:
        db.session.delete(student)
        db.session.commit()
        flash("刪除成功！")
    return redirect(url_for('student', logged_in=current_user.is_authenticated))


@app.route("/usermanage", methods=['GET', 'POST'])
@login_required
def usermanage():
    if current_user.name != 'admin':
        flash("您沒有權限訪問管理員資料設定")
        return redirect(url_for('home'))
    userform = Userform()
    classusers = Classuser.query.filter_by().all()
    if userform.validate_on_submit():
        try:
            classuser = Classuser(class_=userform.class_.data,name=userform.name.data, password=userform.password.data)
            db.session.add(classuser)
            db.session.commit()
            flash("新增成功")
            return redirect(url_for('usermanage'))
        except IntegrityError:
            db.session.rollback()
            flash("帳號重複")
    return render_template("user_page.html", userform=userform, classusers=classusers,
                           logged_in=current_user.is_authenticated)



@app.route("/login", methods=['GET', 'POST'])
def login():
    userlogin = User_login()
    if userlogin.validate_on_submit():

        user = Classuser.query.filter_by(name=userlogin.name.data, password=userlogin.password.data).first()
        if user:
            login_user(user)
            return redirect(url_for('home', logged_in=current_user.is_authenticated))
        else:
            userlogin = User_login(name="無此帳號", password="無此帳號")
            return render_template("login_page.html", userlogin=userlogin, logged_in=current_user.is_authenticated)

    return render_template("login_page.html", userlogin=userlogin, logged_in=current_user.is_authenticated)





@app.route("/logout")
@login_required
def log_out():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
