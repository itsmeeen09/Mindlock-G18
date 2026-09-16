from datetime import date
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, FocusCoin, StudyPass, User, Streak, Achievement, UserAchievement
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

# Helper function to update study streak
def update_user_streak(user_id):
    streak = Streak.query.filter_by(user_id=user_id).first()
    if not streak:
        streak = Streak(user_id=user_id, current_streak=0, best_streak=0)
        db.session.add(streak)

    today = date.today()

    if streak.last_study_date == today:
        return  # Already studied today

    if streak.last_study_date and (today - streak.last_study_date).days == 1:
        streak.current_streak += 1
    else:
        streak.current_streak = 1  # Reset or first time

    if streak.current_streak > streak.best_streak:
        streak.best_streak = streak.current_streak

    streak.last_study_date = today
    db.session.commit()

# --- Achievement Engine ---
def check_and_award_achievements(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return

    # 1. Gather stats
    user_logs = FocusCoin.query.filter_by(user_id=user.id).all()
    total_sessions = len(user_logs)
    current_streak = user.streak_info.current_streak if user.streak_info else 0
    total_coins = user.coins

    # 2. Get unlocked achievement IDs
    user_achievements = getattr(user, 'achievements', [])
    unlocked_ids = {ua.achievement_id for ua in user_achievements}

    # 3. Evaluate criteria for all achievements
    all_achievements = Achievement.query.all()

    for achievement in all_achievements:
        if achievement.id in unlocked_ids:
            continue  # Already unlocked

        should_unlock = False

        # Evaluation Rules based on achievement titles seeded in your DB
        if achievement.title == 'First Focus' and total_sessions >= 1:
            should_unlock = True
        elif achievement.title == 'Streak Starter' and current_streak >= 3:
            should_unlock = True
        elif achievement.title == 'Coin Collector' and total_coins >= 100:
            should_unlock = True

        # Unlock achievement and award coin reward
        if should_unlock:
            new_unlock = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            user.coins += achievement.coin_reward
            db.session.add(new_unlock)

    db.session.commit()

# --- Page Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/shop')
@login_required
def shop():
    return render_template('shop.html')

@app.route('/stats')
@login_required
def stats():
    user_logs = FocusCoin.query.filter_by(user_id=current_user.id).all()
    total_earned = sum(log.amount for log in user_logs)
    total_sessions = len(user_logs)
    
    all_achievements = Achievement.query.all()
    
    # Query unlocked achievements directly for current_user
    user_unlocks = UserAchievement.query.filter_by(user_id=current_user.id).all()
    unlocked_ids = [ua.achievement_id for ua in user_unlocks]
    
    return render_template(
        'stats.html', 
        logs=user_logs, 
        total_earned=total_earned, 
        total_sessions=total_sessions,
        achievements=all_achievements,
        unlocked_ids=unlocked_ids
    )

@app.route('/achievements')
@login_required
def achievements():
    all_achievements = Achievement.query.all()
    user_unlocks = UserAchievement.query.filter_by(user_id=current_user.id).all()
    unlocked_ids = [ua.achievement_id for ua in user_unlocks]

    return render_template(
        'achievements.html',
        achievements=all_achievements,
        unlocked_ids=unlocked_ids
    )

@app.route('/timer')
@login_required
def timer():
    return render_template('timer.html', has_2hr_pass=current_user.has_2hr_pass)

@app.route('/purchase/<string:item_type>/<string:item_id>', methods=['POST'])
@login_required
def purchase(item_type, item_id):
    shop_items = {
        'pass_2hr_pass': {'cost': 100, 'name': '2-Hour Focus Pass'},
        'theme_matcha': {'cost': 80, 'name': 'Matcha Green Theme'},
        'theme_lavender': {'cost': 80, 'name': 'Lavender Dreams Theme'},
        'theme_terracotta': {'cost': 120, 'name': 'Terracotta Warmth Theme'}
    }

    key = f"{item_type}_{item_id}"
    item = shop_items.get(key)

    if not item:
        flash("Invalid item selected.", "error")
        return redirect(url_for('shop'))

    cost = item['cost']

    if current_user.coins < cost:
        flash("Not enough coins to purchase this item!", "error")
        return redirect(url_for('shop'))

    current_user.coins -= cost

    if item_type == 'theme':
        current_user.theme = item_id
        current_user.has_custom_themes = True
        flash(f"Unlocked and applied {item['name']}! 🎨", "success")
    elif item_type == 'pass':
        current_user.has_2hr_pass = True
        new_pass = StudyPass(user_id=current_user.id, pass_type='2hr_focus', is_active=True)
        db.session.add(new_pass)
        flash(f"Redeemed 1x {item['name']}! 🎫", "success")

    db.session.commit()
    return redirect(url_for('shop'))

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

        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, email=email, password=hashed_pw, coins=50)
        
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

