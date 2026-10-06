import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, g)

from models import (db, User, Category, Article, News, Appeal,
                    AppealMessage, Feedback, ROLES, STATUSES)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'zhilkom-practice-2026')
# по умолчанию sqlite, для XAMPP (MySQL) задать DATABASE_URL,
# например mysql+pymysql://root:@localhost/zhilkom
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'zhilkom.db'))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
          'августа', 'сентября', 'октября', 'ноября', 'декабря']

db.init_app(app)

with app.app_context():
    db.create_all()
    if User.query.first() is None:
        from seed import fill_db
        fill_db()


# ---------- вспомогательные функции ----------

def get_user():
    if 'user' not in g:
        g.user = None
        if session.get('user_id'):
            g.user = db.session.get(User, session['user_id'])
    return g.user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if get_user() is None:
            flash('Чтобы открыть эту страницу, войдите на сайт', 'error')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def staff_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_user()
        if user is None:
            return redirect(url_for('login', next=request.path))
        if not user.is_staff:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_user()
        if user is None:
            return redirect(url_for('login', next=request.path))
        if not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def check_user_form(form, new_user=True):
    errors = []
    if not form.get('fio', '').strip():
        errors.append('Укажите ФИО')
    if new_user:
        login = form.get('login', '').strip()
        if len(login) < 3:
            errors.append('Логин должен быть не короче 3 символов')
        elif User.query.filter_by(login=login).first():
            errors.append('Такой логин уже занят')
    password = form.get('password', '')
    if new_user or password:
        if len(password) < 6:
            errors.append('Пароль должен быть не короче 6 символов')
        elif password != form.get('password2', ''):
            errors.append('Пароли не совпадают')
    return errors


