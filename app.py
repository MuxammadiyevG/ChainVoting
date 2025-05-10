import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3

# Loyiha modullarini import qilish
from models.models import db, User, Candidate, Election
from utils.blockchain import BlockchainClient
from utils.helpers import generate_ethereum_account, format_address, validate_ethereum_address
from config import Config

# .env faylini o'qish
load_dotenv()

# Flask ilovasini yaratish
app = Flask(__name__)
app.config.from_object(Config)

# Ma'lumotlar bazasini inizializatsiya qilish
db.init_app(app)

# Login manager sozlash
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Global blockchain client
blockchain = None

@app.before_request
def before_first_request():
    global blockchain
    # Ma'lumotlar bazasini yaratish
    db.create_all()
    
    # Admin foydalanuvchisini yaratish (agar yo'q bo'lsa)
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        eth_account = generate_ethereum_account()
        admin = User(
            username='admin',
            email='admin@example.com',
            eth_address=eth_account['address'],
            is_admin=True
        )
        admin.set_password('admin123')  # Bu yerda xavfsiz parol qo'yish kerak
        db.session.add(admin)
        db.session.commit()
        print(f"Admin yaratildi. ETH Address: {eth_account['address']}")
        print(f"Admin private key: {eth_account['private_key']}")
        print("Bu ma'lumotlarni saqlang! Ularni .env fayliga yozib qo'ying.")
    
    # Blockchain clientni yaratish
    try:
        blockchain = BlockchainClient()
        print(f"Blockchain ga ulanish: {'Muvaffaqiyatli' if blockchain.is_connected() else 'Muvaffaqiyatsiz'}")
    except Exception as e:
        print(f"Blockchain ga ulanishda xatolik: {str(e)}")

# Bosh sahifa
@app.route('/')
def index():
    # Aktiv saylovni olish
    active_election = Election.query.filter_by(is_active=True).first()
    return render_template('index.html', active_election=active_election)

# Ro'yxatdan o'tish
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validatsiya
        if not username or not email or not password:
            flash('Barcha maydonlarni to\'ldiring', 'danger')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Parollar mos kelmadi', 'danger')
            return redirect(url_for('register'))
            
        # Foydalanuvchini tekshirish
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Bunday foydalanuvchi yoki email mavjud', 'danger')
            return redirect(url_for('register'))
            
        # Ethereum akkountini yaratish
        eth_account = generate_ethereum_account()
        
        # Yangi foydalanuvchini yaratish
        new_user = User(
            username=username,
            email=email,
            eth_address=eth_account['address']
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Ro\'yxatdan o\'tdingiz! Ethereum address: {eth_account["address"]}', 'success')
        flash(f'Ethereum private key: {eth_account["private_key"]}. Bu kalitni saqlang!', 'warning')
        
        # Foydalanuvchini tizimga kiritish
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html')

# Tizimga kirish
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Tizimga kirdingiz!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login yoki parol noto\'g\'ri', 'danger')
            
    return render_template('login.html')

# Tizimdan chiqish
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Tizimdan chiqdingiz', 'info')
    return redirect(url_for('index'))

# Nomzodlar ro'yxati
@app.route('/candidates')
def candidates():
    # Barcha nomzodlarni olish
    candidates_list = Candidate.query.all()
    
    # Aktiv saylovni olish
    active_election = Election.query.filter_by(is_active=True).first()
    
    # Blockchaindagi ovozlarni olish
    if blockchain and blockchain.is_connected() and active_election:
        for candidate in candidates_list:
            try:
                _, _, votes = blockchain.get_candidate(candidate.blockchain_id)
                candidate.votes = votes
            except Exception as e:
                print(f"Nomzod {candidate.id} uchun ovozlarni olishda xatolik: {str(e)}")
                candidate.votes = 0
                
    return render_template('candidates.html', candidates=candidates_list, active_election=active_election)

# Ovoz berish
@app.route('/vote/<int:candidate_id>', methods=['GET', 'POST'])
@login_required
def vote(candidate_id):
    # Aktiv saylovni tekshirish
    active_election = Election.query.filter_by(is_active=True).first()
    if not active_election:
        flash('Hozirda aktiv saylov yo\'q', 'warning')
        return redirect(url_for('candidates'))
    
    # Foydalanuvchi ovoz berganligini tekshirish
    if current_user.has_voted:
        flash('Siz allaqachon ovoz bergansiz', 'warning')
        return redirect(url_for('results'))
    
    # Nomzodni olish
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if request.method == 'POST':
        private_key = request.form.get('private_key')
        
        if not private_key or not private_key.startswith('0x'):
            flash('Yaroqli ETH private key kiriting', 'danger')
            return redirect(url_for('vote', candidate_id=candidate_id))
        
        try:
            # Blockchainda ovoz berish
            receipt = blockchain.vote(private_key, current_user.eth_address, candidate.blockchain_id)
            
            # Foydalanuvchining ovoz berganligini belgilash
            current_user.has_voted = True
            db.session.commit()
            
            flash(f'{candidate.name} uchun ovoz berdingiz!', 'success')
            return redirect(url_for('results'))
        except Exception as e:
            flash(f'Ovoz berishda xatolik: {str(e)}', 'danger')
            
    return render_template('vote.html', candidate=candidate)

