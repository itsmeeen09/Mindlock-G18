from datetime import date, datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, FocusCoin, StudyPass, User, Streak, Achievement, UserAchievement, StudySession, Task, FocusInterruptionRecord
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


# Create database tables and seed initial achievements
with app.app_context():
    db.create_all()

    # Define initial achievement list (8 total)
    initial_achievements = [
        {
            "id": 1,
            "title": "First Step",
            "description": "Complete one focus session",
            "icon": "🌱",
            "coin_reward": 10
        },
        {
            "id": 2,
            "title": "Consistency is Key (3 Days)",
            "description": "Maintain a 3-day streak",
            "icon": "🔥",
            "coin_reward": 20
        },
        {
            "id": 3,
            "title": "Consistency is Key (7 Days)",
            "description": "Maintain a 7-day streak",
            "icon": "⚡",
            "coin_reward": 30
        },
        {
            "id": 4,
            "title": "Consistency is Key (14 Days)",
            "description": "Maintain a 14-day streak",
            "icon": "👑",
            "coin_reward": 50
        },
        {
            "id": 5,
            "title": "Night Bird",
            "description": "Start and complete a session after 12:00 AM",
            "icon": "🦉",
            "coin_reward": 20
        },
        {
            "id": 6,
            "title": "Early Bird",
            "description": "Start and complete a session after 6:00 AM",
            "icon": "🌅",
            "coin_reward": 20
        },
        {
            "id": 7,
            "title": "Deep Focus",
            "description": "Complete a 1-hour focus session with no pauses",
            "icon": "🎯",
            "coin_reward": 50
        },
        {
            "id": 8,
            "title": "Phoenix",
            "description": "Resume a streak within 24 hours of losing a long one",
            "icon": "🔥",
            "coin_reward": 40
        }
    ]

    for item in initial_achievements:
        existing = db.session.get(Achievement, item["id"])
        if not existing:
            existing_title = Achievement.query.filter_by(
                title=item["title"]).first()
            if not existing_title:
                achievement = Achievement(
                    id=item["id"],
                    title=item["title"],
                    description=item["description"],
                    icon=item["icon"],
                    coin_reward=item["coin_reward"]
                )
                db.session.add(achievement)

    db.session.commit()

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
        # Check if user had a solid previous streak (e.g. 3+ days) before resetting
        # This flags potential eligibility for the Phoenix achievement
        if streak.current_streak >= 3 and streak.last_study_date and (today - streak.last_study_date).days == 2:
            streak.just_recovered_streak = True
        else:
            streak.just_recovered_streak = False

        streak.current_streak = 1  # Reset/restart streak

    if streak.current_streak > streak.best_streak:
        streak.best_streak = streak.current_streak

    streak.last_study_date = today
    db.session.commit()

# --- Achievement Engine ---


def check_and_award_achievements(user_id, session_data=None):
    user = db.session.get(User, user_id)
    if not user:
        return

    session_data = session_data or {}

    # Gather user stats
    user_logs = FocusCoin.query.filter_by(user_id=user.id).all()
    total_sessions = len(user_logs)
    streak_info = user.streak_info
    current_streak = streak_info.current_streak if streak_info else 0

    # Get already unlocked achievement IDs
    user_unlocks = UserAchievement.query.filter_by(user_id=user.id).all()
    unlocked_ids = {ua.achievement_id for ua in user_unlocks}

    all_achievements = Achievement.query.all()

    for achievement in all_achievements:
        if achievement.id in unlocked_ids:
            continue  # Skip if already unlocked

        should_unlock = False
        title = achievement.title

        # First Step (10 coins)
        if title == "First Step" and total_sessions >= 1:
            should_unlock = True

        # Consistency is Key (3, 7, 14 days)
        elif title == "Consistency is Key (3 Days)" and current_streak >= 3:
            should_unlock = True
        elif title == "Consistency is Key (7 Days)" and current_streak >= 7:
            should_unlock = True
        elif title == "Consistency is Key (14 Days)" and current_streak >= 14:
            should_unlock = True

        # Phoenix: Resume streak right after losing a long one (e.g. 3+ day streak)
        elif title == "Phoenix" and streak_info and getattr(streak_info, 'just_recovered_streak', False):
            should_unlock = True

        # Time/Session Specific Checks (Pass session_data if available)
        if session_data:
            start_hour = session_data.get('start_hour')  # 0-23
            duration_minutes = session_data.get('duration_minutes', 0)
            pauses = session_data.get('pauses', 0)

            # Night Bird: Start/complete session after 12:00 AM (0:00 - 4:59 AM)
            if title == "Night Bird" and start_hour is not None and 0 <= start_hour < 5:
                should_unlock = True

            # Early Bird: Start/complete session after 6:00 AM (6:00 - 9:59 AM)
            elif title == "Early Bird" and start_hour is not None and 6 <= start_hour < 10:
                should_unlock = True

            # Deep Focus: 1 hour (60 min) focus session with no pauses
            elif title == "Deep Focus" and duration_minutes >= 60 and pauses == 0:
                should_unlock = True

        # Unlock and grant coins
        if should_unlock:
            new_unlock = UserAchievement(
                user_id=user.id, achievement_id=achievement.id)
            user.coins += achievement.coin_reward
            db.session.add(new_unlock)

    db.session.commit()

