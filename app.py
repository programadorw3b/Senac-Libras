#Bibliotecas necessárias para executar o código
import os
import sqlite3
import random
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_mail import Mail, Message
from pathlib import Path
if hasattr(sys, '_MEIPASS'):
    dotenv_path = Path(sys._MEIPASS) / '.env'
else:
    dotenv_path = '.env'
load_dotenv(dotenv_path)

#App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
DATABASE = 'admins.db'
#Enviar email de recuperação de senha
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_REC_ENVIO")        
app.config['MAIL_PASSWORD'] = os.getenv("SENHA_REC_ENVIO")  
mail = Mail(app)


#Abrir e fechar o banco de dados
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

#Gerar código aleatório:
def token_recuperacao():
    return str(random.randint(100000, 999999))

#Banco de dados
def inicializar_banco():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                tier INTEGER DEFAULT 0
            );
        ''')
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS palavras(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                url TEXT NOT NULL,
                capa TEXT
            );
        ''')
        db.commit()

#---------------------------#
#Rota index
@app.route('/')
def index():
    db = get_db()
    palavras = db.execute('SELECT * FROM palavras WHERE capa IS NOT NULL ORDER BY id DESC LIMIT 15').fetchall()
    return render_template('index.html', palavras=palavras)

#---------------------------#

#Funções do Usuário

#Rota cadastro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if session.get('admin_tier') != 1:
        return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tier = request.form['tier']
        senha_segura = generate_password_hash(senha)
        db = get_db()
        try:
            db.execute('INSERT INTO admins (nome, email, senha, tier) VALUES (?, ?, ?, ?)', (nome, email, senha_segura, tier))
            db.commit()
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Erro ao cadastrar email!')
            return render_template('register.html')
    
    return render_template('register.html')

#Rota login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        db = get_db()
        admin = db.execute('SELECT * FROM admins WHERE email=?', (email, )).fetchone()
        if admin and check_password_hash(admin['senha'], senha):
            session['admin_id'] = admin['id']
            session['admin_nome'] = admin['nome']
            session['admin_tier'] = admin['tier']
            return redirect(url_for('index'))
        else:
            flash('Erro ao logar.')
            return render_template('login.html')
    return render_template('login.html')

#Rota editar_user
@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    usuario = db.execute('SELECT * FROM admins WHERE id=?', (session['admin_id'], )).fetchone()
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        try:
            db.execute('UPDATE admins SET nome=?, email=? WHERE id=?', (nome, email, session['admin_id']))
            db.commit()
            return redirect(url_for('edit_user'))
        except sqlite3.IntegrityError:
            flash('Usuário editado.')
            return render_template('edit_user.html')
    return render_template('edit_user.html', usuario=usuario)


#Rota excluir a conta
@app.route('/excluir_conta')
def excluir_conta():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM admins WHERE id=?', (session['admin_id'],))
    db.commit()
    session.clear()
    return redirect(url_for('index'))

#Rota listar usuários e ver tokens
@app.route('/listar_admins')
def listar_admins():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if session.get('admin_tier') != 1:
        return redirect(url_for('index'))
    db = get_db()
    admins = db.execute('SELECT * FROM admins').fetchall()
    return render_template('listar_admins.html', admins=admins)

