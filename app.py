# app.py
from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit
from flask import render_template, url_for
from flask import send_file, send_from_directory
import os
from werkzeug.utils import secure_filename
import random
import string
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Set maximum file size to 16 MB
socketio = SocketIO(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Dummy user data (replace with a database in production)
users = {}

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_challenge():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operator = random.choice(['+', '-', '*'])
    challenge = f"{num1} {operator} {num2}"
    answer = eval(challenge)  # Evaluate the expression to get the answer
    return challenge, answer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle login logic here
        username = request.form.get('username')
        password = request.form.get('password')

        # Verify the challenge response
        user_answer = int(request.form.get('challenge_response', 0))
        if 'challenge' in session:
            correct_answer = session['challenge']['answer']
            if user_answer != correct_answer:
                flash('Challenge verification failed. Please try again.', 'error')
                return redirect(url_for('index'))
        else:
            flash('Challenge verification failed. Please try again.', 'error')
            return redirect(url_for('index'))

        # Continue with login logic
        if username in users and users[username]['password'] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('index'))

    # Generate and store the challenge in the session
    challenge, answer = generate_challenge()
    session['challenge'] = {'text': challenge, 'answer': answer}

    # If the method is GET, render the login form
    return render_template('login.html', challenge=challenge)

@app.route('/file_transfer', methods=['GET', 'POST'])
def file_transfer():
    image_preview = None
    error = None

    if request.method == 'POST':
        # Handle file upload logic
        if 'file' not in request.files:
            error = 'No file part'
        else:
            file = request.files['file']

            if file.filename == '':
                error = 'No selected file'
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_preview = url_for('uploaded_file', filename=filename)
                else:
                    return send_file(file_path, as_attachment=True)

    return render_template('file_transfer.html', image_preview=image_preview, error=error)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=False)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username not in users:
            users[username] = {'password': password}
            session['username'] = username
            flash('Registration successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('index'))

    # Generate and store the challenge in the session
    challenge, answer = generate_challenge()
    session['challenge'] = {'text': challenge, 'answer': answer}

    # If the method is GET, render the registration form
    return render_template('register.html', challenge=challenge)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Verify the challenge response
    user_answer = int(request.form.get('challenge_response', 0))
    if 'challenge' in session:
        correct_answer = session['challenge']['answer']
        if user_answer != correct_answer:
            flash('Challenge verification failed. Please try again.', 'error')
            return redirect(url_for('index'))
    else:
        flash('Challenge verification failed. Please try again.', 'error')
        return redirect(url_for('index'))

    # Continue with login logic
    if username in users and users[username]['password'] == password:
        session['username'] = username
        flash('Login successful!', 'success')
        return redirect(url_for('chat'))
    else:
        flash('Invalid username or password. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logout successful!', 'success')
    return redirect(url_for('index'))

@app.route('/end_chat')
def end_chat():
    # Additional logic for ending the chat (if needed)
    session.pop('username', None)
    flash('Chat ended successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/chat')
def chat():
    if 'username' in session:
        return render_template('chat.html', username=session['username'])
    else:
        flash('Please log in or register.', 'error')
        return redirect(url_for('index'))

@socketio.on('message')
def handle_message(data):
    username = session.get('username', 'Unknown')  # Get the username from the session or set to 'Unknown'
    emit('message', {'username': username, 'message': data['message']}, broadcast=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    socketio.run(app, debug=True, host='0.0.0.0')  # Allow external access