# --- Page Routes ---


@app.route('/')
def index():
    return redirect(url_for('login'))

# route home


@app.route('/home')
@login_required
def study_home():
    return render_template('study_index.html')

# route shop


@app.route('/shop')
@login_required
def shop():
    return render_template('shop.html')


@app.route('/stats')
@login_required
def stats():
    # 1. Fetch user coin logs
    user_logs = FocusCoin.query.filter_by(user_id=current_user.id).all()
    total_earned = sum(log.amount for log in user_logs)

    # 2. Fetch achievements
    all_achievements = Achievement.query.all()
    user_unlocks = UserAchievement.query.filter_by(
        user_id=current_user.id).all()
    unlocked_ids = [ua.achievement_id for ua in user_unlocks]

    # 3. Calculate student metrics from FocusCoin
    total_sessions = len(user_logs)
    # Defines the variable so Flask doesn't crash!
    completed_sessions = total_sessions

    # Calculate focus hours (assuming ~25 mins per logged session)
    total_minutes = total_sessions * 25
    total_hours = round(total_minutes / 60, 1)

    # Default progress %
    progress = 100

    return render_template(
        'stats.html',
        logs=user_logs,
        total_earned=total_earned,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        achievements=all_achievements,
        unlocked_ids=unlocked_ids,
        total_hours=total_hours,
        progress=progress
    )


@app.route('/achievements')
@login_required
def achievements():
    # 1. Fetch only the 2 achievements you want to present
    all_achievements = Achievement.query.filter(
        Achievement.id.in_([1, 2])).all()

    # 2. Get the list of IDs currently being displayed ([1, 2])
    visible_ids = [a.id for a in all_achievements]

    # 3. Only count unlocks that match the visible achievements!
    user_unlocks = UserAchievement.query.filter(
        UserAchievement.user_id == current_user.id,
        UserAchievement.achievement_id.in_(visible_ids)
    ).all()

    unlocked_ids = [ua.achievement_id for ua in user_unlocks]

    return render_template(
        'achievements.html',
        achievements=all_achievements,
        unlocked_ids=unlocked_ids
    )


