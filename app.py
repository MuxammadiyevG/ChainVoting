import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from flask import current_app

from models.models import db, User, Candidate, Election
from utils.blockchain import BlockchainClient
from utils.helpers import generate_ethereum_account, format_address, validate_ethereum_address
from config import Config
import csv
from io import StringIO
from flask import make_response

load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


blockchain = None

@app.before_request
def before_first_request():
    global blockchain
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        eth_account = generate_ethereum_account()
        admin = User(
            username='admin',
            email='admin@example.com',
            eth_address=eth_account['address'],
            is_admin=True
        )
        admin.set_password('admin123') 
        db.session.add(admin)
        db.session.commit()
        print(f"Admin yaratildi. ETH Address: {eth_account['address']}")
        print(f"Admin private key: {eth_account['private_key']}")
        print("Bu ma'lumotlarni saqlang! Ularni .env fayliga yozib qo'ying.")
        
        with open(".env", "a") as env_file:
            env_file.write(f"\nADMIN_ADDRESS={eth_account['address']}\n")
            env_file.write(f"ADMIN_PRIVATE_KEY={eth_account['private_key']}\n")
    
    
    abi_path = os.path.join(app.root_path, 'contracts/abi.json')
    if not os.path.exists(abi_path):
        
        os.makedirs(os.path.dirname(abi_path), exist_ok=True)
        
        try:
            from contracts.compile import deploy_contract
            admin_private_key = app.config.get('ADMIN_PRIVATE_KEY')
            provider_url = app.config.get('BLOCKCHAIN_PROVIDER')
            
            if admin_private_key:
                print("Kontraktni deploy qilish...")
                contract_address, _ = deploy_contract(provider_url, admin_private_key)
                print(f"Kontrakt muvaffaqiyatli deploy qilindi: {contract_address}")
                
                
                app.config['CONTRACT_ADDRESS'] = contract_address
            else:
                print("Admin private key topilmadi. Kontraktni deploy qilib bo'lmaydi.")
        except Exception as e:
            print(f"Kontraktni deploy qilishda xatolik: {str(e)}")
    
    
    try:
        blockchain = BlockchainClient()
        print(f"Blockchain ga ulanish: {'Muvaffaqiyatli' if blockchain.is_connected() else 'Muvaffaqiyatsiz'}")
        print(f"Kontrakt o'rnatilgan: {'Ha' if blockchain.is_contract_deployed() else 'Yo\'q'}")
    except Exception as e:
        print(f"Blockchain ga ulanishda xatolik: {str(e)}")
        
        

