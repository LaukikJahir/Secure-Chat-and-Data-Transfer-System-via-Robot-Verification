# app.py
from flask import Flask, render_template, request, session, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask import render_template, request, url_for, redirect, flash
from flask_socketio import emit
from flask import send_file, send_from_directory
from flask_socketio import join_room
from flask import session
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

# Define a global variable to store shared files
shared_files = []

@socketio.on('file_shared')
def handle_file_shared(data):
    username = data['username']
    filename = data['filename']

    # Generate file path
    file_path = url_for('uploaded_file', filename=filename, _external=True)

    # Broadcast file information to all connected users
    socketio.emit('file_shared', {'username': username, 'filename': filename, 'file_path': file_path})

@app.route('/file_transfer', methods=['GET', 'POST'])
def file_transfer():
    global shared_files  # Make sure to declare shared_files as a global variable
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

                # Broadcast file information to all connected users
                file_url = url_for('uploaded_file', filename=filename)
                socketio.emit('file_shared', {'username': session.get('username', 'Unknown'), 'filename': filename, 'file_path': file_url}, namespace='/')


                # Update the shared_files list with the new shared file information
                shared_files.append({'username': session.get('username', 'Unknown'), 'filename': filename, 'file_path': file_url})

    # Get the list of shared files from the updated shared_files list
    shared_files_list = [{'filename': file['filename'], 'username': file['username'], 'file_path': file['file_path']} for file in shared_files]

    return render_template('file_transfer.html', error=error, shared_files=shared_files_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)


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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)  # Allow external access on port 5000