def save_image(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_IMAGES:
        flash('Картинка должна быть в формате png, jpg, gif или webp', 'error')
        return None
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    name = uuid.uuid4().hex[:12] + '.' + ext
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
    return 'uploads/' + name


def art_images():
    folder = os.path.join(BASE_DIR, 'static', 'img', 'art')
    return sorted('img/art/' + f for f in os.listdir(folder))


@app.context_processor
def inject_globals():
    return {
        'current_user': get_user(),
        'menu_categories': Category.query.order_by(Category.id).all(),
        'vision': session.get('vision', False),
        'v': session.get('v', VISION_DEFAULT),
        'roles': ROLES,
        'statuses': STATUSES,
        'year': datetime.now().year,
    }


@app.template_filter('date')
def date_filter(value):
    return value.strftime('%d.%m.%Y') if value else ''


@app.template_filter('date_ru')
def date_ru_filter(value):
    if not value:
        return ''
    return f'{value.day} {MONTHS[value.month - 1]} {value.year}'


# ---------- версия для слабовидящих ----------

VISION_DEFAULT = {'size': '1', 'scheme': 'white', 'img': 'on', 'space': '1'}


@app.route('/vision/on')
def vision_on():
    session['vision'] = True
    session.setdefault('v', dict(VISION_DEFAULT))
    return redirect(request.referrer or url_for('index'))


@app.route('/vision/off')
def vision_off():
    session['vision'] = False
    return redirect(request.referrer or url_for('index'))


@app.route('/vision/set')
def vision_set():
    v = dict(session.get('v', VISION_DEFAULT))
    options = {
        'size': ('1', '2', '3'),
        'scheme': ('white', 'black', 'blue'),
        'img': ('on', 'off'),
        'space': ('1', '2', '3'),
    }
    for key, allowed in options.items():
        value = request.args.get(key)
        if value in allowed:
            v[key] = value
    session['v'] = v
    session['vision'] = True
    return redirect(request.referrer or url_for('index'))


# ---------- открытые страницы ----------

@app.route('/')
def index():
    news = News.query.order_by(News.created_at.desc()).limit(4).all()
    articles = Article.query.order_by(Article.created_at.desc()).limit(3).all()
    return render_template('index.html', news=news, articles=articles)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/news')
def news_list():
    page = request.args.get('page', 1, type=int)
    pagination = News.query.order_by(News.created_at.desc()).paginate(
        page=page, per_page=5, error_out=False)
    return render_template('news.html', pagination=pagination)


@app.route('/news/<int:news_id>')
def news_item(news_id):
    item = db.get_or_404(News, news_id)
    other = News.query.filter(News.id != item.id).order_by(
        News.created_at.desc()).limit(3).all()
    return render_template('news_item.html', item=item, other=other)


@app.route('/materials')
def materials():
    categories = Category.query.order_by(Category.id).all()
    return render_template('materials.html', categories=categories)


@app.route('/materials/<slug>')
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    articles = Article.query.filter_by(category_id=cat.id).order_by(
        Article.created_at.desc()).all()
    return render_template('category.html', cat=cat, articles=articles)


@app.route('/article/<int:article_id>')
def article(article_id):
    item = db.get_or_404(Article, article_id)
    item.views = (item.views or 0) + 1
    db.session.commit()
    other = Article.query.filter(Article.category_id == item.category_id,
                                 Article.id != item.id).order_by(
        Article.created_at.desc()).limit(3).all()
    return render_template('article.html', item=item, other=other)


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        text = request.form.get('text', '').strip()
        if not name or not text:
            flash('Заполните имя и текст сообщения', 'error')
            return render_template('contacts.html', form=request.form)
        db.session.add(Feedback(name=name, email=email, text=text))
        db.session.commit()
        flash('Сообщение отправлено. Ответ придёт на указанную почту', 'ok')
        return redirect(url_for('contacts'))
    return render_template('contacts.html', form={})


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    found_news, found_articles = [], []
    if len(q) >= 3:
        # ищем без учёта регистра, sqlite по-русски сам так не умеет
        word = q.lower()
        for n in News.query.order_by(News.created_at.desc()).all():
            if word in n.title.lower() or word in n.body.lower():
                found_news.append(n)
        for a in Article.query.order_by(Article.created_at.desc()).all():
            if word in a.title.lower() or word in a.body.lower():
                found_articles.append(a)
    elif q:
        flash('Введите для поиска не меньше 3 символов', 'error')
    return render_template('search.html', q=q, found_news=found_news,
                           found_articles=found_articles)


@app.route('/sitemap')
def sitemap():
    categories = Category.query.order_by(Category.id).all()
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('sitemap.html', categories=categories, news=news)


# ---------- вход и регистрация ----------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(login=request.form.get('login', '').strip()).first()
        if user is None or not user.check_password(request.form.get('password', '')):
            flash('Неверный логин или пароль', 'error')
        elif not user.active:
            flash('Учётная запись заблокирована, обратитесь в комитет', 'error')
        else:
            session['user_id'] = user.id
            flash('Добро пожаловать, ' + user.fio, 'ok')
            next_page = request.args.get('next', '')
            if next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('panel') if user.is_staff else url_for('cabinet'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if get_user():
        return redirect(url_for('cabinet'))
    if request.method == 'POST':
        errors = check_user_form(request.form)
        if not request.form.get('agree'):
            errors.append('Нужно согласие на обработку персональных данных')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html', form=request.form)
        user = User(login=request.form['login'].strip(),
                    fio=request.form['fio'].strip(),
                    email=request.form.get('email', '').strip(),
                    phone=request.form.get('phone', '').strip(),
                    address=request.form.get('address', '').strip(),
                    role='resident')
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash('Регистрация прошла успешно', 'ok')
        return redirect(url_for('cabinet'))
    return render_template('register.html', form={})


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из личного кабинета', 'ok')
    return redirect(url_for('index'))


# ---------- личный кабинет и обращения ----------

@app.route('/cabinet', methods=['GET', 'POST'])
@login_required
def cabinet():
    user = get_user()
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        text = request.form.get('text', '').strip()
        if not topic or not text:
            flash('Укажите тему и текст обращения', 'error')
        else:
            appeal = Appeal(user_id=user.id, topic=topic)
            db.session.add(appeal)
            db.session.flush()
            db.session.add(AppealMessage(appeal_id=appeal.id, user_id=user.id, text=text))
            db.session.commit()
            flash(f'Обращение №{appeal.id} отправлено', 'ok')
            return redirect(url_for('appeal', appeal_id=appeal.id))
    appeals = Appeal.query.filter_by(user_id=user.id).order_by(Appeal.created_at.desc()).all()
    return render_template('cabinet.html', appeals=appeals)


@app.route('/cabinet/profile', methods=['POST'])
@login_required
def profile():
    user = get_user()
    errors = check_user_form(request.form, new_user=False)
    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('cabinet'))
    user.fio = request.form['fio'].strip()
    user.email = request.form.get('email', '').strip()
    user.phone = request.form.get('phone', '').strip()
    user.address = request.form.get('address', '').strip()
    if request.form.get('password'):
        user.set_password(request.form['password'])
    db.session.commit()
    flash('Данные профиля сохранены', 'ok')
    return redirect(url_for('cabinet'))


@app.route('/appeal/<int:appeal_id>', methods=['GET', 'POST'])
@login_required
def appeal(appeal_id):
    user = get_user()
    item = db.get_or_404(Appeal, appeal_id)
    if item.user_id != user.id and not user.is_staff:
        abort(403)

    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        if item.status == 'closed' and not user.is_staff:
            flash('Обращение закрыто, создайте новое', 'error')
            return redirect(url_for('appeal', appeal_id=item.id))
        if text:
            db.session.add(AppealMessage(appeal_id=item.id, user_id=user.id, text=text))
            if user.is_staff and item.status == 'new':
                item.status = 'work'
        if user.is_staff and request.form.get('status') in STATUSES:
            item.status = request.form['status']
        db.session.commit()
        flash('Сохранено', 'ok')
        return redirect(url_for('appeal', appeal_id=item.id))

    return render_template('appeal.html', item=item)


# ---------- панель сотрудника ----------

@app.route('/panel')
@staff_required
def panel():
    status = request.args.get('status')
    query = Appeal.query
    if status in STATUSES:
        query = query.filter_by(status=status)
    appeals = query.order_by(Appeal.created_at.desc()).all()
    feedback = Feedback.query.order_by(Feedback.created_at.desc()).all()
    stats = {
        'new': Appeal.query.filter_by(status='new').count(),
        'all': Appeal.query.count(),
        'users': User.query.count(),
        'unread': Feedback.query.filter_by(is_read=False).count(),
    }
    return render_template('panel/index.html', appeals=appeals, feedback=feedback,
                           stats=stats, status=status)


@app.route('/panel/feedback/<int:fid>/read', methods=['POST'])
@staff_required
def feedback_read(fid):
    item = db.get_or_404(Feedback, fid)
    item.is_read = True
    db.session.commit()
    return redirect(url_for('panel'))


@app.route('/panel/users')
@staff_required
def panel_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('panel/users.html', users=users)


@app.route('/panel/users/new', methods=['GET', 'POST'])
@staff_required
def user_new():
    me = get_user()
    # сотрудник может заводить только жителей, админ - кого угодно
    allowed = list(ROLES) if me.is_admin else ['resident']
    if request.method == 'POST':
        errors = check_user_form(request.form)
        role = request.form.get('role', 'resident')
        if role not in allowed:
            errors.append('Нет прав на создание пользователя с такой ролью')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('panel/user_form.html', form=request.form,
                                   allowed=allowed, edit=None)
        user = User(login=request.form['login'].strip(),
                    fio=request.form['fio'].strip(),
                    email=request.form.get('email', '').strip(),
                    phone=request.form.get('phone', '').strip(),
                    address=request.form.get('address', '').strip(),
                    role=role)
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash(f'Пользователь {user.login} создан', 'ok')
        return redirect(url_for('panel_users'))
    return render_template('panel/user_form.html', form={}, allowed=allowed, edit=None)


@app.route('/panel/users/<int:uid>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(uid):
    me = get_user()
    user = db.get_or_404(User, uid)
    if request.method == 'POST':
        errors = check_user_form(request.form, new_user=False)
        if errors:
            for e in errors:
                flash(e, 'error')
            return redirect(url_for('user_edit', uid=uid))
        user.fio = request.form['fio'].strip()
        user.email = request.form.get('email', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.address = request.form.get('address', '').strip()
        if user.id != me.id:
            if request.form.get('role') in ROLES:
                user.role = request.form['role']
            user.active = bool(request.form.get('active'))
        if request.form.get('password'):
            user.set_password(request.form['password'])
        db.session.commit()
        flash('Изменения сохранены', 'ok')
        return redirect(url_for('panel_users'))
    form = {'login': user.login, 'fio': user.fio, 'email': user.email,
            'phone': user.phone, 'address': user.address, 'role': user.role,
            'active': user.active}
    return render_template('panel/user_form.html', form=form,
                           allowed=list(ROLES), edit=user)


def get_model(kind):
    if kind == 'news':
        return News
    if kind == 'article':
        return Article
    abort(404)


@app.route('/panel/content')
@staff_required
def panel_content():
    news = News.query.order_by(News.created_at.desc()).all()
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('panel/content.html', news=news, articles=articles)


@app.route('/panel/<kind>/new', methods=['GET', 'POST'])
@app.route('/panel/<kind>/<int:item_id>/edit', methods=['GET', 'POST'])
@staff_required
def content_form(kind, item_id=None):
    Model = get_model(kind)
    item = db.get_or_404(Model, item_id) if item_id else None
    categories = Category.query.order_by(Category.id).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        if not title or not body:
            flash('Заголовок и текст обязательны', 'error')
            return render_template('panel/content_form.html', kind=kind, item=item,
                                   form=request.form, categories=categories,
                                   images=art_images())
        if item is None:
            item = Model()
            db.session.add(item)
        item.title = title
        item.summary = request.form.get('summary', '').strip()
        item.body = body.replace('\r\n', '\n')
        if kind == 'article':
            item.category_id = request.form.get('category_id', type=int)
        try:
            item.created_at = datetime.strptime(request.form.get('date', ''), '%Y-%m-%d')
        except ValueError:
            item.created_at = item.created_at or datetime.now()
        uploaded = save_image(request.files.get('image_file'))
        item.image = uploaded or request.form.get('image') or None
        db.session.commit()
        flash('Материал сохранён', 'ok')
        return redirect(url_for('panel_content'))

    form = {}
    if item:
        form = {'title': item.title, 'summary': item.summary, 'body': item.body,
                'image': item.image, 'date': item.created_at.strftime('%Y-%m-%d'),
                'category_id': getattr(item, 'category_id', None)}
    return render_template('panel/content_form.html', kind=kind, item=item, form=form,
                           categories=categories, images=art_images())


@app.route('/panel/<kind>/<int:item_id>/delete', methods=['POST'])
@staff_required
def content_delete(kind, item_id):
    Model = get_model(kind)
    item = db.get_or_404(Model, item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Материал удалён', 'ok')
    return redirect(url_for('panel_content'))


# ---------- ошибки ----------

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('not_found', page=request.path))


@app.route('/404')
def not_found():
    return render_template('404.html', page=request.args.get('page', '')), 404


@app.errorhandler(403)
def forbidden(e):
    flash('У вас нет доступа к этому разделу', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
