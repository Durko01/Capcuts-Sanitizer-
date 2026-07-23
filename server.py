#!/usr/bin/env python3
"""
CapCuts — Video Sanitizer
-------------------------
Server lokal buat "membersihkan" metadata & fingerprint video hasil export
CapCut sebelum diupload ke TikTok/IG, biar gak gampang ke-flag/ke-grouping
sebagai "pakai template CapCut X" sama sistem deteksi konten platform.

Proses yang dilakukan:
  1. Hapus semua metadata (author, device, GPS, chapters, dll) via ffmpeg
  2. Re-encode ulang video (codec, bitrate, preset baru) -> checksum berubah total
  3. Micro-crop + rescale tipis (default 2%) -> geometri frame sedikit beda
  4. (Opsional) ubah speed dikit -> durasi & pola frame beda
  5. Rename output pakai random UUID, hapus file asli dari uploads/

Author : (isi nama/username lu)
License: MIT
"""

import re
import uuid
import shutil
import subprocess
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, render_template

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".webm"}
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

JOBS = {}  # job_id -> {status, progress, message, output_file}


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def get_duration(path):
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stderr=subprocess.STDOUT,
        )
        return float(out.strip())
    except Exception:
        return None


def sanitize_video(job_id, input_path, options):
    job = JOBS[job_id]
    job["status"] = "processing"
    job["message"] = "Menyiapkan..."

    output_name = f"clean_{uuid.uuid4().hex[:10]}.mp4"
    output_path = OUTPUT_DIR / output_name
    duration = get_duration(input_path)

    vf_filters = []
    af_filters = []

    if options.get("micro_crop", True):
        pct = options.get("crop_percent", 2)
        factor = (100 - pct) / 100
        vf_filters.append(f"crop=iw*{factor}:ih*{factor},scale=iw/{factor}:ih/{factor}")

    speed = options.get("speed_factor", 1.0)
    if speed != 1.0:
        vf_filters.append(f"setpts={1/speed}*PTS")
        af_filters.append(f"atempo={speed}")

    cmd = ["ffmpeg", "-y", "-i", str(input_path)]
    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]
    if af_filters:
        cmd += ["-af", ",".join(af_filters)]

    crf = options.get("crf", 23)
    cmd += [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    job["message"] = "Encoding video..."
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

    time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    for line in process.stderr:
        if duration:
            match = time_re.search(line)
            if match:
                h, m, s = match.groups()
                elapsed = int(h) * 3600 + int(m) * 60 + float(s)
                job["progress"] = min(99, int((elapsed / duration) * 100))

    process.wait()

    if process.returncode == 0 and output_path.exists():
        job["status"] = "done"
        job["progress"] = 100
        job["message"] = "Selesai"
        job["output_file"] = output_name
    else:
        job["status"] = "error"
        job["message"] = "Gagal memproses video (cek ffmpeg terpasang & format didukung)"

    try:
        input_path.unlink(missing_ok=True)
    except Exception:
        pass


@app.route("/")
def index():
    return render_template("index.html", ffmpeg_ok=ffmpeg_available())


@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "Tidak ada file dikirim"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "Nama file kosong"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Format {ext} tidak didukung. Pakai: {', '.join(ALLOWED_EXT)}"}), 400

    job_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{job_id}{ext}"
    file.save(saved_path)

    options = {
        "micro_crop": request.form.get("micro_crop", "true") == "true",
        "crop_percent": float(request.form.get("crop_percent", 2)),
        "speed_factor": float(request.form.get("speed_factor", 1.0)),
        "crf": int(request.form.get("crf", 23)),
    }

    JOBS[job_id] = {"status": "queued", "progress": 0, "message": "Menunggu...", "output_file": None}

    threading.Thread(target=sanitize_video, args=(job_id, saved_path, options), daemon=True).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job tidak ditemukan"}), 404
    return jsonify(job)


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    if not ffmpeg_available():
        print("⚠️  ffmpeg belum terpasang. Jalankan: pkg install ffmpeg")
    print("🚀 CapCuts server jalan di http://127.0.0.1:8787")
    app.run(host="127.0.0.1", port=8787, debug=False)