@app.route('/api/complete-session', methods=['POST'])
@login_required
def complete_session():
    data = request.get_json() or {}
    duration_seconds = data.get('duration', 0)
    is_demo = data.get('is_demo', False)
    
    if duration_seconds <= 0:
        return jsonify({'success': False, 'message': 'Invalid session duration'}), 400

    if is_demo:
        coins_earned = duration_seconds
    else:
        coins_earned = max(1, duration_seconds // 60)

    MAX_COINS = 200
    actual_earned = min(coins_earned, max(0, MAX_COINS - current_user.coins))
    current_user.coins += actual_earned

    # Always log the session record (even if 0 coins earned due to max cap)
    new_record = FocusCoin(
        user_id=current_user.id,
        amount=actual_earned, 
        reason=f"Completed {'demo' if is_demo else 'focus'} session"
    )
    db.session.add(new_record)
    db.session.commit()  # Save log first so len(user_logs) counts it immediately
    
    # Update streak & achievements
    update_user_streak(current_user.id)
    check_and_award_achievements(current_user.id)

    return jsonify({
        'success': True,
        'coins_earned': actual_earned,
        'total_coins': current_user.coins,
        'current_streak': current_user.streak_info.current_streak if current_user.streak_info else 1
    }), 200

@app.route('/api/redeem-2hr-pass', methods=['POST'])
@login_required
def redeem_2hr_pass():
    cost = 100
    if current_user.coins >= cost:
        current_user.coins -= cost
        current_user.has_2hr_pass = True
        
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

    MAX_COINS = 200
    
    if current_user.coins >= MAX_COINS:
        actual_earned = 0
        message = f"You've reached the maximum limit of {MAX_COINS} FocusCoins! Spend some in the shop to earn more. 🪙"
    else:
        actual_earned = min(earned_amount, MAX_COINS - current_user.coins)
        current_user.coins += actual_earned
        message = f"Coins awarded successfully! (+{actual_earned} 🪙)"

    new_record = FocusCoin(
        user_id=current_user.id,
        amount=actual_earned, 
        reason=f"Completed {duration_minutes} min session"
    )
    db.session.add(new_record)
    
    # Update streak upon earning coins from session
    update_user_streak(current_user.id)
    
    # Check and award achievements
    check_and_award_achievements(current_user.id)
    
    db.session.commit()
    
    return jsonify({
        'message': message,
        'coins_earned': actual_earned,
        'total_coins': current_user.coins,
        'at_max_limit': current_user.coins >= MAX_COINS,
        'current_streak': current_user.streak_info.current_streak if current_user.streak_info else 1
    }), 200


@app.route('/api/buy-theme', methods=['POST'])
@login_required
def buy_theme():
    data = request.get_json()
    theme_id = data.get('theme_id')

    theme_prices = {
        'sakura': 80,
        'matcha': 100,
        'sunset': 120,
        'midnight': 150
    }

    if theme_id not in theme_prices:
        return jsonify({'success': False, 'message': 'Invalid theme.'}), 400

    cost = theme_prices[theme_id]

    if current_user.coins < cost:
        return jsonify({'success': False, 'message': f'Not enough coins! You need {cost} coins.'}), 400

    unlocked = current_user.unlocked_themes.split(',') if current_user.unlocked_themes else ['pastel']

    if theme_id in unlocked:
        return jsonify({'success': False, 'message': 'Theme already unlocked!'}), 400

    current_user.coins -= cost
    unlocked.append(theme_id)
    current_user.unlocked_themes = ','.join(unlocked)
    current_user.theme = theme_id
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'Unlocked and applied {theme_id.capitalize()} theme! 🎨'})


@app.route('/api/set-theme', methods=['POST'])
@login_required
def set_theme():
    data = request.get_json()
    theme_id = data.get('theme')

    unlocked = current_user.unlocked_themes.split(',') if current_user.unlocked_themes else ['pastel']

    if theme_id == 'pastel' or theme_id in unlocked:
        current_user.theme = theme_id
        db.session.commit()
        return jsonify({'success': True, 'message': f'Theme changed to {theme_id}!'})

    return jsonify({'success': False, 'message': 'You have not unlocked this theme yet.'}), 403

if __name__ == '__main__':
    app.run(debug=True)