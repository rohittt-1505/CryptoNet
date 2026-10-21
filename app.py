
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection

from cryptography.exceptions import InvalidTag
from crypto_service import encrypt_message, decrypt_message
from key_service import load_or_create_key

app = Flask(__name__)

# Local development only. Production mein secret environment variable se lena.
app.secret_key = "change-this-local-development-secret"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill in all fields.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        connection = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                "SELECT UserId FROM dbo.Users WHERE Username = ? OR Email = ?",
                (username, email)
            )

            if cursor.fetchone():
                flash("Username or email is already registered.", "error")
                return render_template("register.html")

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO dbo.Users (Username, Email, PasswordHash)
                VALUES (?, ?, ?)
                """,
                (username, email, password_hash)
            )

            connection.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except Exception:
            app.logger.exception("Registration failed")
            flash("Registration failed. Please check the server logs.", "error")

        finally:
            if connection is not None:
                connection.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = None

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT UserId, Username, PasswordHash
                FROM dbo.Users
                WHERE Username = ?
                """,
                (username,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(user[2], password):
                session.clear()
                session["user_id"] = user[0]
                session["username"] = user[1]

                return redirect(url_for("dashboard"))

            flash("Invalid username or password.", "error")

        except Exception:
            app.logger.exception("Login failed")
            flash("Login failed. Please check the server logs.", "error")

        finally:
            if connection is not None:
                connection.close()

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )



@app.route("/messages")
def messages():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT UserId, Username
            FROM dbo.Users
            WHERE UserId != ?
            ORDER BY Username
            """,
            (session["user_id"],)
        )

        users = cursor.fetchall()

        return render_template(
            "messages.html",
            users=users
        )

    except Exception:
        app.logger.exception("Could not load receiver list")
        return "Unable to load users. Check the server log.", 500

    finally:
        if connection is not None:
            connection.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))



@app.route("/messages/send", methods=["POST"])
def send_message():
    if "user_id" not in session:
        return redirect(url_for("login"))

    receiver_id = request.form.get("receiver", type=int)
    message = request.form.get("message", "").strip()

    if not receiver_id or not message or len(message) > 5000:
        flash("Select a receiver and enter a valid message.", "error")
        return redirect(url_for("messages"))

    if receiver_id == session["user_id"]:
        flash("You cannot send a message to yourself.", "error")
        return redirect(url_for("messages"))

    connection = None

    try:
        import hashlib

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT UserId FROM dbo.Users WHERE UserId = ?",
            (receiver_id,)
        )

        if cursor.fetchone() is None:
            flash("Receiver does not exist.", "error")
            return redirect(url_for("messages"))

        key = load_or_create_key()
        encrypted = encrypt_message(message, key)

        # Store a SHA-256 hash of the encrypted ciphertext.
        ciphertext = encrypted["ciphertext"]
        message_hash = hashlib.sha256(
            ciphertext.encode("utf-8")
        ).hexdigest()

        cursor.execute(
            """
            INSERT INTO dbo.MessageLogs
                (SenderId, ReceiverId, MessageHash, Nonce, CipherText, Status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                receiver_id,
                message_hash,
                encrypted["nonce"],
                ciphertext,
                "Sent"
            )
        )

        connection.commit()
        flash("Encrypted message saved successfully!", "success")

    except Exception:
        if connection is not None:
            connection.rollback()

        app.logger.exception("Message sending failed")
        flash("Message could not be sent. Check the server log.", "error")

    finally:
        if connection is not None:
            connection.close()

    return redirect(url_for("messages"))


@app.route("/inbox")
def inbox():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    messages_list = []

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT m.MessageId, u.Username, m.CipherText,
                   m.Nonce, m.SentAt, m.Status
            FROM dbo.MessageLogs AS m
            INNER JOIN dbo.Users AS u ON u.UserId = m.SenderId
            WHERE m.ReceiverId = ?
            ORDER BY m.SentAt DESC, m.MessageId DESC
            """,
            (session["user_id"],)
        )

        rows = cursor.fetchall()
        key = load_or_create_key()

        for row in rows:
            message_text = None
            message_status = "Encrypted data could not be verified"

            try:
                encrypted_data = {
                    "ciphertext": row[2],
                    "nonce": row[3]
                }

                message_text = decrypt_message(encrypted_data, key)
                message_status = "Verified and decrypted"

            except (InvalidTag, ValueError, TypeError):
                # Do not display modified or invalid ciphertext.
                message_text = None

            messages_list.append({
                "message_id": row[0],
                "sender": row[1],
                "message": message_text,
                "sent_at": row[4],
                "status": message_status
            })

    except Exception:
        app.logger.exception("Inbox loading failed")
        flash("Could not load inbox. Check the server log.", "error")

    finally:
        if connection is not None:
            connection.close()

    return render_template("inbox.html", messages=messages_list)

if __name__ == "__main__":
    app.run(debug=True)