# Natijalar
@app.route('/results')
def results():
    candidates_list = []
    
    # Aktiv saylovni olish
    active_election = Election.query.filter_by(is_active=True).first()
    
    if blockchain and blockchain.is_connected():
        try:
            # Blockchaindagi barcha nomzodlarni olish
            candidates_list = blockchain.get_all_candidates()
            
            # Nomzodlar haqida qo'shimcha ma'lumotlarni olish
            for candidate_data in candidates_list:
                db_candidate = Candidate.query.filter_by(blockchain_id=candidate_data['id']).first()
                if db_candidate:
                    candidate_data['full_name'] = db_candidate.name
                    candidate_data['party'] = db_candidate.party
                    candidate_data['image_url'] = db_candidate.image_url
                    
        except Exception as e:
            flash(f'Natijalarni olishda xatolik: {str(e)}', 'danger')
            
    return render_template('results.html', candidates=candidates_list, active_election=active_election)

# Admin panel - boshqaruv
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
        
    # Statistikani olish
    users_count = User.query.count()
    candidates_count = Candidate.query.count()
    elections_count = Election.query.count()
    
    # Aktiv saylovni olish
    active_election = Election.query.filter_by(is_active=True).first()
    
    # Blockchain holati
    blockchain_status = "Ulanmagan"
    election_status = "Nofaol"
    
    if blockchain and blockchain.is_connected():
        blockchain_status = "Ulangan"
        
        if blockchain.contract.functions.electionStarted().call():
                if blockchain.contract.functions.electionEnded().call():
                    election_status = "Yakunlangan"
                else:
                    election_status = "Aktiv"
    
    return render_template('admin/dashboard.html', 
                           users_count=users_count,
                           candidates_count=candidates_count,
                           elections_count=elections_count,
                           active_election=active_election,
                           blockchain_status=blockchain_status,
                           election_status=election_status)

# Admin panel - nomzod qo'shish
@app.route('/admin/add_candidate', methods=['GET', 'POST'])
@login_required
def add_candidate():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    if request.method == 'POST':
        name = request.form.get('name')
        party = request.form.get('party')
        bio = request.form.get('bio')
        
        # Rasmni yuklash
        image_url = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.root_path, 'static/images/candidates', filename)
                image.save(filepath)
                image_url = f'/static/images/candidates/{filename}'
        
        # Nomzodni blockchain ga qo'shish
        try:
            receipt = blockchain.add_candidate(name)
            # Blockchainda qo'shilgan nomzod ID sini olish
            blockchain_id = blockchain.get_candidates_count()
            
            # Ma'lumotlar bazasiga nomzodni qo'shish
            new_candidate = Candidate(
                name=name,
                party=party,
                bio=bio,
                image_url=image_url,
                blockchain_id=blockchain_id
            )
            
            db.session.add(new_candidate)
            db.session.commit()
            
            flash(f'Nomzod {name} muvaffaqiyatli qo\'shildi!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Nomzodni qo\'shishda xatolik: {str(e)}', 'danger')
    
    return render_template('admin/add_candidate.html')

# Admin panel - foydalanuvchilarni boshqarish
@app.route('/admin/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

# Admin panel - saylovni boshqarish
@app.route('/admin/manage_elections', methods=['GET', 'POST'])
@login_required
def manage_elections():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Yangi saylovni qo'shish
            new_election = Election(
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date
            )
            
            db.session.add(new_election)
            db.session.commit()
            
            flash(f'Yangi saylov "{title}" muvaffaqiyatli yaratildi', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Saylovni yaratishda xatolik: {str(e)}', 'danger')
    
    elections = Election.query.all()
    return render_template('admin/manage_elections.html', elections=elections)

# Admin panel - saylovni boshlatish
@app.route('/admin/start_election/<int:election_id>')
@login_required
def start_election(election_id):
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    election = Election.query.get_or_404(election_id)
    
    # Boshqa aktiv saylovlarni to'xtatish
    active_elections = Election.query.filter_by(is_active=True).all()
    for active_election in active_elections:
        active_election.is_active = False
    
    # Yangi saylovni aktivlashtirish
    election.is_active = True
    db.session.commit()
    
    # Blockchainda saylovni boshlatish
    try:
        blockchain.start_election()
        flash(f'Saylov "{election.title}" boshlandi!', 'success')
    except Exception as e:
        flash(f'Saylovni boshlashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

# Admin panel - saylovni yakunlash
@app.route('/admin/end_election/<int:election_id>')
@login_required
def end_election(election_id):
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    election = Election.query.get_or_404(election_id)
    
    if not election.is_active:
        flash('Bu saylov hozirda aktiv emas', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    # Blockchainda saylovni yakunlash
    try:
        blockchain.end_election()
        
        # Ma'lumotlar bazasida saylovni yakunlash
        election.is_active = False
        db.session.commit()
        
        flash(f'Saylov "{election.title}" yakunlandi!', 'success')
    except Exception as e:
        flash(f'Saylovni yakunlashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)