@app.route('/timer')
def timer():
    return redirect(url_for('index'))  # Redirects straight to your dashboard!


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
        new_pass = StudyPass(user_id=current_user.id,
                             pass_type='2hr_focus', is_active=True)
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
        new_user = User(username=username, email=email,
                        password=hashed_pw, coins=50)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('study_home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('study_home'))

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

        new_pass = StudyPass(user_id=current_user.id,
                             pass_type='2hr_focus', is_active=True)
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

    unlocked = current_user.unlocked_themes.split(
        ',') if current_user.unlocked_themes else ['pastel']

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

    unlocked = current_user.unlocked_themes.split(
        ',') if current_user.unlocked_themes else ['pastel']

    if theme_id in ['pastel', 'pink', 'sakura', 'default'] or theme_id in unlocked:
        current_user.theme = theme_id
        db.session.commit()
        return jsonify({'success': True, 'message': f'Theme changed to {theme_id}!'})

    return jsonify({'success': False, 'message': 'You have not unlocked this theme yet.'}), 403


# =========================
# STUDY MANAGEMENT ROUTES
# =========================

@app.route("/sessions/create", methods=["GET", "POST"])
def create_session():
    # If the user submitted the form...
    if request.method == "POST":
        # Get the session title from the form.
        title = request.form["title"]

        # Create a new StudySession object.
        session = StudySession(title=title)

        # Add the new session to the database.
        db.session.add(session)

        # Save the changes to the database.
        db.session.commit()

        # Send the user to the task creation page.
        return redirect(url_for("create_task", session_id=session.id))

    return render_template("create_session.html")


@app.route("/sessions")
def view_sessions():
    sessions = StudySession.query.all()
    return render_template("sessions.html", sessions=sessions)


@app.route("/sessions/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    # Find the study session.
    session = StudySession.query.get_or_404(session_id)

    # Delete all tasks belonging to this session.
    for task in session.tasks:
        db.session.delete(task)

    # Delete the study session.
    db.session.delete(session)

    # Save the changes.
    db.session.commit()

    # Return to the My Study Sessions page.
    return redirect(url_for("view_sessions"))


@app.route("/tasks/create/<int:session_id>", methods=["GET", "POST"])
def create_task(session_id):
    # Find the study session that this task belongs to.
    session = StudySession.query.get_or_404(session_id)

    if request.method == "POST":
        # Get the task title from the form.
        title = request.form["title"]

        # Get the task duration from the form.
        duration = int(request.form["duration"])

        # Create a new task with the title and selected duration.
        task = Task(
            title=title,
            duration=duration,
            study_session_id=session.id
        )

        # Add the new task to the database.
        db.session.add(task)

        # Save the new task.
        db.session.commit()

        # Return to the My Study Sessions page.
        return redirect(url_for("view_sessions"))

    return render_template("create_task.html", session=session)


@app.route("/tasks/<int:task_id>/focus")
def task_focus_mode(task_id):
    # Find the task the user wants to focus on.
    task = Task.query.get_or_404(task_id)

    interruptions = FocusInterruptionRecord.query.filter_by(
        task_id=task.id
    ).all()

    total_interruption_seconds = 0

    for interruption in interruptions:
        # Only count interruptions that have ended.
        if interruption.ended_at is not None:
            duration = interruption.ended_at - interruption.started_at
            total_interruption_seconds += int(duration.total_seconds())

    return render_template(
        "task_focus_mode.html",
        task=task,
        interruption_count=len(interruptions),
        interruption_time=total_interruption_seconds
    )


@app.route("/tasks/<int:task_id>/start", methods=["POST"])
def start_task(task_id):
    # Find the task.
    task = Task.query.get_or_404(task_id)

    if task.status == "completed":
        task.remaining_time = task.duration * 60

    task.status = "ongoing"
    task.completed = False

    db.session.commit()

    return redirect(url_for("task_focus_mode", task_id=task.id))


@app.route("/tasks/<int:task_id>/pause", methods=["POST"])
def pause_task(task_id):
    # Find the task.
    task = Task.query.get_or_404(task_id)

    # Get the remaining time from the Focus Mode timer.
    remaining_time = request.form.get("remaining_time", type=int)

    # Keep the task as ongoing.
    task.status = "ongoing"

    # Save the remaining time.
    task.remaining_time = remaining_time

    # Save the changes to the database.
    db.session.commit()

    # Return to Task Focus Mode.
    return redirect(url_for("task_focus_mode", task_id=task.id))


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    # Find the task.
    task = Task.query.get_or_404(task_id)

    # Check if the task was already completed.
    was_completed = task.status == "completed"

    # Mark the task as completed.
    task.status = "completed"

    # Keep the completed field in sync.
    task.completed = True

    # Set the remaining time to zero.
    task.remaining_time = 0

    # Check if all tasks in this study session are now completed.
    session = task.study_session

    total_tasks = len(session.tasks)
    completed_tasks = sum(
        1 for session_task in session.tasks
        if session_task.status == "completed"
    )

    # Reward 50 FocusCoins when the session reaches 100%.
    if (
        not was_completed
        and total_tasks > 0
        and completed_tasks == total_tasks
    ):
        reward = min(50, max(0, 200 - current_user.coins))
        current_user.coins += reward

        # Record the FocusCoin reward.
        new_record = FocusCoin(
            user_id=current_user.id,
            amount=reward,
            reason="Completed study session"
        )
        db.session.add(new_record)

        # Update the user's study streak.
        update_user_streak(current_user.id)

        # Check if completing this session unlocks an achievement.
        check_and_award_achievements(current_user.id)

    # Save the changes to the database.
    db.session.commit()

    # Return to the My Tasks page.
    return redirect(url_for("view_tasks"))


@app.route("/tasks")
def view_tasks():
    sessions = StudySession.query.all()

    # Calculate completion percentage for each session.
    for session in sessions:
        total_tasks = len(session.tasks)

        completed_tasks = sum(
            1 for task in session.tasks
            if task.status == "completed"
        )

        if total_tasks > 0:
            session.progress = (completed_tasks / total_tasks) * 100
        else:
            session.progress = 0

    return render_template("tasks.html", sessions=sessions)


@app.route("/tasks/<int:task_id>/status/<status>", methods=["POST"])
def update_task_status(task_id, status):
    # Find the task.
    task = Task.query.get_or_404(task_id)

    if status == "upcoming" and task.status == "completed":
        task.remaining_time = task.duration * 60

    was_completed = task.status == "completed"
    task.status = status
    task.completed = status == "completed"

    # Check if all tasks in this study session are now completed.
    session = task.study_session

    total_tasks = len(session.tasks)
    completed_tasks = sum(
        1 for session_task in session.tasks
        if session_task.status == "completed"
    )
    # Reward 50 FocusCoins when the session reaches 100%.
    if (
        status == "completed"
        and not was_completed
        and total_tasks > 0
        and completed_tasks == total_tasks
    ):
        reward = min(50, max(0, 200 - current_user.coins))
        current_user.coins += reward

        # Record the FocusCoin reward.
        new_record = FocusCoin(
            user_id=current_user.id,
            amount=reward,
            reason="Completed study session"
        )
        db.session.add(new_record)
        # Check if completing this session unlocks an achievement.
        check_and_award_achievements(current_user.id)

    db.session.commit()

    return redirect(url_for("view_tasks"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    # Find the task.
    task = Task.query.get_or_404(task_id)

    # Delete the task.
    db.session.delete(task)

    # Save the change.
    db.session.commit()

    # Return to the My Tasks page.
    return redirect(url_for("view_tasks"))


# =========================
# FOCUS INTERRUPTION ROUTES
# =========================

@app.route("/tasks/<int:task_id>/interruptions/start", methods=["POST"])
def start_interruption(task_id):
    # Find the task that was interrupted.
    task = Task.query.get_or_404(task_id)

    interruption = FocusInterruptionRecord(
        task_id=task.id,
        started_at=datetime.utcnow()
    )

    db.session.add(interruption)
    db.session.commit()

    return jsonify({"interruption_id": interruption.id})


@app.route(
    "/tasks/<int:task_id>/interruptions/<int:record_id>/end",
    methods=["POST"]
)
def end_interruption(task_id, record_id):
    # Find the interruption record.
    interruption = FocusInterruptionRecord.query.get_or_404(record_id)

    interruption.ended_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"success": True})


@app.route("/tasks/<int:task_id>/interruptions", methods=["GET"])
def get_interruptions(task_id):
    # Find all interruptions recorded for this task.
    interruptions = FocusInterruptionRecord.query.filter_by(
        task_id=task_id
    ).all()

    total_seconds = 0

    for interruption in interruptions:
        # Only calculate time for completed interruptions.
        if interruption.ended_at is not None:
            duration = interruption.ended_at - interruption.started_at
            total_seconds += int(duration.total_seconds())

    return jsonify({
        "count": len(interruptions),
        "total_seconds": total_seconds
    })


if __name__ == '__main__':
    app.run(debug=True)