@app.route('/')
def index():
    
    active_election = Election.query.filter_by(is_active=True).first()
    return render_template('index.html', active_election=active_election)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        
        if not username or not email or not password:
            flash('Barcha maydonlarni to\'ldiring', 'danger')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Parollar mos kelmadi', 'danger')
            return redirect(url_for('register'))
            
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Bunday foydalanuvchi yoki email mavjud', 'danger')
            return redirect(url_for('register'))
            
        
        eth_account = generate_ethereum_account()
        
        
        new_user = User(
            username=username,
            email=email,
            eth_address=eth_account['address']
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
                        
        try:
            blockchain.send_eth(new_user.eth_address, 1)
            flash(f'1 ETH muvaffaqiyatli yuborildi! Manzil: {format_address(new_user.eth_address)}', 'success')
        except Exception as e:
            flash(f'ETH yuborishda xatolik: {str(e)}', 'warning')
        
        
        flash(f'Ro\'yxatdan o\'tdingiz! Ethereum address: {eth_account["address"]}', 'success')
        flash(f'Ethereum private key: {eth_account["private_key"]}. Bu kalitni saqlang!', 'warning')
        
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html')


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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Tizimdan chiqdingiz', 'info')
    return redirect(url_for('index'))

# Nomzodlar ro'yxati
@app.route('/candidates')
def candidates():
    
    candidates_list = Candidate.query.all()
    
    
    active_election = Election.query.filter_by(is_active=True).first()
    
    
    if blockchain and blockchain.is_connected() and active_election:
        for candidate in candidates_list:
            try:
                _, _, votes = blockchain.get_candidate(candidate.blockchain_id)
                candidate.votes = votes
            except Exception as e:
                print(f"Nomzod {candidate.id} uchun ovozlarni olishda xatolik: {str(e)}")
                candidate.votes = 0
                
    return render_template('candidates.html', candidates=candidates_list, active_election=active_election)

@app.route('/vote/<int:candidate_id>', methods=['GET', 'POST'])
@login_required
def vote(candidate_id):
    
    active_election = Election.query.filter_by(is_active=True).first()
    if not active_election:
        flash('Hozirda aktiv saylov yo\'q', 'warning')
        return redirect(url_for('candidates'))
    
    
    if current_user.has_voted:
        flash('Siz allaqachon ovoz bergansiz', 'warning')
        return redirect(url_for('results'))
    
    
    candidate = Candidate.query.get_or_404(candidate_id)
    
    
    w3 = Web3(Web3.HTTPProvider(app.config['BLOCKCHAIN_PROVIDER']))
    balance = w3.eth.get_balance(current_user.eth_address)
    min_required = w3.to_wei(0.0001, 'ether')  
    
    if balance < min_required:
        flash(f'Sizning hisobingizda yetarli ETH mavjud emas. Kamida 0.0001 ETH talab qilinadi. Hozirgi balans: {w3.from_wei(balance, "ether")} ETH', 'danger')
        return redirect(url_for('candidates'))
    
    if request.method == 'POST':
        private_key = request.form.get('private_key')
        
        if not private_key or not private_key.startswith('0x'):
            flash('Yaroqli ETH private key kiriting', 'danger')
            return redirect(url_for('vote', candidate_id=candidate_id))
        
        try:
            
            receipt = blockchain.vote(private_key, current_user.eth_address, candidate.blockchain_id)
            
            
            current_user.has_voted = True
            db.session.commit()
            
            flash(f'{candidate.name} uchun ovoz berdingiz!', 'success')
            return redirect(url_for('results'))
        except Exception as e:
            flash(f'Ovoz berishda xatolik: {str(e)}', 'danger')
    
    
    balance_eth = w3.from_wei(balance, 'ether')
    
    return render_template('vote.html', candidate=candidate, balance=balance_eth)

@app.route('/results')
def results():
    candidates_list = []

    election = Election.query.order_by(Election.end_date.desc()).first()

    if blockchain and blockchain.is_connected():
        try:
            raw_candidates = blockchain.get_all_candidates()

            
            seen_ids = set()
            for c in raw_candidates:
                if c['id'] not in seen_ids:
                    seen_ids.add(c['id'])
                    db_candidate = Candidate.query.filter_by(blockchain_id=c['id']).first()
                    if db_candidate:
                        c['full_name'] = db_candidate.name
                        c['party'] = db_candidate.party
                        c['image_url'] = db_candidate.image_url
                    candidates_list.append(c)

        except Exception as e:
            flash(f'Natijalarni olishda xatolik: {str(e)}', 'danger')

    return render_template('results.html', candidates=candidates_list, active_election=election)






@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
        
    
    users_count = User.query.count()
    candidates_count = Candidate.query.count()
    elections_count = Election.query.count()
    
    
    active_election = Election.query.filter_by(is_active=True).first()
    
    
    blockchain_status = "Ulanmagan"
    election_status = "Nofaol"
    
    if blockchain and blockchain.is_connected():
        blockchain_status = "Ulangan"
        
        try:
            if blockchain.contract.functions.electionStarted().call():
                if blockchain.contract.functions.electionEnded().call():
                    election_status = "Yakunlangan"
                else:
                    election_status = "Aktiv"
        except Exception as e:
            print(f"Blockchain holatini tekshirishda xatolik: {str(e)}")
            # Xatolik bo'lganda dastur ishini davom ettirish
    
    return render_template('admin/dashboard.html', 
                           users_count=users_count,
                           candidates_count=candidates_count,
                           elections_count=elections_count,
                           active_election=active_election,
                           blockchain_status=blockchain_status,
                           election_status=election_status)
    
"""   

@app.route('/admin/add_candidate', methods=['GET', 'POST'])

@login_required
def add_candidate():
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        name = request.form.get('name')
        party = request.form.get('party')
        bio = request.form.get('bio')

        image_url = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.root_path, 'static/images/candidates', filename)
                image.save(filepath)
                image_url = f'/static/images/candidates/{filename}'

        try:
            
            blockchain_id = blockchain.add_candidate(name)

            new_candidate = Candidate(
                name=name,
                party=party,
                bio=bio,
                image_url=image_url,
                blockchain_id=blockchain_id
            )

            db.session.add(new_candidate)
            db.session.commit()

            flash(f'Nomzod {name} muvaffaqiyatli qo‘shildi!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            flash(f'Nomzodni qo‘shishda xatolik: {str(e)}', 'danger')

    return render_template('admin/add_candidate.html')

"""

@app.route('/admin/add_candidate', methods=['GET', 'POST'])
@login_required
def add_candidate():
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        name = request.form.get('name')
        party = request.form.get('party')
        bio = request.form.get('bio')

        image_url = None
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.root_path, 'static/images/candidates', filename)
                image.save(filepath)
                image_url = f'/static/images/candidates/{filename}'

        try:
            # ✅ Nomzodni blockchain ga faqat bir marta qo‘shamiz
            blockchain_id = blockchain.add_candidate(name)

            new_candidate = Candidate(
                name=name,
                party=party,
                bio=bio,
                image_url=image_url,
                blockchain_id=blockchain_id
            )

            db.session.add(new_candidate)
            db.session.commit()

            flash(f'Nomzod {name} muvaffaqiyatli qo‘shildi!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            flash(f'Nomzodni qo‘shishda xatolik: {str(e)}', 'danger')

    return render_template('admin/add_candidate.html')



@app.route('/admin/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        abort(403)  # Ruxsat yo'q
    
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)


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
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            
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


@app.route('/admin/start_election/<int:election_id>')
@login_required
def start_election(election_id):
    if not current_user.is_admin:
        abort(403)  
    
    election = Election.query.get_or_404(election_id)
    
     
    candidates_count = Candidate.query.count()
    if candidates_count == 0:
        flash("Saylovni boshlash uchun kamida bitta nomzod qo'shilishi kerak", "danger")
        return redirect(url_for('admin_dashboard'))
    
    active_elections = Election.query.filter_by(is_active=True).all()
    for active_election in active_elections:
        active_election.is_active = False
    
    
    election.is_active = True
    db.session.commit()
    
    
    try:
        blockchain.start_election()
        flash(f'Saylov "{election.title}" boshlandi!', 'success')
    except Exception as e:
        flash(f'Saylovni boshlashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/end_election/<int:election_id>')
@login_required
def end_election(election_id):
    if not current_user.is_admin:
        abort(403) 
    
    election = Election.query.get_or_404(election_id)
    
    if not election.is_active:
        flash('Bu saylov hozirda aktiv emas', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    
    try:
        blockchain.end_election()
        
        election.is_active = False
        db.session.commit()
        
        flash(f'Saylov "{election.title}" yakunlandi!', 'success')
    except Exception as e:
        flash(f'Saylovni yakunlashda xatolik: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))



@app.route('/admin/fund_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def fund_user(user_id):
    if not current_user.is_admin:
        abort(403)  
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0.1))
        
        try:
            w3 = Web3(Web3.HTTPProvider(current_app.config['BLOCKCHAIN_PROVIDER']))
            admin_address = current_app.config['ADMIN_ADDRESS']
            admin_private_key = current_app.config['ADMIN_PRIVATE_KEY']
            
            amount_wei = w3.to_wei(amount, 'ether')
            
            
            tx = {
                'from': admin_address,
                'to': user.eth_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(admin_address)
            }
            
            
            signed_tx = w3.eth.account.sign_transaction(tx, admin_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            flash(f'Foydalanuvchi {user.username} hisobiga {amount} ETH muvaffaqiyatli yuborildi!', 'success')
            return redirect(url_for('manage_users'))
        except Exception as e:
            flash(f'Hisobni to\'ldirishda xatolik: {str(e)}', 'danger')
    
    return render_template('admin/fund_user.html', user=user)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@app.route('/results/download')
@login_required
def download_results():
    election = Election.query.order_by(Election.end_date.desc()).first()
    if not election:
        flash("Saylov topilmadi", "danger")
        return redirect(url_for('results'))

    
    candidates_list = []

    try:
        raw_candidates = blockchain.get_all_candidates()

        seen_ids = set()
        for c in raw_candidates:
            if c['id'] not in seen_ids:
                seen_ids.add(c['id'])
                db_candidate = Candidate.query.filter_by(blockchain_id=c['id']).first()
                if db_candidate:
                    c['full_name'] = db_candidate.name
                    c['party'] = db_candidate.party
                    c['image_url'] = db_candidate.image_url
                candidates_list.append(c)
    except Exception as e:
        flash(f'Natijalarni olishda xatolik: {str(e)}', 'danger')
        return redirect(url_for('results'))

    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Ism', 'Partiya', 'Ovozlar', 'Blockchain ID'])

    for c in candidates_list:
        writer.writerow([
            c.get('id'),
            c.get('full_name', ''),
            c.get('party', ''),
            c.get('votes') or c.get('voteCount', 0),
            c.get('id')  
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=saylov_natijalari.csv"
    output.headers["Content-type"] = "text/csv"
    return output


if __name__ == '__main__':
    app.run(debug=True)