#Rota deletar admin
@app.route('/deletar_admin/<int:id>')
def deletar_admin(id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if session.get('admin_tier') != 1:
        return redirect(url_for('index'))
    db = get_db()
    db.execute('DELETE FROM admins WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('listar_admins'))
#Fim das funções do usuário

#---------------------------#

#Funções palavra

#Rota cadastrar palavra
@app.route('/cadastrar_palavras', methods=['GET', 'POST'])
def cadastrar_palavra():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        titulo = request.form['titulo'].upper()
        descricao = request.form['descricao']
        url = request.form['url']
        card = request.form.get('card')
        db = get_db()
        if "https://www.youtube.com/embed/" and "?" in url:
            if card == 'sim':
                capa = url.split("/embed/")[1].split("?")[0]
            else:
                capa = None
        else:
            flash('Cadastre um link incorporado do vídeo do Youtube para funcionar.')
            return redirect('cadastrar_palavras')
        try:
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', (titulo, descricao, url, capa))
            db.commit()
            flash('Palavra cadastrada!!!')
            return redirect(url_for('cadastrar_palavra'))
        except sqlite3.IntegrityError:
            flash('Erro ao cadastrar palavra!')
            return render_template('cadastrar_palavra.html')
    return render_template('cadastrar_palavra.html')

#Rota editar_palavra
@app.route('/edit_palavra/<int:id>', methods=['GET', 'POST'])
def edit_palavra(id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    palavra = db.execute('SELECT * FROM palavras WHERE id=?', (id, )).fetchone()
    if request.method == 'POST':
        titulo = request.form['titulo'].upper()
        descricao = request.form['descricao']
        url = request.form['url']
        card = request.form.get('card')
        db = get_db()
        if "https://www.youtube.com/embed/" and "?" in url:
            if card == 'sim':
                capa = url.split("/embed/")[1].split("?")[0]
            else:
                capa = None
        else:
            flash('Cadastre um link incorporado do vídeo do Youtube para funcionar.')
            return redirect('edit_palavra')
        try:
            db.execute('UPDATE palavras SET titulo=?, descricao=?, url=?, capa=? WHERE id=?', (titulo, descricao, url, capa, id))
            db.commit()
            return redirect(url_for('glossario'))
        except sqlite3.IntegrityError:
            flash('Usuário editado.')
            return render_template('edit_palavra.html')
    return render_template('edit_palavra.html', palavra=palavra)

#Rota ver palavra
@app.route('/exibir_palavra/<int:id>')
def exibir_palavra(id):
    db = get_db()
    palavra = db.execute('SELECT * FROM palavras WHERE id = ?', (id,)).fetchone()
    return render_template('exibir_palavra.html', palavra=palavra)

#Rota deletar palavra
@app.route('/deletar_palavra/<int:id>')
def deletar_palavra(id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM palavras WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('glossario'))


#Rota glossario
@app.route('/glossario')
@app.route('/glossario/<letra>')
def glossario(letra=None):
    db = get_db()
    if letra:
        palavras = db.execute('SELECT * FROM palavras WHERE titulo LIKE ? ORDER BY titulo ASC', (letra + '%',)).fetchall()
    else:
        palavras = db.execute('SELECT * FROM palavras ORDER BY titulo ASC').fetchall()
    return render_template('glossario.html', palavras=palavras)

#Rota pesquisa
@app.route('/pesquisar', methods=['GET', 'POST'])
def pesquisar():
    pesquisa = request.form['pesquisa'].upper()
    db = get_db()
    palavras = db.execute('SELECT * FROM palavras WHERE titulo LIKE ? ORDER BY titulo ASC', ('%' + pesquisa + '%',)).fetchall()
    return render_template('glossario.html', palavras=palavras)


#Fim das funções palavra

#---------------------------#

#Função recuperar a senha

#Rota gerar token
@app.route('/recuperar_senha', methods=['GET', 'POST'])
def rec_senha():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        usuario = db.execute("SELECT * FROM admins WHERE email=?", (email,)).fetchone()
        if usuario:
            token = token_recuperacao()
            session['token'] = token
            email_rec = Message(
                    subject='Senac - Libras',
                    sender= os.getenv("EMAIL_REC_ENVIO"),
                    recipients=[email],
                    body=f'Seu código para recuperação de senha é: {token}'
                )
            print(token)
            mail.send(email_rec)
            flash("Código enviado! Verifique seu e-mail (ou veja no terminal).", "info")
            return redirect(url_for('rec_senha_codigo', email=email, token=token))
        else:
            flash("E-mail não encontrado.")
            return render_template('rec_senha.html')
    return render_template('rec_senha.html')

#Rota mudar senha
@app.route('/rec_senha_codigo/<email>', methods=['GET', 'POST'])
def rec_senha_codigo(email):
    if request.method == 'POST':
        token_rec = request.form['codigo']
        senha = request.form['senha']
        senha_segura = generate_password_hash(senha)
        db = get_db()
        if token_rec == session.get('token'):
            db.execute('UPDATE admins SET senha=? WHERE email=?', (senha_segura, email))
            db.commit()
            session.clear()
            return redirect(url_for('login'))
        else:
            flash("Código inválido", "danger")
            return render_template('rec_senha_codigo.html', email=email)
    return render_template('rec_senha_codigo.html', email=email)

#Fim das funções recuperação de senha

#---------------------------#

#Rota logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

'''
.env:
SECRET_KEY=589086421acc03edf62ecb6c7750347ee66a76501d1c7510caa5392503391790
ADM_NOME=adm
ADM_EMAIL=adm@gmail.com
ADM_SENHA=adm123
EMAIL_REC_ENVIO=
SENHA_REC_ENVIO=

'''

if __name__ == '__main__':
    inicializar_banco()
    with app.app_context():
        db = get_db()
        admin = db.execute('SELECT * FROM admins WHERE tier=1').fetchone()
        if not admin:
            adm_nome = os.getenv("ADM_NOME")
            adm_email = os.getenv("ADM_EMAIL")
            adm_senha = os.getenv("ADM_SENHA")
            adm_senha_segura = generate_password_hash(adm_senha)
            db.execute('INSERT INTO admins (nome, email, senha, tier) VALUES (?, ?, ?, 1)', (adm_nome, adm_email, adm_senha_segura))
            db.commit()
        palavra = db.execute('SELECT * FROM palavras').fetchone()
        if not palavra:
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('BEM VINDO', 'Bem-vindo é uma saudação calorosa e inclusiva, usada para expressar a alegria e o prazer pela chegada de alguém a um novo local, evento ou grupo.', 'https://www.youtube.com/embed/RfdLdQUfZAg?si=sEKxZQ0qYcLNALau', 'RfdLdQUfZAg' ))
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('OBRIGADO', 'Segundo a gramática tradicional, a palavra obrigado é um adjetivo que, num contexto de agradecimento, significa que alguém se sente agradecido por alguma coisa, por algum favor que lhe tenha sido feito, sentindo-se obrigado a retribuir esse favor a quem o fez.', 'https://www.youtube.com/embed/_X2i1MXPCkA?si=OsJP8f2eIaMhRJ68', '_X2i1MXPCkA' ))
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('DE NADA', 'É uma forma cortês de se replicar um agradecimento de alguém, podendo ainda ser expresso de outras formas, como: “por nada”, “não há de quê”, “não seja por isso”, “eu que agradeço”, “obrigado você”, “obrigado eu”, “às ordens”, “imagina”, entre outras expressões populares.', 'https://www.youtube.com/embed/REsRmvi4ckk?si=58UcIlG7wPjBAJTc', 'REsRmvi4ckk' ))
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('POR FAVOR', '"Por favor" é uma locução adverbial de cortesia utilizada para suavizar pedidos, ordens ou solicitações, demonstrando polidez e gentileza. É frequentemente empregada ao fazer uma solicitação, para pedir um favor ou para aceitar uma oferta, demonstrando uma atitude amigável e respeitosa. ', 'https://www.youtube.com/embed/ZONwauXiwRc?si=1z3FIgdA8BaamXNW', 'ZONwauXiwRc' ))
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('OI', 'Exclamação que exprime admiração, espanto, e que se emprega também para chamamento e saudação.', 'https://www.youtube.com/embed/3iUZju5h5gw?si=JEYG-f0lPOzD9oAH', '3iUZju5h5gw' ))
            db.execute('INSERT INTO palavras (titulo, descricao, url, capa) VALUES (?, ?, ?, ?)', ('COMO ESTÁ?', 'Saudação comum em português, usada para perguntar sobre o estado físico ou emocional de alguém.', 'https://www.youtube.com/embed/XEaQnV4LnR8?si=OhOI1FF04veOXDE_', 'XEaQnV4LnR8' ))
            db.commit()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, port=port)