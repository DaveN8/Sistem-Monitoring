from flask import (
    Flask,
    redirect,
    render_template,
    request,
    make_response,
    session,
    abort,
    jsonify,
    url_for,
    flash,
)
import secrets
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
from datetime import timedelta
import os
import requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import math
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Configure session cookie settings
app.config["SESSION_COOKIE_SECURE"] = True  # Ensure cookies are sent over HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to cookies
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    days=1
)  # Adjust session expiration as needed
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Can be 'Strict', 'Lax', or 'None'

# Firebase Admin SDK setup
cred = credentials.Certificate("firebase-auth.json")
firebase_admin.initialize_app(cred)
# firebase_admin.initialize_app(cred, {
#     'storageBucket': 'your-project-id.appspot.com'  # <- Ganti dengan nama bucket kamu
# })
db = firestore.client()
# bucket = storage.bucket()

# Setup Static folder for file
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


########################################
""" Authentication and Authorization """


# Decorator for routes that require authentication
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if "user" not in session:
            return redirect(url_for("login"))

        else:
            return f(*args, **kwargs)

    return decorated_function


@app.route("/auth", methods=["POST"])
def authorize():
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return "Unauthorized", 401

    token = token[7:]  # Strip off 'Bearer ' to get the actual token

    try:
        decoded_token = auth.verify_id_token(
            token, check_revoked=True, clock_skew_seconds=60
        )  # Validate token here
        session["user"] = decoded_token  # Add user to session
        return redirect(url_for("dashboard"))

    except:
        return "Unauthorized", 401


