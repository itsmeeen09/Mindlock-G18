from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, FocusCoin, StudyPass, User 
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mindlock_super_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to start your focus session! 🌸'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# --- Page Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/shop')
@login_required  # Redirects to /login if not logged in
def shop():
    return render_template('shop.html')

@app.route('/stats')
@login_required
def stats():
    # Filter logs by user_id
    user_logs = FocusCoin.query.filter_by(user_id=current_user.id).all()
    
    total_earned = sum(log.amount for log in user_logs)
    total_sessions = len(user_logs)
    
    return render_template(
        'stats.html', 
        logs=user_logs, 
        total_earned=total_earned, 
        total_sessions=total_sessions
    )

@app.route('/timer')
@login_required
def timer():
    return render_template('timer.html', has_2hr_pass=current_user.has_2hr_pass)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
            return redirect(url_for('login'))

        # Hash the password before saving
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, email=email, password=hashed_pw, coins=100)
        
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('timer'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Verify the password hash
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('timer'))
            
        flash('Invalid email or password!')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- API Endpoints ---

@app.route('/api/redeem-2hr-pass', methods=['POST'])
@login_required
def redeem_2hr_pass():
    cost = 100
    if current_user.coins >= cost:
        current_user.coins -= cost
        current_user.has_2hr_pass = True
        
        # Save active pass state in StudyPass table
        new_pass = StudyPass(user_id=current_user.id, pass_type='2hr_focus', is_active=True)
        db.session.add(new_pass)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '2-Hour Focus Pass unlocked! 🌸', 'new_balance': current_user.coins})
    
    return jsonify({'success': False, 'message': 'Not enough FocusCoins! 🪙'}), 400

@app.route('/api/earn-coins', methods=['POST'])
@login_required
def earn_coins():
    data = request.get_json() or {}
    duration_minutes = data.get('duration_minutes', 0)
    task_completed = data.get('task_completed', False)
    
    if duration_minutes <= 0:
        return jsonify({'error': 'Invalid duration'}), 400
    
    earned_amount = int(duration_minutes)
    
    if task_completed:
        if duration_minutes >= 120:
            earned_amount += 30
        elif duration_minutes >= 60:
            earned_amount += 15
        else:
            earned_amount += 5

    # Define maximum coin balance limit
    MAX_COINS = 200
    
    # Calculate capped amount so balance never exceeds MAX_COINS
    if current_user.coins >= MAX_COINS:
        actual_earned = 0
        message = f"You've reached the maximum limit of {MAX_COINS} FocusCoins! Spend some in the shop to earn more. 🪙"
    else:
        actual_earned = min(earned_amount, MAX_COINS - current_user.coins)
        current_user.coins += actual_earned
        message = f"Coins awarded successfully! (+{actual_earned} 🪙)"

    # Record actual earned amount in history log
    new_record = FocusCoin(
        user_id=current_user.id,
        amount=actual_earned, 
        reason=f"Completed {duration_minutes} min session"
    )
    db.session.add(new_record)
    db.session.commit()
    
    return jsonify({
        'message': message,
        'coins_earned': actual_earned,
        'total_coins': current_user.coins,
        'at_max_limit': current_user.coins >= MAX_COINS
    }), 200

    # API to unlock custom theme feature (Cost: 150 Coins)
@app.route('/api/buy-theme-pack', methods=['POST'])
@login_required
def buy_theme_pack():
    cost = 150
    if current_user.coins < cost:
        return jsonify({'success': False, 'message': 'Not enough FocusCoins! 🪙'}), 400
    
    current_user.coins -= cost
    current_user.has_custom_themes = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Custom Themes Unlocked! 🎨'})

# API to switch active theme
@app.route('/api/set-theme', methods=['POST'])
@login_required
def set_theme():
    if not current_user.has_custom_themes:
        return jsonify({'success': False, 'message': 'Unlock the theme pack first!'}), 403
    
    data = request.get_json() or {}
    new_theme = data.get('theme', 'pink')
    
    if new_theme in ['pink', 'matcha', 'lavender']:
        current_user.theme = new_theme
        db.session.commit()
        return jsonify({'success': True, 'theme': new_theme})
    
    return jsonify({'success': False, 'message': 'Invalid theme'}), 400

if __name__ == '__main__':
    app.run(debug=True)