#####################
""" Public Routes """


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            # Sign in user pakai Firebase Auth
            user = auth.get_user_by_email(email)

            api_key = os.getenv("FIREBASE_API_KEY")  # tambahkan ke .env
            payload = {"email": email, "password": password, "returnSecureToken": True}

            res = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
                json=payload,
            )

            if res.status_code == 200:
                uid = res.json()["localId"]
                user_doc = db.collection("users").document(uid).get()
                user_data = user_doc.to_dict()

                session["user_id"] = uid
                session["role"] = user_data["role"]
                session["nama"] = user_data["nama"]

                # Redirect berdasarkan role
                if user_data["role"] == "pemilik":
                    return redirect(url_for("dashboard_pemilik"))
                else:
                    return redirect(url_for("dashboard_penghuni"))
            else:
                flash("Email atau password salah!", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nama = request.form["nama"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        try:
            # Firebase Auth
            user = auth.create_user(email=email, password=password)

            # Simpan data ke Firestore
            db.collection("users").document(user.uid).set(
                {"nama": nama, "email": email, "role": role}
            )

            flash("Registrasi berhasil!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template("auth/register.html")


@app.route("/reset-password")
def reset_password():
    if "user" in session:
        return redirect(url_for("dashboard"))
    else:
        return render_template("auth/forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Berhasil logout", "success")
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


##############################################
""" Private Routes (Require authorization) """


@app.route("/dashboard/pemilik")
def dashboard_pemilik():
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    # Ambil semua kamar
    kamar_list = db.collection("kamar").order_by("created_at").stream()
    kamar_data = []
    for doc in kamar_list:
        kamar = doc.to_dict()
        kamar["id"] = doc.id

        # Ambil tagihan terakhir
        tagihan_ref = (
            db.collection("tagihan")
            .where("KamarID", "==", doc.id)
            .order_by("Bulan", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        tagihan = next(tagihan_ref, None)
        kamar["tagihan"] = tagihan.to_dict() if tagihan else None

        kamar_data.append(kamar)

    users_ref = db.collection("users").where("role", "==", "penghuni")
    penghuni_list = [doc.to_dict() | {"uid": doc.id} for doc in users_ref.stream()]
    return render_template(
        "dashboard/pemilik.html", kamar_data=kamar_data, penghuni_list=penghuni_list
    )


@app.route("/dashboard/penghuni")
def dashboard_penghuni():
    if session.get("role") != "penghuni":
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    # Cari kamar berdasarkan PenghuniID
    kamar_doc = next(
        (
            doc
            for doc in db.collection("kamar").stream()
            if doc.to_dict().get("UserID") == user_id
        ),
        None,
    )
    if not kamar_doc:
        flash("Kamu belum terdaftar di kamar mana pun.", "warning")
        return render_template("penghuni/belum_assign.html", kamar=None)

    kamar_data = kamar_doc.to_dict()
    kamar_id = kamar_doc.id

    # Ambil tagihan terbaru
    tagihan_query = (
        db.collection("tagihan")
        .where("KamarID", "==", kamar_id)
        .order_by("Bulan", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    tagihan_docs = list(tagihan_query.stream())
    tagihan = tagihan_docs[0].to_dict() if tagihan_docs else None

    # Ambil histori daya terakhir (7 data)
    histori_query = (
        db.collection("data_daya")
        .where("KamarID", "==", kamar_id)
        .order_by("Timestamp", direction=firestore.Query.DESCENDING)
        .limit(7)
    )
    histori_raw = list(histori_query.stream())
    histori_data = []

    for doc in reversed(histori_raw):  # dari yang lama ke baru
        data = doc.to_dict()
        timestamp = data.get("Timestamp")
        watt = data.get("JumlahWatt", 0)

        kwh = round(watt * (5 / 60 / 60), 4)  # konversi watt ke kWh

        histori_data.append(
            {
                "timestamp": timestamp.strftime("%Y-%m-%d") if timestamp else "Unknown",
                "kWh": kwh,
            }
        )

    return render_template(
        "dashboard/penghuni.html",
        kamar=kamar_data,
        tagihan=tagihan,
        histori=histori_data,  # histori sekarang dalam kWh
    )


@app.route("/profil", methods=["GET", "POST"])
def profil():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = auth.get_user(user_id)
    role = session.get("role")

    # Ambil kamar penghuni
    kamar_doc = next(
        (
            doc
            for doc in db.collection("kamar").stream()
            if doc.to_dict().get("UserID") == user_id
        ),
        None,
    )
    if not kamar_doc:
        flash("Kamu belum terdaftar di kamar mana pun.", "warning")
        return render_template("profil.html", user=user, role=role, kamar=None)

    kamar_data = kamar_doc.to_dict()

    if request.method == "POST":
        new_password = request.form.get("new_password")
        if new_password:
            try:
                auth.update_user(user_id, password=new_password)
                flash("Password berhasil diperbarui.", "success")
            except Exception as e:
                flash(f"Gagal mengubah password: {str(e)}", "danger")

    return render_template("profil.html", user=user, role=role, kamar=kamar_data)


#############################
""" Routing Untuk Pemilik """


### Kamar
@app.route("/pemilik/kamar", methods=["GET", "POST"])
def kelola_kamar():
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    kamar_ref = db.collection("kamar")

    if request.method == "POST":
        nomor = request.form.get("nomor_kamar")
        tarif = float(request.form.get("tarif_per_kwh"))
        batas = float(request.form.get("batas_watt") or 0)

        # 🔎 Cek apakah nomor kamar sudah ada
        existing_kamar = kamar_ref.where("NomorKamar", "==", nomor).get()
        if existing_kamar:
            flash("Nomor kamar sudah digunakan. Silakan pilih nomor lain.", "danger")
            return redirect(url_for("kelola_kamar"))

        # ✅ Jika tidak duplikat, tambahkan kamar
        kamar_ref.add(
            {
                "NomorKamar": nomor,
                "TarifPerKWH": tarif,
                "BatasKWH": batas,
                "UserID": "",
                "relay1_status": "OFF",
                "relay2_status": "OFF",
                "created_at": datetime.utcnow(),
            }
        )

        flash("Kamar berhasil ditambahkan!", "success")
        return redirect(url_for("kelola_kamar"))

    users_ref = db.collection("users").where("role", "==", "penghuni")
    penghuni_list = [doc.to_dict() | {"uid": doc.id} for doc in users_ref.stream()]
    daftar_kamar = [
        doc.to_dict() | {"id": doc.id}
        for doc in kamar_ref.order_by("created_at").stream()
    ]
    return render_template(
        "pemilik/kelola_kamar.html", kamar=daftar_kamar, penghuni_list=penghuni_list
    )


@app.route("/pemilik/kamar/edit/<id>", methods=["POST"])
def edit_kamar(id):
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    nomor = request.form.get("nomor_kamar")
    tarif = float(request.form.get("tarif_per_kwh"))
    batas = float(request.form.get("batas_kwh") or 0)

    kamar_ref = db.collection("kamar")
    kamar_doc = kamar_ref.document(id)

    # Cek apakah nomor kamar sudah dipakai oleh kamar lain
    existing = kamar_ref.where("NomorKamar", "==", nomor).get()
    for doc in existing:
        if doc.id != id:
            flash("Nomor kamar sudah digunakan oleh kamar lain.", "danger")
            return redirect(url_for("kelola_kamar"))

    # Update data
    kamar_doc.update({"NomorKamar": nomor, "TarifPerKWH": tarif, "BatasKWH": batas})

    flash("Kamar berhasil diupdate!", "success")
    return redirect(url_for("kelola_kamar"))


@app.route("/pemilik/kamar/delete/<id>", methods=["POST"])
def delete_kamar(id):
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    db.collection("kamar").document(id).delete()
    flash("Kamar berhasil dihapus!", "success")
    return redirect(url_for("kelola_kamar"))


@app.route("/pemilik/relay_control", methods=["POST"])
def relay_control():
    kamar_id = request.form.get("kamar_id")
    relay1_status = request.form.get("relay1_status")

    # Konversi dari "on"/"off" ke boolean
    relay1_bool = relay1_status == "on"

    kamar_ref = db.collection("kamar").document(kamar_id)

    # Ambil data kamar untuk flash message
    kamar_data = kamar_ref.get().to_dict()
    nomor_kamar = kamar_data.get("NomorKamar", "Tidak diketahui")

    # Update hanya relay1_status
    kamar_ref.update({"relay1_status": relay1_bool})

    flash(
        f"Status relay Kamar {nomor_kamar} diperbarui menjadi {'ON' if relay1_bool else 'OFF'}.",
        "success",
    )
    return redirect(url_for("dashboard_pemilik"))


### Assign penghuni ke kamar
@app.route("/pemilik/kamar/assign/<id>", methods=["POST"])
def assign_penghuni(id):
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    user_id = request.form.get("user_id")

    if user_id == "":
        # Unassign kamar
        db.collection("kamar").document(id).update({"UserID": firestore.DELETE_FIELD})
        flash("Penghuni berhasil di-unassign dari kamar.", "info")
        return redirect(url_for("kelola_kamar"))

    # Cek apakah user_id sudah digunakan di kamar lain
    kamar_ref = db.collection("kamar").where("UserID", "==", user_id).get()
    if kamar_ref:
        flash("Gagal assign: Penghuni ini sudah menempati kamar lain.", "danger")
        return redirect(url_for("kelola_kamar"))

    # Assign user_id ke kamar ini
    db.collection("kamar").document(id).update({"UserID": user_id})
    flash("Penghuni berhasil di-assign ke kamar.", "success")
    return redirect(url_for("kelola_kamar"))


### Tagihan
def buat_tagihan_bulanan():
    now = datetime.now()
    bulan_str = now.strftime("%Y-%m")

    kamar_ref = db.collection("kamar").stream()
    tagihan_terbuat = 0  # Counter untuk menghitung jumlah tagihan yang berhasil dibuat

    for kamar in kamar_ref:
        kamar_data = kamar.to_dict()
        kamar_id = kamar.id
        batas_kwh = kamar_data.get("BatasKWH", 0)

        histori_ref = (
            db.collection("data_daya").where("KamarID", "==", kamar_id).stream()
        )

        total_kwh = 0.0
        for doc in histori_ref:
            data = doc.to_dict()
            ts = data.get("Timestamp")
            if ts and ts.month == now.month and ts.year == now.year:
                watt = data.get(
                    "JumlahWatt", 0
                )  # Perhatikan field-nya: JumlahWatt, bukan Watt
                total_kwh += (watt / 1000) * (1 / 3600)

        total_kwh = round(total_kwh, 3)

        if total_kwh > batas_kwh:
            pemakaian_berlebih = round(total_kwh - batas_kwh, 3)
            total_tagihan = round(pemakaian_berlebih * 1400, 2)

            existing = (
                db.collection("tagihan")
                .where("KamarID", "==", kamar_id)
                .where("Bulan", "==", bulan_str)
                .get()
            )

            if not existing:
                db.collection("tagihan").add(
                    {
                        "KamarID": kamar_id,
                        "Bulan": bulan_str,
                        "JumlahkWhTerpakai": pemakaian_berlebih,
                        "TotalTagihan": total_tagihan,
                        "StatusPembayaran": "Menunggu",
                        "Timestamp": datetime.now(),
                    }
                )
                tagihan_terbuat += 1

    return tagihan_terbuat


@app.route("/pemilik/tagihan", methods=["GET", "POST"])
def tagihan_pemilik():
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    # Ambil parameter filter dari query string
    selected_kamar = request.args.get("kamar")
    selected_bulan = request.args.get("bulan")

    # Handle POST
    if request.method == "POST":
        if request.form.get("aksi") == "generate_tagihan":
            jumlah_tagihan = buat_tagihan_bulanan()
            if jumlah_tagihan > 0:
                flash(
                    f"{jumlah_tagihan} tagihan berhasil dibuat untuk bulan ini.",
                    "success",
                )
            else:
                flash(
                    "Tidak ada tagihan yang dibuat. Semua kamar berada di bawah batas kWh atau tagihan sudah dibuat.",
                    "warning",
                )
            return redirect(url_for("tagihan_pemilik"))

        tagihan_id = request.form.get("tagihan_id")
        aksi = request.form.get("aksi")
        if tagihan_id and aksi:
            status = "Sudah Bayar" if aksi == "konfirmasi" else "Belum Bayar"
            db.collection("tagihan").document(tagihan_id).update(
                {"StatusPembayaran": status}
            )
            flash(
                f"Status pembayaran berhasil diperbarui menjadi '{status}'.", "success"
            )
        return redirect(url_for("tagihan_pemilik"))

    # Ambil data kamar untuk filter dan akses cepat
    kamar_ref = db.collection("kamar").stream()
    kamar_dict = {doc.id: doc.to_dict() for doc in kamar_ref}

    # Query tagihan
    tagihan_query = db.collection("tagihan")

    if selected_kamar:
        tagihan_query = tagihan_query.where("KamarID", "==", selected_kamar)
    if selected_bulan:
        tagihan_query = tagihan_query.where("Bulan", "==", selected_bulan)

    tagihan_docs = tagihan_query.order_by(
        "Bulan", direction=firestore.Query.DESCENDING
    ).stream()

    tagihan_list = []
    for doc in tagihan_docs:
        data = doc.to_dict()
        data["id"] = doc.id
        kamar_info = kamar_dict.get(data["KamarID"], {})
        data["NomorKamar"] = kamar_info.get("NomorKamar", "Unknown")
        tagihan_list.append(data)

    # Siapkan list kamar untuk dropdown filter
    kamar_options = [
        {"id": kid, "nomor": info.get("NomorKamar")} for kid, info in kamar_dict.items()
    ]

    return render_template(
        "pemilik/tagihan_pemilik.html",
        tagihan_list=tagihan_list,
        kamar_options=kamar_options,
        selected_kamar=selected_kamar,
        selected_bulan=selected_bulan,
    )


@app.route("/pemilik/verifikasi-pembayaran/<tagihan_id>", methods=["POST"])
def verifikasi_pembayaran(tagihan_id):
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    aksi = request.form.get("aksi")
    tagihan_ref = db.collection("tagihan").document(tagihan_id)
    tagihan = tagihan_ref.get().to_dict()

    if not tagihan:
        flash("Tagihan tidak ditemukan.", "error")
        return redirect(url_for("tagihan_pemilik"))

    if aksi == "terima":
        tagihan_ref.update({"StatusPembayaran": "Sudah Bayar"})
        flash("Pembayaran berhasil dikonfirmasi.", "success")
    elif aksi == "tolak":
        tagihan_ref.update({"StatusPembayaran": "Ditolak"})
        flash("Pembayaran ditolak. Penghuni dapat mengunggah ulang bukti.", "warning")
    else:
        flash("Aksi tidak valid.", "error")

    return redirect(url_for("tagihan_pemilik"))


### Daya
@app.route("/pemilik/histori-daya", methods=["GET", "POST"])
def histori_daya():
    if session.get("role") != "pemilik":
        return redirect(url_for("login"))

    selected_kamar = request.args.get("kamar")
    selected_date = request.args.get("tanggal")
    selected_bulan = request.args.get("bulan")
    page = int(request.args.get("page", 1))
    per_page = 15

    if selected_date in (None, "", "None"):
        selected_date = None
    if selected_bulan in (None, "", "None"):
        selected_bulan = None

    # Ambil semua data kamar (nomor & batas kWh)
    kamar_docs = db.collection("kamar").stream()
    kamar_dict = {}
    for k in kamar_docs:
        data = k.to_dict()
        kamar_dict[k.id] = {
            "nomor": data.get("NomorKamar", "Tidak diketahui"),
            "batas_kwh": data.get("BatasKWH", 0),
        }

    # Query histori daya
    query = db.collection("data_daya")
    if selected_kamar:
        query = query.where("KamarID", "==", selected_kamar)

    query = query.order_by("Timestamp", direction=firestore.Query.DESCENDING).stream()

    histori_data = []
    ringkasan_kamar = (
        {}
    )  # kunci: KamarID, isi: {total_kwh, total_kwh_over, nomor_kamar}

    for doc in query:
        data = doc.to_dict()
        ts = data.get("Timestamp")
        if not ts:
            continue

        # Filter tanggal
        if selected_date:
            try:
                if ts.date() != datetime.strptime(selected_date, "%Y-%m-%d").date():
                    continue
            except ValueError:
                continue

        elif selected_bulan:
            try:
                bulan_obj = datetime.strptime(selected_bulan, "%Y-%m")
                if ts.year != bulan_obj.year or ts.month != bulan_obj.month:
                    continue
            except ValueError:
                continue

        kamar_id = data.get("KamarID")
        watt = data.get("JumlahWatt", 0)
        kwh = round((watt / 1000) * (1 / 3600), 6)

        kamar_info = kamar_dict.get(
            kamar_id, {"nomor": "Tidak diketahui", "batas_kwh": 0}
        )
        batas_kwh = kamar_info["batas_kwh"]
        kwh_over = max(kwh - batas_kwh, 0)

        histori_data.append(
            {
                "NomorKamar": kamar_info["nomor"],
                "KamarID": kamar_id,
                "Tanggal": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "kWh": kwh,
                "kWhOverLimit": kwh_over,
            }
        )

        # Akumulasi per kamar
        if kamar_id not in ringkasan_kamar:
            ringkasan_kamar[kamar_id] = {
                "nomor": kamar_info["nomor"],
                "total_kwh": 0,
                "total_kwh_over": 0,
            }
        ringkasan_kamar[kamar_id]["total_kwh"] += kwh
        ringkasan_kamar[kamar_id]["total_kwh_over"] += kwh_over

    # Pagination
    total_data = len(histori_data)
    total_pages = (total_data + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    histori_data_paginated = histori_data[start:end]

    kamar_for_filter = [{"id": k, "nomor": v["nomor"]} for k, v in kamar_dict.items()]

    return render_template(
        "pemilik/histori_daya.html",
        histori_data=histori_data_paginated,
        kamar_list=kamar_for_filter,
        selected_kamar=selected_kamar,
        selected_date=selected_date,
        selected_bulan=selected_bulan,
        current_page=page,
        total_pages=total_pages,
        ringkasan_kamar=ringkasan_kamar,
    )


########################
""" Routing Penghuni """


@app.route("/penghuni/upload-bukti/<tagihan_id>", methods=["GET", "POST"])
def upload_bukti(tagihan_id):
    if session.get("role") != "penghuni":
        return redirect(url_for("login"))

    tagihan_ref = db.collection("tagihan").document(tagihan_id)
    tagihan_doc = tagihan_ref.get()

    if not tagihan_doc.exists:
        flash("Tagihan tidak ditemukan.", "danger")
        return redirect(url_for("tagihan_penghuni"))

    tagihan = tagihan_doc.to_dict()
    status = tagihan.get("StatusPembayaran", "").lower()

    if status not in ["ditolak", "menunggu", "belum dibayar"]:
        flash("Hanya bisa upload jika status tagihan Menunggu atau Ditolak.", "warning")
        return redirect(url_for("tagihan_penghuni"))

    if request.method == "POST":
        file = request.files["bukti"]
        if file:
            # Hapus file lama di folder lokal (jika ada)
            old_url = tagihan.get("BuktiBayarURL")
            if old_url and "static/uploads" in old_url:
                try:
                    old_filename = old_url.split("uploads/")[-1]
                    os.remove(os.path.join(UPLOAD_FOLDER, old_filename))
                except Exception as e:
                    print("Gagal menghapus file lama:", e)

            filename = secure_filename(f"{tagihan_id}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            url = url_for("static", filename=f"uploads/{filename}", _external=True)

            tagihan_ref.update(
                {
                    "BuktiBayarURL": url,
                    "StatusPembayaran": "Menunggu",
                    "TerakhirUpload": datetime.utcnow(),
                }
            )

            flash("Bukti pembayaran berhasil diunggah.", "success")
            return redirect(url_for("tagihan_penghuni"))

        flash("Silakan unggah file terlebih dahulu.", "warning")

    return render_template("penghuni/upload_bukti.html", tagihan=tagihan)


@app.route("/penghuni/tagihan")
def tagihan_penghuni():
    if session.get("role") != "penghuni":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    # print(user_id)

    # Ambil kamar_id dari UserID
    kamar_id = None
    for doc in db.collection("kamar").stream():
        data = doc.to_dict()
        if data.get("UserID") == user_id:
            kamar_id = doc.id
            # print(kamar_id)
            break

    if not kamar_id:
        flash("Anda belum terdaftar di kamar mana pun.", "warning")
        return render_template("penghuni/tagihan.html", tagihan=[], bulan_filter=None)

    # Filter bulan
    bulan_filter = request.args.get("bulan")  # Format: YYYY-MM
    page = int(request.args.get("page", 1))

    tagihan_ref = db.collection("tagihan").where("KamarID", "==", kamar_id)
    if bulan_filter:
        tagihan_ref = tagihan_ref.where("Bulan", "==", bulan_filter)

    tagihan_docs = tagihan_ref.order_by(
        "Bulan", direction=firestore.Query.DESCENDING
    ).stream()

    tagihan_all = [doc.to_dict() | {"id": doc.id} for doc in tagihan_docs]
    total_pages = (len(tagihan_all) + 14) // 15
    tagihan = tagihan_all[(page - 1) * 15 : page * 15]
    print(tagihan)

    return render_template(
        "penghuni/tagihan_penghuni.html",
        tagihan=tagihan,
        bulan_filter=bulan_filter,
        page=page,
        total_pages=total_pages,
    )


@app.route("/penghuni/histori")
def histori_penghuni():
    if session.get("role") != "penghuni":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    kamar_id = None
    batas_kwh = 0

    # Cari kamar milik penghuni
    for doc in db.collection("kamar").stream():
        data = doc.to_dict()
        if data.get("UserID") == user_id:
            kamar_id = doc.id
            batas_kwh = data.get("BatasKWH", 0)  # dari watt ke kWh
            break

    if not kamar_id:
        flash("Anda belum terdaftar di kamar mana pun.", "warning")
        return render_template(
            "penghuni/histori_penghuni.html",
            histori=[],
            bulan_filter=None,
            batas_kwh=0,
            total_kwh=0,
        )

    bulan_filter = request.args.get("bulan")  # format: YYYY-MM
    page = int(request.args.get("page", 1))

    daya_ref = db.collection("data_daya").where("KamarID", "==", kamar_id)

    if bulan_filter:
        year, month = map(int, bulan_filter.split("-"))
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        daya_ref = daya_ref.where("Timestamp", ">=", start_date).where(
            "Timestamp", "<", end_date
        )

    daya_docs = daya_ref.order_by(
        "Timestamp", direction=firestore.Query.DESCENDING
    ).stream()
    daya_all = [doc.to_dict() for doc in daya_docs]

    # Hitung total kWh bulan ini
    total_kwh = round(sum([d.get("JumlahWatt", 0) for d in daya_all]) / 60000, 6)

    # Pagination
    total_pages = (len(daya_all) + 14) // 15
    daya = daya_all[(page - 1) * 15 : page * 15]

    for data in daya:
        data["kWh"] = round(data.get("JumlahWatt", 0) / 60000, 6)

    return render_template(
        "penghuni/histori_penghuni.html",
        histori=daya,
        bulan_filter=bulan_filter,
        page=page,
        total_pages=total_pages,
        batas_kwh=batas_kwh,
        total_kwh=total_kwh,
    )


### Dummy
@app.route("/dev/dummydata")
def generate_dummy_data():
    kamar_ids = ["6cAqsZboaQ1giiSqeQ4J", "t7jqaBpRQ9S3QgS1DkKJ"]  # Kamar 1  # Kamar 2
    jakarta_tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(jakarta_tz)

    # 1. Tambahkan dummy data daya (10 hari terakhir)
    for kamar_id in kamar_ids:
        for i in range(10):
            timestamp = now - timedelta(days=i)
            watt = random.randint(100, 300)
            db.collection("data_daya").add(
                {
                    "KamarID": kamar_id,
                    "JumlahWatt": watt,
                    "Timestamp": timestamp,
                }
            )

    # 2. Tambahkan dummy tagihan (3 tagihan)
    tagihan_data = [
        {
            "KamarID": "6cAqsZboaQ1giiSqeQ4J",
            "Bulan": "2025-03",
            "JumlahKWH": 15.2,
        },
        {
            "KamarID": "6cAqsZboaQ1giiSqeQ4J",
            "Bulan": "2025-04",
            "JumlahKWH": 12.7,
        },
        {
            "KamarID": "t7jqaBpRQ9S3QgS1DkKJ",
            "Bulan": "2025-04",
            "JumlahKWH": 9.5,
        },
    ]
    tarif_per_kwh = 1400

    for tagihan in tagihan_data:
        total_tagihan = tagihan["JumlahKWH"] * tarif_per_kwh
        db.collection("tagihan").add(
            {
                "KamarID": tagihan["KamarID"],
                "Bulan": tagihan["Bulan"],
                "JumlahKWH": tagihan["JumlahKWH"],
                "JumlahWattTerpakai": tagihan["JumlahKWH"] * 1000,
                "TotalTagihan": total_tagihan,
                "StatusPembayaran": "Belum Dibayar",
                "Timestamp": now,
            }
        )

    return jsonify(
        {"status": "success", "message": "Dummy data daya & tagihan berhasil dibuat."}
    )


if __name__ == "__main__":
    app.run(debug=True)
